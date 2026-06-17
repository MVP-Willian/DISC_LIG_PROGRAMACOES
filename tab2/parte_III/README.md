# Nota Secreta — Agente Estratégico LLM

Este projeto contém a implementação de um agente estratégico autônomo para o jogo **Nota Secreta** (uma variação de Dixit com músicas brasileiras). O sistema é baseado na integração de um modelo de linguagem local (Phi-3.5-mini-instruct) com rotinas de fallback heurístico para garantir estabilidade e resiliência em um ambiente distribuído.

## 1. Integrantes do Grupo
* Lucas de Souza Cerveira Pereira
* Mikaelle Costa de Sanatana
* Michael Willian Pereira Vieira

---

## 2. Instruções de instalação
*As instruções de instalação são as mesmas fornecidas na arquitetura base do professor.*

1. Acesse a pasta do projeto contendo o llm_agent.
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

O projeto pode ser executado facilmente através do orquestrador `run_game.py`:

**Para rodar em modo Mock (teste rápido sem carregar o modelo LLM pesado):**
```bash
python3 run_game.py --force-mock
```

**Para rodar a partida oficial (com o modelo real integrado):**
```bash
python run_game.py --model /caminho/absoluto/para/o/Phi-3.5-mini-instruct-Q4_K_M.gguf
```

*(O script orquestrará o Game Master, o Serviço LLM, o nosso agente estratégico e 5 agentes aleatórios automaticamente).*

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

Nossa arquitetura é **Híbrida Defensiva**. Para as ferramentas (tools) do agente, combinamos chamadas à LLM com *fallbacks* (planos de contingência) puramente algorítmicos.

* **`choose_card` (Narrador):**
  * *Heurística:* Usa um cálculo simples baseado no comprimento da letra[cite: 4]. Avalia o tamanho de todas as letras da mão, calcula a mediana e seleciona a música cujo tamanho mais se aproxima desse valor[cite: 4].
* **`send_clue` (Narrador):**
  * *Prompt:* Envia as 60 primeiras palavras da letra e instrui a LLM a retornar uma dica de no máximo 6 palavras[cite: 4]. 
  * *Heurística:* A saída passa pelo método `_sanitize_clue`[cite: 4]. Se a LLM falhar completamente, o agente adota uma dica *fallback* de segurança ("coisa estranha")[cite: 4].
* **`select_card_by_clue` (Melômano):**
  * *Prompt:* Pede restritamente que a LLM retorne o **Índice (0 a n-1)** da música na mão (em vez do ID do catálogo) para reduzir alucinações[cite: 4]. Usamos Regex (`_parse_song_choice`) para extrair esse dígito[cite: 4].
  * *Heurística (Fallback):* Em caso de timeout (limite de 60s), fazemos a interseção de palavras-chave da dica com as palavras de cada música (`_song_keywords`)[cite: 4].
* **`vote` (Melômano):**
  * *Heurística Inicial:* Usamos `_find_own_option_index` para localizar nossa própria carta na mesa (por ID ou Título+Artista) e proibi-la de receber votos[cite: 4].
  * *Prompt:* Requisita um JSON rigoroso: `{"votes": [opcaoA, opcaoB]}`[cite: 4].
  * *Heurísticas de Fallback:* Se o `json.loads` falhar, aplicamos Regex (`re.findall`) na mesma resposta crua para resgatar os números[cite: 4]. Se ainda faltarem votos, usamos a função `_score_song_for_clue` para classificar e votar nas cartas restantes mais semelhantes à dica[cite: 4].

---

## 6. Dificuldades encontradas e soluções

1. **Alucinação de IDs Inexistentes:** A LLM frequentemente respondia com IDs do catálogo de músicas que nem sequer estavam na mão do jogador ou na mesa.
   * *Solução:* Alteramos o prompt na função `select_card_by_clue` para solicitar o **Índice posicional na mão (0 a 3)**, em vez do ID[cite: 4]. Limitar o escopo de opções da LLM praticamente zerou as alucinações.
2. **Quebra de Protocolo e Timeouts na Votação:** O processo de extrair exatamente dois votos distintos, sem incluir a própria carta, gerava strings sujas da LLM ou causava timeouts (acima de 60s) se tentássemos pedir a resposta múltiplas vezes.
   * *Solução:* Otimizamos o `vote` para fazer **apenas uma chamada** ao modelo. Extraímos o JSON e, se falhar, reciclamos a string original passando uma Regex por cima[cite: 4]. Se tudo der errado, uma rotina de repescagem algorítmica escolhe as cartas finais, garantindo o envio rápido ao *Game Master*[cite: 4].
3. **Identificação da Própria Carta na Votação:** Depender exclusivamente da chave `id` enviada pelo *Game Master* era frágil e poderia quebrar nosso filtro de não votar na própria carta.
   * *Solução:* Implementamos o método `_find_own_option_index`, que possui um fallback próprio para comparar `title` + `artist` se o ID falhar[cite: 4].