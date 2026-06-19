# Nota Secreta

Este projeto contém uma **versão comentada e simplificada** do jogo **Nota Secreta**,
usada como base para a implementação do agente estratégico da disciplina.

A ideia é que você possa:

- entender a arquitetura do sistema;
- rodar partidas localmente;
- testar seu agente em modo mock ou com um modelo real;
- modificar principalmente `llm_agent.py` e, se desejar, `base_agent.py`.

## Integrantes do grupo

- Michael Willian Pereira Vieira
- Lucas de Souza Cerveira Pereira
- Mikaelle Costa de Santana

---

## 1. Visão geral da arquitetura

O projeto combina dois estilos de comunicação:

- **REST/FastAPI** entre os agentes e o serviço LLM centralizado (`llm_service.py`);
- **A2A / JSON-RPC** entre o Game Master e os agentes.

Em uma execução típica:

1. o `run_game.py` sobe o serviço LLM;
2. sobe o `game_master.py`;
3. sobe 1 agente estratégico e 5 agentes aleatórios;
4. registra os agentes no Game Master;
5. executa uma partida completa;
6. salva um log da partida em `logs/`.

---

## 2. Estrutura dos arquivos

Arquivos principais:

- `fasta2a.py`: mini-implementação de `A2AApp` e `@tool`
- `base_agent.py`: utilidades comuns para agentes
- `llm_service.py`: serviço LLM centralizado (real ou mock)
- `game_master.py`: coordenação da partida, votação, pontuação e logs
- `llm_agent.py`: agente estratégico a ser estudado e modificado
- `random_agent.py`: baseline aleatório
- `run_game.py`: sobe tudo e executa uma partida completa
- `render_log_readable.py`: transforma logs em uma visualização mais legível
- `brazilian_songs.csv`: base de músicas usada pelo jogo
- `tests/`: testes auxiliares

---

## 3. O que você deve modificar

Em geral, os arquivos mais importantes para o aluno são:

- `llm_agent.py`
- `base_agent.py` (opcional)

Você pode reorganizar a lógica interna do agente, desde que preserve a interface esperada
pelo restante da infraestrutura.

As ferramentas (tools) esperadas do agente são:

- `receive_hand(hand)`
- `choose_card()`
- `send_clue(lyrics, max_words=6)`
- `select_card_by_clue(clue)`
- `vote(clue, options, my_chosen_card)`

---

## 4. Instalação

Crie e ative um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:

```bash
python3 -m pip install -r requirements.txt
```

---

## 5. Execução rápida

### 5.1. Rodar em modo mock

Esse modo não usa um modelo real e é útil para validar rapidamente a arquitetura:

```bash
python3 run_game.py --force-mock
```

### 5.2. Rodar com um modelo GGUF real

```bash
python3 run_game.py --model /caminho/do/modelo.gguf
```

Exemplo:

```bash
python3 run_game.py --model ~/Documentos/LLM/Phi-3.5-mini-instruct-Q4_K_M.gguf
```

---

## 6. Opções úteis do `run_game.py`

### Subir 6 agentes estratégicos

```bash
python3 run_game.py --all-strategic --force-mock
```

ou:

```bash
python3 run_game.py --all-strategic --model /caminho/do/modelo.gguf
```

### Alterar a base de músicas

```bash
python3 run_game.py --db outra_base.csv --force-mock
```

### Ajustar concorrência do serviço LLM

```bash
python3 run_game.py --model /caminho/do/modelo.gguf --llm-max-concurrency 1
```

---

## 7. Logs

Ao final da partida, o Game Master salva um log JSON em:

```text
logs/
```

O caminho do log também é mostrado no terminal ao fim da execução.

Esses logs ajudam a entender:

- qual agente foi narrador em cada rodada;
- qual dica foi produzida;
- quais cartas foram jogadas;
- como os votos foram distribuídos;
- como a pontuação evoluiu ao longo da partida.

---

## 8. Como ler os logs

Para transformar um log em uma visualização mais legível:

```bash
python3 render_log_readable.py logs/partida_xxx.json
```

---

## 9. Observações sobre a base de músicas

A base CSV deve conter, no mínimo, as colunas:

- `id`
- `title`
- `artist`
- `lyrics`

A base fornecida aqui serve para testes e desenvolvimento local.
Na avaliação, vai ser usada uma base oficial definida pelo professor.

---

## 10. Objetivo pedagógico

O foco deste trabalho não é apenas “fazer um agente funcionar”, mas construir
um **sistema multiagente baseado em LLM**.

Por isso, espera-se que o agente:

- use a LLM para decisões semânticas;
- lide com respostas imperfeitas de forma robusta;
- preserve o protocolo esperado pela infraestrutura.

Em outras palavras:

> a implementação interna pode variar, mas a interface externa do agente deve continuar compatível.

---

## 11. Resumo

Use esta versão do projeto para:

- entender a arquitetura;
- rodar testes locais;
- modificar o agente estratégico;
- experimentar diferentes prompts e estratégias.

Fluxo mínimo recomendado:

1. rodar `python3 run_game.py --force-mock`
2. rodar `python3 run_game.py --model ...`
3. inspecionar os logs
4. modificar `llm_agent.py`
5. repetir os testes

---

## 12. Agente estratégico: o Narrador

> Esta seção documenta **apenas o papel de Narrador** (`choose_card` e `send_clue`)
> do agente em `llm_agent.py`. As tools de Melômano não são abordadas aqui.

### 12.1. Estratégia

Pela regra de pontuação do Dixit, o Narrador só pontua no chamado **Caso B**:
*alguém* acerta a sua carta, mas *não todos*. Se ninguém acerta (dica obscura
demais) **ou** todos acertam (dica óbvia demais), o Narrador recebe **0** e cada
adversário ganha **+2**. Como cada acertador ainda ganha **+3** à custa da dica,
o agente busca uma dica de **dificuldade intermediária** e de caráter
**temático/abstrato** — evocando clima, imagem ou sentimento, sem copiar a letra
e sem usar o título. Esse é o critério que orienta toda a implementação.

### 12.2. Divisão LLM × heurística

- **`send_clue` → LLM.** A geração da dica é a decisão semântica central do
  Narrador; é onde a LLM agrega valor real e onde o enunciado pede o uso do
  modelo no núcleo das decisões.
- **`choose_card` → heurística determinística (sem LLM).** A escolha da carta é
  uma decisão estatística; resolvê-la por heurística é mais robusto, não gasta
  latência de inferência e escala para bases grandes. O enunciado permite
  explicitamente heurísticas auxiliares.
- **Saneamento, validação e fallback → heurística.** Modelos pequenos (Phi-3.5)
  produzem saídas imperfeitas que precisam ser tratadas de forma confiável.

### 12.3. Escolha da carta (`choose_card`)

A carta é escolhida pela função `_clueability_score`, que mede o quão "cluável"
é cada carta usando **apenas o texto da própria carta** (sem corpus global). A
pontuação combina:

- **diversidade lexical**: palavras distintas / total (peso **0,45**);
- **especificidade**: fração de palavras longas (≥ 6 letras), proxy de palavras
  concretas (peso **0,35**);
- **material suficiente**: quantidade de palavras de conteúdo, saturando em 20
  (peso **0,20**);
- **bônus de título**: informativo como âncora temática (peso **0,05**);
- **penalidade suave**: por densidade de clichês de amor (peso **−0,30**).

A escolha é o `argmax` determinístico desses valores, com desempate estável por
índice. A pontuação de cada carta é isolada por `try/except`: uma carta
malformada não impede a decisão.

### 12.4. Geração da dica (`send_clue`)

O método segue um pipeline tolerante a falhas:

1. **Prompt** curto em português, com duas instâncias *few-shot* genéricas que
   fixam o estilo desejado. As regras passadas ao modelo são:

   ```text
   - No máximo {max_words} palavras (ideal: 3 a 4).
   - NÃO copie palavras da letra e NÃO use o título.
   - Nem óbvia demais, nem vaga demais: quem presta atenção deve
     conseguir associar, mas não todo mundo.
   - Responda apenas com a dica, em português, sem aspas e sem explicar.
   ```

   A letra é truncada para 50 palavras antes de entrar no prompt (a letra já
   chega ≤ 80 palavras do Game Master), reduzindo latência e a tentação de copiar.

2. **Consulta à LLM** em até duas tentativas, com temperaturas distintas (0,55 e
   0,85) — a segunda só ocorre se a primeira não passar na validação. Usa
   `max_tokens=24` (dentro da faixa recomendada de 20–35) e sequências de
   `stop` para conter modelos "faladores".

3. **Saneamento** da saída crua: remoção de prefixos (`Dica:`, `Resposta:`…),
   marcadores de markdown, aspas e meta-vocabulário; corte no teto de palavras; e
   remoção de palavras iguais às do título (para evitar que adversários casem
   dica ↔ título e acertem trivialmente, o que levaria ao Caso A).

4. **Validação de dificuldade**: a dica é rejeitada se for vazia/curta demais, se
   for cópia literal de um trecho da letra, ou se a sobreposição lexical com a
   letra ultrapassar **0,6**, empurrando a dica para o lado temático.

5. **Fallback determinístico**: se nenhuma tentativa vinga, a dica é montada com
   as palavras mais distintivas da letra (raras na própria letra e mais longas),
   excluindo as do título. Em último caso, recorre a frases evocativas genéricas,
   evitando repetir a dica anterior.

**Garantias do método:** `send_clue` nunca propaga exceção, nunca devolve dica
vazia e nunca excede `max_words` — requisitos de robustez e de protocolo.

### 12.5. Robustez e generalização

- Todas as etapas (chamadas à LLM e helpers) são protegidas por `try/except`; há
  `request_timeout=60s` e o cliente de LLM herdado de `base_agent` faz cache de
  prompts repetidos.
- O teto `max_words` é tratado como **restrição inegociável**: a saída é limitada
  a `[1, 6]` palavras e o mínimo de palavras úteis se adapta ao teto.
- A tokenização de palavras usa um casador **Unicode**, resistente a acentos e
  grafias incomuns — importante porque a base do torneio é uma amostra de uma
  coleção bem maior (~146 mil letras), mais heterogênea que a de desenvolvimento.
- Nenhuma decisão usa corpus global nem músicas fixas no código: o comportamento
  e o custo não mudam quando a base é maior ou diferente. A penalidade de clichê é
  suave (por densidade), não uma regra rígida ajustada à base de testes.
- O código usa *type hints* e `async/await`, e centraliza os parâmetros de
  estratégia como constantes da classe, facilitando ajuste fino.

---

## 13. Exemplo de saída: rodadas do Narrador

Ao final de uma partida, o terminal exibe o placar e o caminho do log:

```text
Final scores: [30, 24, 19, 28, 18, 26]
Winner: 0
Total rounds: 8
Log file: logs/partida_AAAAMMDD_HHMMSS.json
```

A seguir, duas rodadas em que o **agente 0 (`LLMAgent_1`) é o Narrador**, no
formato do `render_log_readable.py`. As colunas `0`–`5` indicam **qual jogador
votou** em cada carta (o Narrador não vota); `Pts` é a pontuação do dono da carta
na rodada. *Exemplo ilustrativo do formato de saída — as dicas exatas dependem da
saída do Phi-3.5 e variam por música; em modo `--force-mock` o serviço emite uma
dica-placeholder fixa.*

```text
round 3
Clue (agent 0 - LLMAgent_1): "partida silenciosa ao amanhecer"
id  card_id  title              0  1  2  3  4  5  Pts
0   181      Por Onde Andei        x        x     3     <- carta do Narrador (Caso B: +3)
1   119      Sereia                      x           1
2   49       A Sua              x     x              3
3   61       Exagerado                x        x     2
4   97       Preciso Dizer                        x  1
5   172      Sá Marina             x                 2
```

Na rodada 3, **2 dos 5** melômanos votaram na carta do Narrador — alguns, mas não
todos. É o **Caso B**: o Narrador ganha **+3**. Esse é o resultado-alvo da
estratégia.

```text
round 7
Clue (agent 0 - LLMAgent_1): "euforia coletiva de fevereiro"
id  card_id  title              0  1  2  3  4  5  Pts
0   53       Disritmia             x  x  x  x  x  0     <- carta do Narrador (Caso A: 0)
1   220      Magrelinha                           1
2   37       Ando Meio Desligado   x        x     3
3   227      Vapor Barato                   x     1
4   224      Fátima                               0
5   169      Malemolência          x  x           3
```

Na rodada 7, **todos os 5** melômanos acertaram, dica óbvia demais. É o
**Caso A**: o Narrador recebe **0** e cada adversário ganha +2. Comparar as duas
rodadas evidencia por que a dica precisa ser de dificuldade intermediária.

---

## 14. Dificuldades encontradas e soluções (Narrador)

- **Saídas imperfeitas do modelo pequeno.** O Phi-3.5 frequentemente devolve
  prefixos, markdown, texto em inglês ou explicações extras. *Solução:* pipeline
  de saneamento + validação, com fallback heurístico quando a saída é inutilizável.

- **Calibrar a dificuldade da dica.** Uma dica boa não pode ser óbvia/cópia (todos
  acertam → Caso A) nem vaga (ninguém acerta → Caso A). *Solução:* rejeição de
  cópia literal e de sobreposição lexical > 0,6, alvo de 3–4 palavras e estilo
  temático induzido por *few-shot*.

- **Vazamento de título/letra.** Repetir o título na dica permitiria que
  adversários casassem dica ↔ título trivialmente. *Solução:* remoção das palavras
  do título no saneamento, desde que reste conteúdo suficiente.

- **Robustez a falhas e latência da LLM.** Uma exceção na chamada ao modelo
  derrubaria a rodada. *Solução:* `try/except` em todas as etapas, `timeout` e
  fallback determinístico; a tool nunca quebra nem devolve dica vazia.

- **Conformidade com o teto de palavras.** O limite `max_words` é uma restrição do
  enunciado. *Solução:* o teto é tratado como absoluto (`[1, 6]`) e o mínimo de
  palavras úteis se adapta a ele.

- **Generalização para a base do torneio.** A base oficial é maior e diferente.
  *Solução:* features calculadas apenas a partir da própria carta (sem corpus
  global nem músicas fixas) e tokenizador Unicode para grafias heterogêneas.

- **Validação sem depender do modelo real.** Para testar o Narrador de forma
  isolada, foram usados testes de unidade (saneamento, validação, fallback,
  conformidade de teto) e partidas completas em modo `--force-mock`, garantindo a
  integração com o Game Master independentemente da disponibilidade do modelo.
