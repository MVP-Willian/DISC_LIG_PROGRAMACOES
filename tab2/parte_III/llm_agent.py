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
import json
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
        """Escolhe qual carta da mão melhor representa a dica do narrador (via JSON)."""
        if not self.hand:
            logger.warning(f"[{self.name}] Mão vazia recebida.")
            return {"chosen_card": {}}

        n = len(self.hand)
        chosen_idx = None

        prompt = (
            f"Jogo Dixit. Dica: '{clue}'\n"
            "Qual música melhor representa a dica?\n"
        )
        for idx, song in enumerate(self.hand):
            snippet = song.get("lyrics", "").replace("\n", " ")[:150]
            prompt += f"[{idx}] {song.get('title')} | Letra: {snippet}...\n"

        # Template minúsculo para poupar tokens
        prompt += (
            "\nResponda APENAS com um objeto JSON válido no formato exato: {\"c\": numero}"
        )

        try:
            raw_text = await asyncio.wait_for(
                self.llm_generate(prompt, max_tokens=20, temperature=0.2),
                timeout=45.0,
            )
            
            # Extrai apenas o bloco JSON usando regex para driblar modelos faladores
            match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                
                if "c" in data and isinstance(data["c"], int):
                    idx_val = data["c"]
                    if 0 <= idx_val < n:
                        chosen_idx = idx_val

            # Fallback secundário: se o JSON falhar, tenta achar qualquer número
            if chosen_idx is None:
                numbers = [int(x) for x in re.findall(r'\b\d\b', raw_text)]
                valid_numbers = [x for x in numbers if 0 <= x < n]
                if valid_numbers:
                    chosen_idx = valid_numbers[0]

        except Exception as e:
            logger.warning(f"[{self.name}] Falha na LLM em select_card: {e}")

        if chosen_idx is None:
            logger.info(f"[{self.name}] Usando fallback aleatório para select_card.")
            chosen_idx = random.randrange(n)

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
    async def vote(self, clue: str, options: List[Dict[str, Any]], my_chosen_card: Dict[str, Any]) -> Dict[str, Any]:
        """Vota nas cartas dos oponentes (via JSON)."""
        my_idx = self._find_own_option_index(options, my_chosen_card)
        valid_indices = [i for i in range(len(options)) if i != my_idx]
        final_votes = []

        prompt = (
            f"Jogo Dixit. Dica: '{clue}'.\n"
            "Escolha as DUAS músicas que MELHOR combinam com a dica.\n\n"
        )
        for i in valid_indices:
            opt = options[i]
            snippet = opt.get("lyrics", "").replace("\n", " ")[:120]
            prompt += f"[{i}] {opt.get('title')} - Letra: {snippet}...\n"

        prompt += "\nResponda APENAS com um objeto JSON válido no formato exato: {\"v\": [num1, num2]}"

        try:
            # Aumentamos o max_tokens para 20 para acomodar uma lista no JSON
            raw_text = await asyncio.wait_for(
                self.llm_generate(prompt, max_tokens=20, temperature=0.1),
                timeout=45.0,
            )
            
            # Extração segura do JSON via regex
            match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                
                if "v" in data and isinstance(data["v"], list):
                    for n_val in data["v"]:
                        if isinstance(n_val, int) and n_val in valid_indices and n_val not in final_votes:
                            final_votes.append(n_val)
                        if len(final_votes) == 2:
                            break

            # Fallback secundário garimpeiro
            if len(final_votes) < 2:
                nums = [int(x) for x in re.findall(r'\b\d\b', raw_text)]
                for n_val in nums:
                    if n_val in valid_indices and n_val not in final_votes:
                        final_votes.append(n_val)
                    if len(final_votes) == 2:
                        break

        except Exception as e:
            logger.warning(f"[{self.name}] Falha na LLM em vote: {e}")

        # Rede de Segurança Férrea
        final_votes = [v for v in final_votes if v in valid_indices]
        
        if len(final_votes) < 2:
            logger.info(f"[{self.name}] Falta de votos válidos da LLM. Completando aleatoriamente.")
            remaining = [i for i in valid_indices if i not in final_votes]
            random.shuffle(remaining)
            final_votes.extend(remaining[: 2 - len(final_votes)])

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