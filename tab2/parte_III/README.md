# Nota Secreta — Agente Estratégico LLM

Este projeto contém a implementação de um agente estratégico autônomo para o jogo **Nota Secreta** (uma variação de Dixit com músicas brasileiras). O sistema utiliza uma arquitetura híbrida, combinando um modelo de linguagem local (Phi-3.5-mini-instruct) com heurísticas determinísticas e múltiplos mecanismos de *fallback*, garantindo robustez mesmo diante de respostas inválidas, alucinações ou indisponibilidade temporária da LLM.

## 1. Integrantes do Grupo
* Lucas de Souza Cerveira Pereira
* Mikaelle Costa de Santana
* Michael Willian Pereira Vieira

---

## 2. Instruções de instalação

*As instruções de instalação são as mesmas fornecidas na arquitetura base do professor.*

1. Acesse a pasta do projeto contendo o `llm_agent.py`.
2. Crie e ative um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Certifique-se de baixar o modelo LLM (`Phi-3.5-mini-instruct-Q4_K_M.gguf`) e colocá-lo em um diretório acessível.

---

## 3. Como executar o código

O projeto pode ser executado através do orquestrador `run_game.py`.

**Modo Mock (sem carregar a LLM):**

```bash
python3 run_game.py --force-mock
```

**Modo completo (modelo real):**

```bash
python3 run_game.py --model /caminho/absoluto/para/o/Phi-3.5-mini-instruct-Q4_K_M.gguf
```

O script iniciará automaticamente:

- Game Master;
- Serviço da LLM;
- Nosso agente estratégico;
- Cinco agentes aleatórios.

---

## 4. Exemplo de saída esperada

Abaixo está o resumo de uma rodada operando normalmente, extraído e formatado visualmente a partir dos logs JSON gerados pelo Game Master:

```text
Letras
id  type       name           card_id  title                            lyrics                                                                          
--  ---------  -------------  -------  -------------------------------  --------------------------------------------------------------------------------
0   strategic  LLMAgent_1     139      Linda Juventude                  Zabelê, Zumbi, Besouro Vespa fabricando mel Guardo teu tesouro Jóia marrom Raça…
                              254      Camisa Amarela                   Encontrei o meu pedaço na avenida De camisa amarela Cantando a Florisbela, oi,… 
                              142      Coração Selvagem                 Meu bem, guarde uma frase pra mim dentro da sua canção Esconda um beijo pra mim…
                              170      Índios                           Quem me dera ao menos uma vez Ter de volta todo o ouro que entreguei a quem Con…
1   random     RandomAgent_2  85       Berimbau                         Quem é homem de bem não trai O amor que lhe quer seu bem Quem diz muito que vai…
                              134      Papel Machê                      Cores do mar, festa do Sol Vida é fazer Todo o sonho brilhar Ser feliz No teu c…
                              28       Apesar de Você                   Hoje você é quem manda Falou, tá falado Não tem discussão A minha gente hoje an…
                              12       Domingo no Parque                No birimbal O rei da brincadeira (ê, José) O rei da confusão (ê, João) Um traba…
2   random     RandomAgent_3  180      Rádio Pirata                     Abordar navios mercantes Invadir, pilhar, tomar o que é nosso Pirataria nas ond…
                              30       Carcará                          Carcará Pega, mata e come Carcará num vai morrer de fome Carcará Lá no sertão É…
                              199      Se Eu Não Te Amasse Tanto Assim  Meu coração Sem direção Voando só por voar Sem saber onde chegar Sonhando em te…
                              145      Sentado à Beira do Caminho       Eu não posso mais ficar aqui a esperar Que um dia, de repente, você volte para… 
3   random     RandomAgent_4  220      Magrelinha                       O pôr do sol vai renovar brilhar de novo o seu sorriso E libertar da areia pret…
                              13       Ovelha Negra                     Levava uma vida sossegada Gostava de sombra E água fresca Meu Deus! Quanto temp…
                              172      Sá Marina                        Descendo a rua da ladeira Só quem viu, que pode contar Cheirando a flor de lara…
                              243      Cigana                           Não deixe o tempo acabar com nosso amor Eu faço tudo e o impossível e você não… 
4   random     RandomAgent_5  62       Primeiros Erros                  Meu caminho é cada manhã Não procure saber onde vou Meu destino não é de ningué…
                              74       Rosa de Hiroshima                Pense nas crianças mudas telepáticas Pense nas meninas cegas inexatas Pense nas…
                              88       Meu Bem Querer                   Meu bem-querer É segredo, é sagrado Está sacramentado Em meu coração Meu bem-qu…
                              2        Detalhes                         Não adianta nem tentar me esquecer Durante muito tempo em sua vida eu vou viver…
5   random     RandomAgent_6  125      Além do Horizonte                Além do horizonte deve ter Algum lugar bonito pra viver em paz Onde eu possa en…
                              32       Pérola Negra                     Tente passar pelo que estou passando Tente apagar este teu novo engano Tente me…
                              67       O Canto da Cidade                A cor dessa cidade sou eu O canto dessa cidade é meu A cor dessa cidade sou eu… 
                              230      Festa                            Festa no gueto, Pode vir, pode chegar Misturando o mundo inteiro Vamos ver no q…

round 1
Clue (agent 0 - LLMAgent_1): "Juventude linda cais claro mel besouro"
id  card_id  title              0  1  2  3  4  5  Pts  Acm  New id  New lyrics            
--  -------  -----------------  -  -  -  -  -  -  ---  ---  ------  ----------------------
0   139      Linda Juventude       x  x     x     3    3    44      Todo Azul do Mar      
1   12       Domingo no Parque           x     x  5    5    107     Expresso 2222         
2   30       Carcará                        x     4    4    248     Fascinação            
3   243      Cigana                x              1    1    9       Eu Sei Que Vou Te Amar
4   74       Rosa de Hiroshima           x     x  5    5    218     Ai Se Eu Te Pego      
5   32       Pérola Negra             x           1    1    135     Já Sei Namorar        

round 2
Clue (agent 1 - RandomAgent_2): "não quem vai bem cai capoeira"
id  card_id  title            0  1  2  3  4  5  Pts  Acm  New id  New lyrics        
--  -------  ---------------  -  -  -  -  -  -  ---  ---  ------  ------------------
0   254      Camisa Amarela            x        4    7    182     Vou Deixar        
1   85       Berimbau         x        x  x  x  3    8    29      Malandragem       
2   248      Fascinação                      x  1    5    227     Vapor Barato      
3   172      Sá Marina                          3    4    194     Sentimental Demais
4   62       Primeiros Erros  x     x           5    10   238     Ferreirinha       
5   135      Já Sei Namorar         x     x     5    6    133     Sonífera Ilha     

round 3
Clue (agent 2 - RandomAgent_3): "não meu coração sem onde estrelas"
id  card_id  title                            0  1  2  3  4  5  Pts  Acm  New id  New lyrics     
--  -------  -------------------------------  -  -  -  -  -  -  ---  ---  ------  ---------------
0   182      Vou Deixar                                   x  x  5    12   152     Marina         
1   107      Expresso 2222                             x        1    9    207     Mulher de Fases
2   199      Se Eu Não Te Amasse Tanto Assim  x              x  3    8    157     Gita           
3   13       Ovelha Negra                        x              1    5    61      Exagerado      
4   88       Meu Bem Querer                   x  x              2    12   214     O Calhambeque  
5   133      Sonífera Ilha                             x  x     5    11   51      Como Eu Quero  

round 4
Clue (agent 3 - RandomAgent_4): "vou sei amar cada tua toda"
id  card_id  title                   0  1  2  3  4  5  Pts  Acm  New id  New lyrics   
--  -------  ----------------------  -  -  -  -  -  -  ---  ---  ------  -------------
0   170      Índios                     x        x  x  6    18   119     Sereia       
1   134      Papel Machê             x                 1    10   43      Dias de Luta 
2   157      Gita                                      3    11   8       Asa Branca   
3   9        Eu Sei Que Vou Te Amar  x     x     x     3    8    117     Vou Festejar 
4   218      Ai Se Eu Te Pego           x  x        x  6    18   55      Ideologia    
5   125      Além do Horizonte                         0    11   140     O Sol Nascerá

round 5
Clue (agent 4 - RandomAgent_5): "cadillac bip meu quero calhambeque mandei"
id  card_id  title             0  1  2  3  4  5  Pts  Acm  New id  New lyrics      
--  -------  ----------------  -  -  -  -  -  -  ---  ---  ------  ----------------
0   142      Coração Selvagem     x              4    22   155     Samba de Verão  
1   43       Dias de Luta            x  x     x  3    13   200     Ainda Bem       
2   227      Vapor Barato               x        1    12   89      Madalena        
3   117      Vou Festejar            x           1    9    47      Polícia         
4   214      O Calhambeque     x              x  3    21   131     Brincar de Viver
5   230      Festa             x  x              5    16   171     Triste Bahia    

round 6
Clue (agent 5 - RandomAgent_6): "sorrir pretendo levar fim vida pois"
id  card_id  title             0  1  2  3  4  5  Pts  Acm  New id  New lyrics    
--  -------  ----------------  -  -  -  -  -  -  ---  ---  ------  --------------
0   152      Marina               x              4    26   10      País Tropical 
1   28       Apesar de Você          x  x  x     6    19   31      Dona          
2   180      Rádio Pirata                  x     4    16   143     Minha Namorada
3   220      Magrelinha        x                 4    13   1       Construção    
4   131      Brincar de Viver                    0    21   190     Pintura Íntima
5   140      O Sol Nascerá     x  x  x  x        3    19   126     Catedral      

round 7
Clue (agent 0 - LLMAgent_1): "Luz do amor brilhante na cascata"
id  card_id  title       0  1  2  3  4  5  Pts  Acm  New id  New lyrics    
--  -------  ----------  -  -  -  -  -  -  ---  ---  ------  --------------
0   119      Sereia         x  x  x        3    29   100     João Valentão 
1   200      Ainda Bem               x  x  5    24   54      Luar do Sertão
2   8        Asa Branca           x  x     5    21   18      Tempo Perdido 
3   1        Construção        x           4    17   26      Por Você      
4   55       Ideologia                  x  1    22   219     Anjo          
5   126      Catedral       x              1    20   66      Maná          

round 8
Clue (agent 1 - RandomAgent_2): "dona não desses sempre onde nunca"
id  card_id  title                       0  1  2  3  4  5  Pts  Acm  New id  New lyrics     
--  -------  --------------------------  -  -  -  -  -  -  ---  ---  ------  ---------------
0   155      Samba de Verão                    x        x  5    34   80      Tente Outra Vez
1   31       Dona                        x           x     3    27   205     BR-3           
2   145      Sentado à Beira do Caminho  x              x  2    23   14      Baby           
3   26       Por Você                          x           1    18   242     Erva Venenosa  
4   2        Detalhes                             x        4    26   65      Cálice         
5   51       Como Eu Quero                        x  x     2    22   221     Chalana        

Final_scores: [0:34, 1:27, 2:23, 3:18, 4:26, 5:22]
Winner: 0 (LLMAgent_1)
Total_rounds: 8

```

---

## 5. Descrição dos prompts e das heurísticas implementadas no agente

Nossa arquitetura segue uma estratégia **LLM + múltiplos fallbacks**, procurando utilizar a capacidade semântica do modelo sempre que possível, mas garantindo que todas as ferramentas continuem funcionando mesmo quando a LLM produz respostas inválidas, incompletas ou sofre timeout.

### `receive_hand`

Recebe a mão distribuída pelo Game Master e apenas armazena as cartas localmente para utilização nas próximas etapas da rodada.

---

### `choose_card` (Narrador)

Nesta versão a escolha da carta continua sendo totalmente heurística.

**Heurística implementada**

- Calcula o tamanho da letra de cada música da mão.
- Calcula a mediana desses comprimentos.
- Escolhe a música cujo comprimento está mais próximo da mediana.

A ideia é evitar tanto letras extremamente curtas quanto extremamente longas, produzindo uma carta "mediana" que tende a oferecer uma quantidade razoável de conceitos para a geração da dica.

---

### `send_clue` (Narrador)

A geração da dica utiliza a LLM.

O agente envia aproximadamente as 60 primeiras palavras da letra juntamente com um prompt que instrui o modelo a:

- produzir apenas uma dica;
- utilizar no máximo o número especificado de palavras;
- não gerar explicações adicionais.

Após receber a resposta, ela passa pelo método `_sanitize_clue`, responsável por remover formatações indesejadas e adequar a saída ao formato esperado pelo jogo.

Caso a saída da LLM seja inutilizável após a sanitização, o agente utiliza a dica de segurança:

```
coisa estranha
```

garantindo que nunca deixe de responder ao Game Master.

---

### `select_card_by_clue` (Melômano)

Esta ferramenta passou a utilizar uma estratégia em múltiplas camadas.

#### Plano A — Escolha semântica via LLM

É enviada à LLM um prompt contendo:

- a dica recebida;
- todas as cartas da mão;
- um pequeno trecho da letra de cada música.

O prompt exige que o modelo responda exclusivamente com um JSON no formato:

```json
{"chosen_index": X}
```

Utilizamos **índices da mão (0 até n−1)** em vez dos IDs reais das músicas, reduzindo significativamente as alucinações.

Após a resposta, o agente tenta extrair o índice por três mecanismos sucessivos:

1. extração do JSON;
2. extração por regex;
3. procura pelo título da música caso a LLM ignore o formato solicitado e responda apenas com o nome da canção.

---

#### Plano B — Fallback heurístico

Caso nenhuma das estratégias anteriores produza um índice válido (erro, timeout ou resposta inválida), o agente utiliza uma heurística baseada em palavras-chave.

O procedimento consiste em:

- extrair palavras relevantes da dica;
- extrair palavras relevantes de cada música;
- calcular a interseção entre ambos os conjuntos;
- atribuir um bônus quando alguma palavra da dica aparece também no título da música.

A carta com maior pontuação é selecionada.

Caso nenhuma música apresente qualquer relação com a dica, uma carta da mão é escolhida aleatoriamente, garantindo que o agente sempre responda.

---

### `_find_own_option_index`

Antes da votação, o agente precisa descobrir qual das cartas sobre a mesa é a sua própria.

Para isso:

1. tenta localizar a carta utilizando seu `id`;
2. caso o protocolo utilize outro formato, realiza um fallback comparando `(título, artista)`.

Se ainda assim não conseguir identificar sua carta, registra um aviso em log e prossegue normalmente, evitando que uma incompatibilidade de formato interrompa a partida.

---

### `vote`

A votação utiliza quatro camadas sucessivas de decisão.

#### Plano A — JSON da LLM

O agente envia à LLM um prompt contendo:

- a dica do narrador;
- todas as cartas disponíveis para voto;
- pequenos trechos das respectivas letras.

O prompt exige exatamente o formato:

```json
{"votes":[A,B]}
```

Os votos válidos são imediatamente aceitos.

---

#### Plano B — Extração por regex

Caso o JSON não seja válido, nenhuma nova chamada à LLM é realizada.

O agente reutiliza exatamente a mesma resposta textual e procura números através de expressões regulares, aproveitando respostas parcialmente corretas.

---

#### Plano C — Heurística

Se ainda não houver dois votos válidos, cada carta recebe uma pontuação calculada pela função `_score_song_for_clue`, baseada na similaridade entre a dica e a música.

As cartas com maior pontuação são escolhidas.

---

#### Plano D — Rede de segurança

Antes de retornar ao Game Master, o agente:

- remove votos duplicados;
- remove votos inválidos;
- garante que nunca vote em sua própria carta;
- completa automaticamente a lista com índices válidos restantes caso ainda faltem votos.

Dessa forma, o contrato do protocolo é sempre respeitado, independentemente da resposta da LLM.

---

## 6. Dificuldades encontradas e soluções

### 1. Alucinação da LLM

Inicialmente a LLM frequentemente respondia utilizando IDs reais do catálogo de músicas, que não correspondiam às posições das cartas disponíveis durante a rodada.

**Solução**

Passamos a solicitar apenas os índices da mão (`0...n-1`), reduzindo drasticamente esse tipo de erro.

Além disso, implementamos três formas independentes de recuperar a escolha do modelo:

- leitura do JSON;
- regex;
- reconhecimento do título da música.

---

### 2. Respostas fora do formato esperado

Mesmo utilizando prompts rígidos, a LLM eventualmente respondia com textos livres em vez do JSON solicitado.

**Solução**

Em vez de desperdiçar uma nova chamada ao modelo, o agente reaproveita a própria resposta produzida pela LLM:

- primeiro tenta interpretar como JSON;
- depois procura números via regex;
- por fim utiliza heurísticas determinísticas.

Isso tornou o agente muito mais robusto e reduziu o tempo médio de resposta.

---

### 3. Garantia do protocolo de votação

Durante os testes verificou-se que respostas inválidas poderiam resultar em:

- votos duplicados;
- votos inexistentes;
- tentativa de votar na própria carta;
- quantidade incorreta de votos.

**Solução**

Foi implementada uma rede de segurança final que sempre:

- elimina votos inválidos;
- elimina duplicatas;
- impede auto-voto;
- completa automaticamente os votos restantes utilizando apenas índices válidos.

Assim, independentemente do comportamento da LLM, o agente sempre retorna exatamente dois votos válidos ao Game Master.

---

### 4. Identificação da própria carta

Dependíamos inicialmente apenas do identificador (`id`) enviado pelo protocolo.

**Solução**

Foi implementado o método `_find_own_option_index`, que também compara `(título, artista)` quando necessário, tornando o agente mais resistente a pequenas alterações no formato das mensagens trocadas com o Game Master.
