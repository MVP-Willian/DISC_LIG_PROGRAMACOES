from __future__ import annotations
import logging
import re

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


---------------------------------------------------------------------- MICHAEL ----------------------------------------------------------------------

Agente estratégico do jogo *Nota Secreta* — foco no papel de NARRADOR.

==============================================================================
RESUMO DA ESTRATÉGIA (leia antes de mexer)
==============================================================================
O Narrador só pontua quando cai no "Caso B" da regra de pontuação:
ALGUÉM acerta a sua carta, mas NÃO TODO MUNDO. Se ninguém acerta (dica obscura
demais) OU todos acertam (dica óbvia demais), o Narrador recebe 0 e todos os
adversários ganham +2. Logo, o objetivo do Narrador é produzir uma dica de
DIFICULDADE INTERMEDIÁRIA — informativa o bastante para que jogadores atentos
consigam associar, porém abstrata o bastante para que nem todos consigam.

Além de garantir o próprio +3, o Narrador quer MINIMIZAR quantos adversários
acertam, porque cada acertador também ganha +3 "de graça" à custa da sua dica.
Por isso a dica é deliberadamente puxada para o lado mais abstrato/temático
(sem copiar a letra e sem usar o título), e não para o lado literal.

DIVISÃO DE TRABALHO LLM x HEURÍSTICA (decisão de projeto consciente):
- send_clue  -> a decisão SEMÂNTICA por excelência: usamos a LLM para gerar a
                dica (evocação de clima/imagem/sentimento). É onde a LLM agrega
                valor real e onde o enunciado pede uso da LLM.
- choose_card -> decisão ESTRATÉGICA/ESTATÍSTICA: implementada com heurística
                tradicional (sem LLM). É mais robusta, determinística, escala
                para bases grandes e não gasta latência de inferência.
- parsing/saneamento/validação/fallback -> heurística tradicional, porque a
                LLM (especialmente modelos pequenos como Phi-3.5) devolve
                respostas imperfeitas que precisam ser domadas de forma confiável.

INTERFACE PRESERVADA (não alterar nomes/assinaturas — a infra depende disso):
    receive_hand(hand) | choose_card() | send_clue(lyrics, max_words=6)
    select_card_by_clue(clue) | vote(clue, options, my_chosen_card)

OBS.: por instrução do trabalho, as tools do MELÔMANO (select_card_by_clue e
vote) são mantidas como na referência e NÃO são o foco deste arquivo. Todo o
esforço de projeto está no Narrador.

Marco Cristo, 2026 — versão estratégica do Narrador.

"""

import argparse
import asyncio
import random
import json
from collections import Counter
from typing import Any, Dict, List

from base_agent import BaseAgent, STOPWORDS
from fasta2a import A2AApp, tool

app = A2AApp(name="LLMAgent")
logger = logging.getLogger(__name__)
# Regex de tokens "de palavra" em português (mesma família usada no base_agent).
_WORD_RE = re.compile(r"[a-záàâãéêíóôõúç]+")


class LLMAgent(BaseAgent):
    
    # ----------------------- Parâmetros de estratégia ------------------------
    # Todos centralizados aqui para facilitar tuning sem caçar números no código.

    # Tamanho-alvo da dica (em palavras de conteúdo). 3-4 dá o melhor equilíbrio
    # entre "associável" e "não óbvio". Sempre respeitamos o teto max_words.
    CLUE_TARGET_WORDS = 4
    # Mínimo de palavras "úteis" (len>2, não-stopword) para a dica valer.
    CLUE_MIN_MEANINGFUL = 2
    # Quantas palavras da letra entram no prompt (a letra já chega <=80 palavras
    # do GM; cortamos mais para reduzir latência e tentação de copiar a letra).
    LYRICS_PROMPT_WORDS = 50
    # Rejeita a dica se a sobreposição lexical com a letra for alta demais
    # (sinal de cópia/obviedade). Empurra a LLM para o lado temático/abstrato.
    MAX_OVERLAP_RATIO = 0.6

    # Termos clichês de "amor" que tornam uma carta difícil de "cluar" de forma
    # distintiva (43% das letras da base de dev contêm "amor"). Penalizados de
    # forma SUAVE (por densidade, não por mera presença) na escolha da carta.
    _CLICHE = {
        "amor", "amar", "amo", "amada", "amado", "amava", "amando",
        "coração", "coracao", "paixão", "paixao", "querer", "quero",
        "saudade", "saudades", "apaixonado", "apaixonada",
    }

    # Último recurso: frases evocativas genéricas, porém VÁLIDAS (não copiam a
    # letra, têm >=2 palavras de conteúdo, são de dificuldade média). Só entram
    # se a LLM falhar completamente E não houver palavras-chave aproveitáveis.
    _GENERIC_CLUES = [
        "lembrança distante", "silêncio entre versos", "memória em trânsito",
        "eco de outro tempo", "retrato desbotado", "promessa adiada",
    ]

    def __init__(self, name: str, llm_url: str):
        super().__init__(name=name, llm_url=llm_url, request_timeout=60.0)
        self._chosen_card: Dict[str, Any] | None = None

    @tool()
    async def receive_hand(self, hand: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.hand = list(hand)
        return {"status": "ok", "hand_size": len(self.hand)}

    @tool()
    async def choose_card(self) -> Dict[str, Any]:
        """Escolhe, entre as 4 cartas da mão, a mais "cluável".

        Heurística (sem LLM, ver justificativa no topo do arquivo): preferimos a
        carta com vocabulário mais rico/distintivo e tema menos clichê, pois é a
        que permite construir uma dica temática que aponta para ELA de forma
        relativamente única — reduzindo o risco de "ninguém acerta" por culpa de
        cartas-isca parecidas. A dificuldade final é controlada depois, na dica.
        """
        if not self.hand:
            raise RuntimeError("Hand is empty")

        # argmax determinístico; o índice serve de desempate estável.
        best_idx = max(
            range(len(self.hand)),
            key=lambda i: (self._clueability_score(self.hand[i]), -i),
        )
        self._chosen_card = self.hand[best_idx]
        return {"chosen_card": self.hand[best_idx]}

    @tool()
    async def send_clue(self, lyrics: str, max_words: int = 6) -> Dict[str, Any]:
        """Gera a dica para a carta escolhida.

        Pipeline robusto:
          1. monta um prompt focado e com 2 exemplos (few-shot) que ancoram o
             estilo "abstrato/temático, sem copiar a letra, sem o título";
          2. chama a LLM (até 2 tentativas com temperaturas diferentes);
          3. SANEIA a resposta (a LLM pequena erra muito: prefixos, markdown,
             aspas, inglês, excesso de palavras...);
          4. VALIDA a dificuldade (nem cópia literal, nem sobreposição alta);
          5. se nada vingar, cai num FALLBACK heurístico determinístico.
        """
        max_words = self._clamp_max_words(max_words)
        title = self._current_title()
        short_lyrics = " ".join(str(lyrics).split()[: self.LYRICS_PROMPT_WORDS])

        clue = ""
        for temperature in (0.55, 0.85):  # 2ª tentativa só se a 1ª falhar
            prompt = self._build_clue_prompt(short_lyrics, max_words, title)
            raw = await self.llm_generate(
                prompt,
                max_tokens=24,
                temperature=temperature,
                stop=["\n", "Letra", "Letra:", "Dica:", "Exemplo", "###"],
            )
            candidate = self._postprocess_clue(raw, max_words, lyrics, title)
            if self._clue_is_acceptable(candidate, lyrics):
                clue = candidate
                break

        if not self._clue_is_acceptable(clue, lyrics):
            clue = self._heuristic_clue(lyrics, max_words, title)

        # Evita repetir exatamente a dica anterior quando viemos de fallback
        # genérico (com modelo real + temperatura isso quase nunca ocorre).
        if clue in self._GENERIC_CLUES and self.clue_history and clue == self.clue_history[-1]:
            alt = [c for c in self._GENERIC_CLUES if c != clue]
            if alt:
                clue = random.choice(alt)

        clue = " ".join(clue.split()[:max_words]).strip(" .,:;!-\"'“”‘’()[]")
        if not clue:  # blindagem final — jamais devolver dica vazia
            clue = self._GENERIC_CLUES[0]

        self.clue_history.append(clue)
        return {"clue": clue}

    @tool()
    async def select_card_by_clue(self, clue: str) -> Dict[str, Any]:
        """Escolhe qual carta da mão melhor representa a dica do narrador.

        Monta um prompt curto contendo a dica e os trechos iniciais de cada 
        letra disponível na mão, instruindo a LLM a devolver APENAS um JSON 
        estrito com o índice escolhido. Como os modelos tendem a ser faladores 
        (adicionando textos como "Aqui está o JSON..."), usamos regex para 
        tentar extrair apenas o bloco de dados. Se a extração falhar, aplica 
        um fallback secundário que procura qualquer número isolado na resposta. 
        Se nem assim conseguirmos uma resposta válida (ou houver timeout), 
        loga um aviso e escolhe uma carta aleatória, garantindo que o agente 
        nunca trave o andamento da partida."""
        
        if not self.hand:
            logger.warning(f"[{self.name}] Mão vazia recebida.")
            raise RuntimeError("Hand is empty")

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
        """Vota nas cartas dos oponentes que melhor combinam com a dica do narrador.

        Primeiro, utiliza a função auxiliar para identificar e excluir a nossa 
        própria carta das opções, evitando votos inválidos. Envia os trechos 
        das músicas restantes para a LLM pedindo um JSON com dois votos.
        Assim como na escolha de cartas, tenta forçar a extração via regex 
        para ignorar alucinações de texto do modelo. Possui uma rede de 
        segurança férrea em camadas: garimpa números brutos caso o JSON venha 
        quebrado, filtra qualquer tentativa da LLM de votar em índices 
        inexistentes ou na própria carta e, em último caso, completa os votos 
        faltantes de forma aleatória. Isso garante máxima resiliência na competição.
        """
        
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

    # ----------------------- Métodos auxiliares de estratégia -----------------------
    
    # NARRADOR ----------------------------------------------------------------------
  
    def _content_tokens(self, text: str) -> List[str]:
        """Tokens de conteúdo (len>2, fora das stopwords), COM repetições."""
        toks = _WORD_RE.findall((text or "").lower())
        return [t for t in toks if len(t) > 2 and t not in STOPWORDS]

    def _clueability_score(self, song: Dict[str, Any]) -> float:
        """Pontua o quão boa uma carta é para o Narrador "cluar".

        Combina (tudo calculado SÓ a partir do texto da própria carta — não
        precisa de corpus global, logo escala para a base grande do torneio):
          - unique_ratio : diversidade lexical (mais imagens distintas);
          - distinct_score: fração de palavras longas/concretas (proxy de
                            especificidade — palavras funcionais são curtas);
          - length_score : material suficiente para extrair um tema (satura);
          - title_bonus  : título informativo ajuda como âncora temática;
          - generic_pen. : penalidade SUAVE por densidade de clichês de amor.
        """
        toks = self._content_tokens(song.get("lyrics", ""))
        n = len(toks)
        if n == 0:
            return float("-inf")

        uniq = set(toks)
        unique_ratio = len(uniq) / n
        length_score = min(n, 20) / 20.0
        long_words = sum(1 for w in uniq if len(w) >= 6)
        distinct_score = long_words / max(1, len(uniq))
        cliche_hits = sum(1 for w in toks if w in self._CLICHE)
        generic_penalty = cliche_hits / n
        title_bonus = 0.05 if self._content_tokens(song.get("title", "")) else 0.0

        return (
            0.45 * unique_ratio
            + 0.35 * distinct_score
            + 0.20 * length_score
            + title_bonus
            - 0.30 * generic_penalty
        )

    def _build_clue_prompt(self, lyrics: str, max_words: int, title: str) -> str:
        """Prompt enxuto, em PT-BR, com 2 exemplos que fixam o estilo desejado.

        Exemplos são genéricos de propósito (não dependem de músicas reais), só
        servem para ancorar: dica curta, abstrata, evocando clima/imagem, sem
        copiar a letra e sem o título.
        """
        return (
            "Tarefa: criar uma DICA curta para um jogo de adivinhação de músicas "
            "(estilo Dixit). A dica deve evocar o clima, a imagem ou o sentimento "
            "da letra de forma poética e indireta.\n"
            "Regras:\n"
            f"- No máximo {max_words} palavras (ideal: 3 a 4).\n"
            "- NÃO copie palavras da letra e NÃO use o título.\n"
            "- Nem óbvia demais, nem vaga demais: quem presta atenção deve "
            "conseguir associar, mas não todo mundo.\n"
            "- Responda apenas com a dica, em português, sem aspas e sem explicar.\n\n"
            "Letra: o trem parte de madrugada, deixo a cidade pequena pra trás, "
            "levo a viola e o que não cabe na mala\n"
            "Dica: partida silenciosa ao amanhecer\n\n"
            "Letra: bate o tambor, o corpo se solta no meio da multidão, "
            "a tristeza fica para depois\n"
            "Dica: euforia coletiva de fevereiro\n\n"
            f"Letra: {lyrics}\n"
            "Dica:"
        )

    def _postprocess_clue(self, raw: str, max_words: int, lyrics: str, title: str) -> str:
        """Limpa a saída crua da LLM SEM aplicar fallback (o fallback é externo,
        para mantermos o controle do pipeline)."""
        clue = (raw or "").replace("\n", " ").strip()

        # Remove prefixos tipo "Dica:", "Resposta:" no começo.
        clue = re.sub(r"^(dica|clue|resposta|response|answer)\s*:\s*", "", clue, flags=re.IGNORECASE)
        # Corta qualquer continuação "Resposta:/Answer:" no meio.
        clue = re.split(r"\b(?:resposta|response|answer)\s*:", clue, maxsplit=1, flags=re.IGNORECASE)[0]
        # Remove marcadores markdown soltos (#, *, _, crases) e normaliza espaços.
        clue = re.sub(r"[#*_`]+", " ", clue)
        clue = re.sub(r"\s+", " ", clue).strip(" .,:;!-\"'“”‘’()[]*_`")

        words = clue.split()[:max_words]
        # Remove restos de meta-vocabulário que a LLM às vezes deixa.
        banned = {"answer", "response", "resposta", "clue", "dica", "letra", "música", "musica"}
        words = [w for w in words if w.lower().strip(".,:;!-") not in banned]

        # Remove palavras idênticas a palavras de conteúdo do TÍTULO: evita que
        # adversários que casam dica<->título acertem trivialmente (o que nos
        # jogaria para "todo mundo acerta"). Só remove se sobrar conteúdo.
        title_set = set(self._content_tokens(title))
        if title_set:
            kept = [w for w in words if re.sub(r"[^a-záàâãéêíóôõúç]", "", w.lower()) not in title_set]
            if sum(1 for w in kept if len(re.sub(r"[^a-záàâãéêíóôõúç]", "", w.lower())) > 2) >= self.CLUE_MIN_MEANINGFUL:
                words = kept

        return " ".join(words[:max_words]).strip(" .,:;!-\"'“”‘’()[]")

    def _clue_is_acceptable(self, clue: str, lyrics: str) -> bool:
        """A dica está no "ponto" (nem cópia, nem pobre, nem óbvia demais)?"""
        if not clue:
            return False
        toks = set(self._content_tokens(clue))
        if len(toks) < self.CLUE_MIN_MEANINGFUL:
            return False
        # Cópia literal de trecho da letra -> fácil demais.
        if self._is_literal_substring_of_lyrics(clue, lyrics):
            return False
        # Sobreposição lexical alta com a letra -> também fácil demais.
        lyric_set = set(self._content_tokens(lyrics))
        if lyric_set:
            overlap = sum(1 for w in toks if w in lyric_set) / len(toks)
            if overlap > self.MAX_OVERLAP_RATIO:
                return False
        return True

    def _heuristic_clue(self, lyrics: str, max_words: int, title: str) -> str:
        """Fallback determinístico quando a LLM falha.

        Monta uma dica com as palavras MAIS DISTINTIVAS da letra (raras dentro da
        própria letra + longas), excluindo as do título. Não é abstrata, mas é
        válida e conecta — e só roda quando a LLM realmente quebrou.
        """
        title_set = set(self._content_tokens(title))
        toks = self._content_tokens(lyrics)
        freq = Counter(toks)

        # palavras únicas preservando ordem de aparição, sem as do título
        cand = [w for w in dict.fromkeys(toks) if w not in title_set]
        # ordena por (menos frequente, depois mais longa)
        cand.sort(key=lambda w: (freq[w], -len(w)))

        picked: List[str] = []
        for w in cand:
            if len(w) >= 4 and w not in picked:
                picked.append(w)
            if len(picked) >= min(3, max_words):
                break

        clue = " ".join(picked).strip()
        toks_clue = self._content_tokens(clue)
        if len(toks_clue) >= self.CLUE_MIN_MEANINGFUL and not self._is_literal_substring_of_lyrics(clue, lyrics):
            return clue
        return random.choice(self._GENERIC_CLUES)

    def _clamp_max_words(self, max_words: Any) -> int:
        try:
            mw = int(max_words)
        except Exception:
            mw = 6
        return max(self.CLUE_MIN_MEANINGFUL, min(mw, 6))

    def _current_title(self) -> str:
        if self._chosen_card and isinstance(self._chosen_card, dict):
            return self._chosen_card.get("title", "") or ""
        return ""
    
    
    # MELÔMANO ----------------------------------------------------------------------

    def _normalize_words(self, text: str) -> set[str]:
        # normaliza palavras no texto e devolve como um conjunto
        cleaned = []
        for token in text.lower().split():
            token = "".join(ch for ch in token if ch.isalnum())
            if token:
                cleaned.append(token)
        return set(cleaned)


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
