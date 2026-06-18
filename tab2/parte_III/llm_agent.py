from __future__ import annotations

"""Agente estratégico MEGA simples.
Marco Cristo, 2026

Objetivo desta versão:
- servir como ponto de partida;
- manter a interface esperada pela infraestrutura;
- ser funcional, para vcs terem um exemplo que roda.

Características:
- escolhe a carta do narrador por uma heurística muito simples;
- gera dica com a LLM, mas com prompt beeeem básico;
- escolhe carta e votos com regras ingênuas;
- não tenta otimizar de verdade para vencer o baseline aleatório.
"""

import argparse
import asyncio
import logging
import re
import random
from typing import Any, Dict, List

from base_agent import BaseAgent
from fasta2a import A2AApp, tool

app = A2AApp(name="LLMAgent")

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    def __init__(self, name: str, llm_url: str):
        super().__init__(name=name, llm_url=llm_url, request_timeout=60.0)

    @tool()
    async def receive_hand(self, hand: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.hand = list(hand)
        return {"status": "ok", "hand_size": len(self.hand)}

    @tool()
    async def choose_card(self) -> Dict[str, Any]:
        # Heurística mega simples:
        # escolhe a carta cuja letra truncada tem tamanho mais próximo da mediana.
        # Pelamor, n vao me entregar isso de volta!!! x-(
        if not self.hand:
            raise RuntimeError("Hand is empty")

        lengths = [len(song.get("lyrics", "")) for song in self.hand]
        ordered = sorted(lengths)
        median = ordered[len(ordered) // 2]

        best_idx = 0
        best_dist = abs(lengths[0] - median)
        for i in range(1, len(self.hand)):
            dist = abs(lengths[i] - median)
            if dist < best_dist:
                best_idx = i
                best_dist = dist

        return {"chosen_card": self.hand[best_idx]}

    @tool()
    async def send_clue(self, lyrics: str, max_words: int = 6) -> Dict[str, Any]:
        # Prompt bem simples
        # Um exemplo de cm se comunicar com a LLM
        short_lyrics = " ".join(lyrics.split()[:60])

        prompt = (
            "Crie uma dica curta para um jogo de associacao.\n"
            f"Use no maximo {max_words} palavras.\n"
            "Responda apenas com a dica.\n\n"
            f"Letra:\n{short_lyrics}\n\n"
            "Dica:"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=20,
            temperature=0.4,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        clue = self._sanitize_clue(raw.strip(), max_words=max_words, lyrics=lyrics)

        if not clue:
            clue = "coisa estranha"

        return {"clue": clue}

    
    @tool()
    async def select_card_by_clue(self, clue: str) -> Dict[str, Any]:
        """
        Escolhe qual carta da mão melhor representa a dica do narrador.
        Plano A: usa a LLM pedindo estritamente um JSON com o ÍNDICE da música na mão (0..n-1).
        Plano B: heurística de interseção de palavras-chave (fallback).
        """
        if not self.hand:
            logger.warning(f"[{self.name}] Mão vazia recebida em select_card_by_clue.")
            return {"chosen_card": {}}

        n = len(self.hand)
        chosen_idx: int | None = None

        # PLANO A: NÚCLEO SEMÂNTICO (LLM)
        prompt = (
            "Sua tarefa é encontrar a música que melhor combina com a dica.\n"
            f"Dica do narrador: '{clue}'\n\n"
            "Opções na sua mão:\n"
        )
        for idx, song in enumerate(self.hand):
            snippet = song.get("lyrics", "").replace("\n", " ")[:100]
            prompt += f"Opção {idx}: {song.get('title', '?')} | Letra: {snippet}\n"

        prompt += (
            "\nBaseado na dica, qual o melhor índice?\n"
            "Responda estritamente com o bloco JSON abaixo:\n"
            "```json\n"
            "{\"chosen_index\": numero_aqui}\n"
            "```"
        )

        try:
            raw_text = await asyncio.wait_for(
                self.llm_generate(prompt, max_tokens=20, temperature=0.1),
                timeout=60.0,
            )
            
            # Tentativa 1: Extração JSON
            parsed = self._extract_json_object(raw_text)
            if parsed and "chosen_index" in parsed:
                try:
                    idx_val = int(parsed["chosen_index"])
                    if 0 <= idx_val < n:
                        chosen_idx = idx_val
                except (TypeError, ValueError):
                    pass

            # Tentativa 2: Regex padrão do professor
            if chosen_idx is None:
                chosen_idx = self._parse_song_choice(raw_text, n_options=n)

            # Tentativa 3 (NOVA): A LLM ignorou o número e escreveu o nome da música?
            if chosen_idx is None and raw_text:
                raw_lower = raw_text.lower()
                for idx, song in enumerate(self.hand):
                    # Se o título da música da mão estiver dentro da resposta bagunçada da LLM
                    if song.get("title", "").lower() in raw_lower:
                        chosen_idx = idx
                        break

            if chosen_idx is not None:
                logger.info(
                    f"[{self.name}] LLM escolheu índice {chosen_idx}: "
                    f"{self.hand[chosen_idx].get('title')}"
                )

        except asyncio.TimeoutError:
            logger.warning(f"[{self.name}] Timeout da LLM em select_card_by_clue. Usando fallback.")
        except Exception as e:
            logger.warning(f"[{self.name}] Erro na LLM em select_card_by_clue: {e}. Usando fallback.")

        # PLANO B: FALLBACK HEURÍSTICO (interseção de palavras-chave)
        if chosen_idx is None:
            clue_words = set(self._extract_keywords(clue))

            best_score = -1.0
            best_indices: List[int] = []

            for idx, song in enumerate(self.hand):
                song_words = set(self._song_keywords(song, limit=15))
                score = len(clue_words.intersection(song_words))
                if any(word in song.get("title", "").lower() for word in clue_words):
                    score += 0.5

                if score > best_score:
                    best_score = score
                    best_indices = [idx]
                elif score == best_score:
                    best_indices.append(idx)

            if best_score <= 0:
                chosen_idx = random.randrange(n)
                logger.info(f"[{self.name}] Fallback: nenhuma interseção, escolha aleatória.")
            else:
                chosen_idx = best_indices[0]
                logger.info(f"[{self.name}] Fallback: escolha por interseção de palavras-chave.")

        return {"chosen_card": self.hand[chosen_idx]}
    
    def _find_own_option_index(self, options: List[Dict[str, Any]], my_card: Dict[str, Any]) -> int:
        """
        Localiza o índice da própria carta dentro de `options`.

        Tenta casar por 'id' (campo esperado pelo protocolo). Se não
        encontrar - por exemplo, se a chave vier nomeada diferente -,
        tenta casar por (título, artista) como rede de segurança. Loga um
        aviso se nem assim conseguirmos identificar a carta, pois isso
        indicaria uma incompatibilidade de formato que vale investigar
        antes da competição (rode uma partida e confira o formato real
        de `options` e `my_chosen_card` recebidos pelo Game Master).
        """
        my_id = my_card.get("id")
        if my_id is not None:
            for i, opt in enumerate(options):
                if opt.get("id") == my_id:
                    return i

        my_title = my_card.get("title")
        if my_title is not None:
            for i, opt in enumerate(options):
                if opt.get("title") == my_title and opt.get("artist") == my_card.get("artist"):
                    return i

        logger.warning(
            f"[{self.name}] Não foi possível identificar a própria carta em 'options' "
            "(nem por id, nem por título+artista). Nenhum índice será excluído por padrão."
        )
        return -1

    @tool()
    async def vote(self, clue: str, options: List[Dict[str, Any]], my_chosen_card: Dict[str, Any]) -> Dict[str, List[int]]:
        """
        Escolhe em quais cartas votar na rodada.
        Deve retornar exatamente 2 índices distintos, nenhum deles igual ao
        índice da própria carta jogada.

        Plano A: pede à LLM um JSON com dois índices (0 a 5).
        Plano B: garimpa números na MESMA resposta crua, sem nova chamada à LLM.
        Plano C: heurística de interseção de palavras-chave.
        Plano D (rede de segurança): completa com índices válidos restantes,
        garantindo que o contrato (2 votos distintos, sem auto-voto) nunca
        seja violado, mesmo em cenários inesperados.
        """
        my_idx = self._find_own_option_index(options, my_chosen_card)
        valid_indices = [i for i in range(len(options)) if i != my_idx]
        final_votes: List[int] = []

        prompt = f"Dica do narrador: '{clue}'\n"
        prompt += "Quais duas destas músicas melhor combinam com a dica?\n\n"
        for i, opt in enumerate(options):
            if i == my_idx:
                continue
            snippet = opt.get("lyrics", "").replace("\n", " ")[:80]
            prompt += f"Opção {i}: {opt.get('title', '?')} | Letra: {snippet}\n"
        prompt += (
            '\nRetorne APENAS um JSON no formato exato: {"votes": [opcaoA, opcaoB]} '
            "usando os números das Opções acima (0 a 5)."
        )

        raw_text = ""
        try:
            raw_text = await asyncio.wait_for(
                self.llm_generate(prompt, max_tokens=25, temperature=0.1),
                timeout=60.0,
            )
        except Exception as e:
            logger.warning(f"[{self.name}] LLM falhou em vote: {e}")

        # PLANO A: parsing como JSON
        if raw_text:
            parsed = self._extract_json_object(raw_text)
            if parsed and isinstance(parsed.get("votes"), list):
                for v in parsed["votes"]:
                    try:
                        v_int = int(v)
                    except (TypeError, ValueError):
                        continue
                    if v_int in valid_indices and v_int not in final_votes:
                        final_votes.append(v_int)
                    if len(final_votes) == 2:
                        break

        # PLANO B: garimpar números na MESMA resposta crua (sem nova chamada à LLM;
        # o Plano A já usou a única chamada que fizemos ao serviço)
        if len(final_votes) < 2 and raw_text:
            for n in (int(x) for x in re.findall(r"\d+", raw_text)):
                if n in valid_indices and n not in final_votes:
                    final_votes.append(n)
                if len(final_votes) == 2:
                    break

        # PLANO C: heurística de interseção de palavras-chave
        if len(final_votes) < 2:
            logger.info(f"[{self.name}] Usando fallback heurístico para votação.")
            scored = [
                (self._score_song_for_clue(options[i], clue), i)
                for i in valid_indices
                if i not in final_votes
            ]
            scored.sort(reverse=True, key=lambda x: x[0])
            for _, idx in scored:
                final_votes.append(idx)
                if len(final_votes) == 2:
                    break

        # PLANO D: rede de segurança final - garante o contrato sempre,
        # independentemente do que tenha acontecido acima. Itera sobre uma
        # lista finita (não usa "while True"), então nunca trava o agente.
        final_votes = [v for v in final_votes if v in valid_indices]
        deduped: List[int] = []
        for v in final_votes:
            if v not in deduped:
                deduped.append(v)
        final_votes = deduped

        if len(final_votes) < 2:
            remaining = [i for i in valid_indices if i not in final_votes]
            random.shuffle(remaining)
            added = remaining[: 2 - len(final_votes)]
            final_votes.extend(added)

        return {"votes": final_votes[:2]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("game_master_url")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--llm-url", default="http://127.0.0.1:9000")
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    agent = LLMAgent(name=args.name or f"LLMAgent_{args.port}", llm_url=args.llm_url)
    app.register(agent)
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()