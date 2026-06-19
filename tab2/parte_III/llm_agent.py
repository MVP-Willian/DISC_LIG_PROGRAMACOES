
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import random
import re
from collections import Counter
from typing import Any, Dict, List
 
from base_agent import BaseAgent, STOPWORDS
from fasta2a import A2AApp, tool
 
app = A2AApp(name="LLMAgent")
logger = logging.getLogger(__name__)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
 
 
class LLMAgent(BaseAgent):
 
    # ----------------------------- Parâmetros -------------------------------
    # Centralizados para facilitar ajuste fino sem caçar números no código.
 
    # Tamanho-alvo da dica, em palavras de conteúdo (o teto max_words é sempre
    # respeitado). 3-4 equilibra "associável" e "não óbvio".
    CLUE_TARGET_WORDS = 4
    # Mínimo desejável de palavras úteis (len>2, não-stopword) para a dica valer.
    # É reduzido automaticamente se max_words for menor.
    CLUE_MIN_MEANINGFUL = 2
    # Palavras da letra enviadas no prompt (a letra já chega <=80 palavras do
    # Game Master; reduzir mais corta latência e reduz a tentação de copiar).
    LYRICS_PROMPT_WORDS = 50
    # Acima desta fração de sobreposição lexical com a letra a dica é rejeitada
    # por ser óbvia/copiada, empurrando a geração para o lado temático.
    MAX_OVERLAP_RATIO = 0.6
 
    # Clichês de "amor" que tornam uma carta difícil de individualizar.
    # Penalizados de forma suave (por densidade) na escolha da carta.
    _CLICHE = {
        "amor", "amar", "amo", "amada", "amado", "amava", "amando",
        "coração", "coracao", "paixão", "paixao", "querer", "quero",
        "saudade", "saudades", "apaixonado", "apaixonada",
    }
 
    # Frases genéricas e válidas (não copiam letra, têm >=2 palavras
    # de conteúdo, dificuldade média). Último recurso, quando a LLM falha e não
    # há palavras-chave aproveitáveis na letra.
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
 
    # =============================== NARRADOR ===============================
 
    @tool()
    async def choose_card(self) -> Dict[str, Any]:
        """Escolhe, entre as cartas da mão, a mais "cluável".
 
        Prefere a carta com vocabulário mais rico/distintivo e tema menos
        clichê, a que permite uma dica temática apontando para ela de forma
        relativamente única, reduzindo o risco de "ninguém acerta". A pontuação
        usa apenas o texto da carta; a dificuldade final é ajustada na dica.
 
        A pontuação de cada carta é isolada por try/except: uma carta malformada
        não impede a escolha. O desempate por índice mantém o resultado
        determinístico.
        """
        if not self.hand:
            raise RuntimeError("Hand is empty")
 
        def score(i: int) -> tuple[float, int]:
            try:
                return (self._clueability_score(self.hand[i]), -i)
            except Exception:
                return (float("-inf"), -i)
 
        best_idx = max(range(len(self.hand)), key=score)
        self._chosen_card = self.hand[best_idx]
        return {"chosen_card": self.hand[best_idx]}
 
    @tool()
    async def send_clue(self, lyrics: str, max_words: int = 6) -> Dict[str, Any]:
        """Gera a dica da carta escolhida.
 
        Pipeline tolerante a falhas:
          1. monta um prompt curto com dois exemplos (few-shot) que fixam o
             estilo abstrato/temático;
          2. consulta a LLM em até duas tentativas (temperaturas distintas, que
             também evitam reuso de cache entre elas);
          3. saneia a saída (prefixos, markdown, aspas, meta-tokens, excesso);
          4. valida a dificuldade (rejeita cópia literal e sobreposição alta);
          5. recorre a um fallback heurístico determinístico se nada vingar.
 
        Qualquer exceção em uma tentativa é contida; a tool nunca propaga erro e
        nunca devolve dica vazia ou acima do teto max_words.
        """
        max_words = self._clamp_max_words(max_words)
        min_meaningful = min(self.CLUE_MIN_MEANINGFUL, max_words)
        title = self._current_title()
        short_lyrics = " ".join(str(lyrics).split()[: self.LYRICS_PROMPT_WORDS])
 
        clue = ""
        for temperature in (0.55, 0.85):
            try:
                prompt = self._build_clue_prompt(short_lyrics, max_words, title)
                raw = await self.llm_generate(
                    prompt,
                    max_tokens=24,
                    temperature=temperature,
                    stop=["\n", "Letra", "Letra:", "Dica:", "Exemplo", "###"],
                )
                candidate = self._postprocess_clue(raw, max_words, lyrics, title)
            except Exception as e:
                logger.warning(f"[{self.name}] Falha ao gerar dica via LLM: {e}")
                candidate = ""
            if self._clue_is_acceptable(candidate, lyrics, min_meaningful):
                clue = candidate
                break
 
        if not self._clue_is_acceptable(clue, lyrics, min_meaningful):
            try:
                clue = self._heuristic_clue(lyrics, max_words, title)
            except Exception as e:
                logger.warning(f"[{self.name}] Falha no fallback heurístico: {e}")
                clue = self._GENERIC_CLUES[0]
 
        # Evita repetir literalmente o último fallback genérico.
        if clue in self._GENERIC_CLUES and self.clue_history and clue == self.clue_history[-1]:
            alt = [c for c in self._GENERIC_CLUES if c != clue]
            if alt:
                clue = random.choice(alt)
 
        clue = " ".join(clue.split()[:max_words]).strip(" .,:;!-\"'“”‘’()[]")
        if not clue:  
            clue = self._GENERIC_CLUES[0]
 
        self.clue_history.append(clue)
        return {"clue": clue}
 
    # =============================== MELÔMANO ===============================
 
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
        encontrar, por exemplo, se a chave vier nomeada diferente,
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
 
    # ===================== Métodos auxiliares (Narrador) =====================
 
    def _content_tokens(self, text: str) -> List[str]:
        """Palavras de conteúdo (len>2, fora das stopwords), com repetições."""
        toks = _WORD_RE.findall((text or "").lower())
        return [t for t in toks if len(t) > 2 and t not in STOPWORDS]
 
    def _canonical_word(self, word: str) -> str:
        """Reduz uma palavra à sua forma canônica (apenas letras, minúsculas)."""
        return "".join(_WORD_RE.findall((word or "").lower()))
 
    def _clueability_score(self, song: Dict[str, Any]) -> float:
        """Quão boa é uma carta para o Narrador "cluar".
 
        Combina, usando apenas o texto da carta (sem corpus global, logo escala
        para a base do torneio):
          - unique_ratio  : diversidade lexical (mais imagens distintas);
          - distinct_score: fração de palavras longas/concretas (especificidade);
          - length_score  : material suficiente para extrair um tema (satura);
          - title_bonus   : título informativo serve de âncora temática;
          - generic_pen.  : penalidade suave por densidade de clichês de amor.
        """
        toks = self._content_tokens(song.get("lyrics", ""))
        n = len(toks)
        if n == 0:
            return float("-inf")
 
        uniq = set(toks)
        unique_ratio = len(uniq) / n
        length_score = min(n, 20) / 20.0
        long_words = sum(1 for w in uniq if len(w) >= 6)
        distinct_score = long_words / len(uniq)
        generic_penalty = sum(1 for w in toks if w in self._CLICHE) / n
        title_bonus = 0.05 if self._content_tokens(song.get("title", "")) else 0.0
 
        return (
            0.45 * unique_ratio
            + 0.35 * distinct_score
            + 0.20 * length_score
            + title_bonus
            - 0.30 * generic_penalty
        )
 
    def _build_clue_prompt(self, lyrics: str, max_words: int, title: str) -> str:
        """Prompt enxuto, em PT-BR, com dois exemplos que fixam o estilo.
 
        Os exemplos são genéricos (não dependem de músicas reais) e servem
        apenas para ancorar o formato: dica curta, abstrata, evocando clima ou
        imagem, sem copiar a letra e sem o título.
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
 
    def _postprocess_clue(self, raw: Any, max_words: int, lyrics: str, title: str) -> str:
        """Saneia a saída crua da LLM, sem aplicar fallback (feito externamente)."""
        clue = str(raw or "").replace("\n", " ").strip()
 
        # Remove prefixos como "Dica:"/"Resposta:" e cortes de continuação.
        clue = re.sub(r"^(dica|clue|resposta|response|answer)\s*:\s*", "", clue, flags=re.IGNORECASE)
        clue = re.split(r"\b(?:resposta|response|answer)\s*:", clue, maxsplit=1, flags=re.IGNORECASE)[0]
        # Remove marcadores markdown soltos e normaliza espaços/pontuação de borda.
        clue = re.sub(r"[#*_`]+", " ", clue)
        clue = re.sub(r"\s+", " ", clue).strip(" .,:;!-\"'“”‘’()[]*_`")
 
        words = clue.split()[:max_words]
        # Remove meta-vocabulário que a LLM às vezes deixa.
        banned = {"answer", "response", "resposta", "clue", "dica", "letra", "música", "musica"}
        words = [w for w in words if w.lower().strip(".,:;!-") not in banned]
 
        # Remove palavras iguais às do título: evita que adversários que casam
        # dica<->título acertem trivialmente (o que levaria a "todos acertam").
        # Só aplica se ainda restarem palavras úteis suficientes.
        title_set = set(self._content_tokens(title))
        if title_set:
            kept = [w for w in words if self._canonical_word(w) not in title_set]
            useful = sum(1 for w in kept if len(self._canonical_word(w)) > 2)
            if useful >= min(self.CLUE_MIN_MEANINGFUL, max_words):
                words = kept
 
        return " ".join(words[:max_words]).strip(" .,:;!-\"'“”‘’()[]")
 
    def _is_literal_substring_of_lyrics(self, clue: str, lyrics: str) -> bool:
        """True se a dica aparece como trecho contíguo da letra (cópia literal)."""
        norm_clue = re.sub(r"\s+", " ", (clue or "").lower()).strip()
        if len(norm_clue) < 3:
            return False
        norm_lyrics = re.sub(r"\s+", " ", str(lyrics or "").lower())
        return norm_clue in norm_lyrics
 
    def _clue_is_acceptable(self, clue: str, lyrics: str, min_meaningful: int | None = None) -> bool:
        """A dica está no ponto: nem vazia/pobre, nem cópia, nem óbvia demais."""
        if min_meaningful is None:
            min_meaningful = self.CLUE_MIN_MEANINGFUL
        if not clue:
            return False
        toks = set(self._content_tokens(clue))
        if len(toks) < min_meaningful:
            return False
        if self._is_literal_substring_of_lyrics(clue, lyrics):
            return False
        lyric_set = set(self._content_tokens(lyrics))
        if lyric_set:
            overlap = sum(1 for w in toks if w in lyric_set) / len(toks)
            if overlap > self.MAX_OVERLAP_RATIO:
                return False
        return True
 
    def _heuristic_clue(self, lyrics: str, max_words: int, title: str) -> str:
        """Fallback determinístico quando a LLM falha.
 
        Monta a dica com as palavras mais distintivas da letra (raras na própria
        letra e mais longas), excluindo as do título. É menos abstrata que a
        ideal, mas válida e conectada e só roda quando a LLM realmente falha.
        """
        title_set = set(self._content_tokens(title))
        toks = self._content_tokens(lyrics)
        freq = Counter(toks)
 
        # Palavras únicas (ordem de aparição), sem as do título.
        cand = [w for w in dict.fromkeys(toks) if w not in title_set]
        # Mais distintivas primeiro: menos frequentes e mais longas.
        cand.sort(key=lambda w: (freq[w], -len(w)))
 
        picked: List[str] = []
        for w in cand:
            if len(w) >= 4:
                picked.append(w)
            if len(picked) >= min(3, max_words):
                break
 
        clue = " ".join(picked).strip()
        if (
            len(self._content_tokens(clue)) >= min(self.CLUE_MIN_MEANINGFUL, max_words)
            and not self._is_literal_substring_of_lyrics(clue, lyrics)
        ):
            return clue
        return random.choice(self._GENERIC_CLUES)
 
    def _clamp_max_words(self, max_words: Any) -> int:
        """Limita max_words a [1, 6]; o teto do Game Master nunca é excedido."""
        try:
            mw = int(max_words)
        except Exception:
            mw = 6
        return max(1, min(mw, 6))
 
    def _current_title(self) -> str:
        """Título da carta escolhida nesta rodada (ou "" se indisponível)."""
        if isinstance(self._chosen_card, dict):
            return self._chosen_card.get("title", "") or ""
        return ""
 
    # =============================== MELÔMANO ===============================
 
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