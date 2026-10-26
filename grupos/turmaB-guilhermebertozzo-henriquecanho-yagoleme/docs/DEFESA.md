# Roteiro de apresentação e estudo

Turma B, Grupo 7: Henrique Motta Canho, Guilherme Bertozzo e Yago Leme.

Este roteiro explica a implementação preparada com assistência de IA.
Pratique com o código aberto. A apresentação exige compreender as fases
e saber fazer uma alteração, não apenas ler os slides.

## Antes da aula

1. Rode make verificar E=4, make testes e make demonstracao.
2. Abra apresentacao/apresentacao-grupo-07.pdf e o terminal na raiz do projeto.
3. Deixe abertos exemplos/torre_hanoi.mpl e apresentacao/rastreamento.txt.
4. Gere o executável com ./compilar exemplos/torre_hanoi.mpl e abra
   exemplos/torre_hanoi.mplb no editor.
5. Envie o PDF até 23h59 do dia anterior. Para a Turma B, o enunciado
   informa apresentação em 23/11 e envio dos slides até 22/11 às 23h59.
6. Cronometre uma apresentação inteira e pratique pelo menos uma alteração
   numa cópia de estudo. As extensões não fazem parte da linguagem obrigatória.

## Cinco minutos de apresentação

Os slides 1 a 6 formam a apresentação principal. Os slides 7 e 8 são apoio
para perguntas e para o exercício ao vivo.

| Tempo | Slide | Conteúdo | Divisão sugerida |
|---|---|---|---|
| 0:00 a 0:30 | 1 | Compilar e executar Torre de Hanoi | Henrique |
| 0:30 a 1:30 | 2 | Tokens e árvore de passos = 2 * 3 + 1; | Guilherme |
| 1:30 a 2:30 | 3 | Tipo, escopo e código intermediário | Yago |
| 2:30 a 3:10 | 4 | Instruções no arquivo .mplb | Yago |
| 3:10 a 3:30 | 5 | Registro de ativação e recursão | Guilherme |
| 3:30 a 5:00 | 6 | Sintoma, diagnóstico, correção e teste do defeito | Henrique, com participação dos demais |

### 1. Programa funcionando

```sh
make demonstracao
```

Explique: hanoi transfere três discos entre os pinos A, B e C. Cada chamada
resolve dois problemas menores. quantidade calcula recursivamente o número
de movimentos. A execução imprime sete movimentos e uma conferência verdadeira.
O PDF resume a saída; a saída completa esperada está em exemplos/torre_hanoi.saida.

### 2. Tokens e AST

```sh
./compilar --tokens exemplos/torre_hanoi.mpl
./compilar --ast exemplos/torre_hanoi.mpl
```

Na expressão passos = 2 * 3 + 1;, o lexer reconhece o nome, o sinal de
atribuição, os literais, os operadores e o ponto e vírgula. Ele conserva
linha e coluna. O parser monta + acima de *, provando que a multiplicação
vem primeiro. Os laços de cada nível montam os binários à esquerda:
10 - 4 - 3 significa (10 - 4) - 3.

Mostre _Parser.adicao, _Parser.multiplicacao e _Parser.binarios em
mplc/sintatico.py. A gramática completa está no README.

### 3. Escopo, tipo e IR

```sh
./compilar --tabela exemplos/torre_hanoi.mpl
./compilar --ir exemplos/torre_hanoi.mpl
```

A tabela vincula passos a uma variável inteiro no bloco de principal.
A semântica faz duas passadas: assinaturas primeiro e corpos depois.
Isso permite chamar uma função que aparece mais adiante no arquivo.

Cada escopo tem dicionário próprio e ponteiro para o pai. O corpo de uma
função abre dois escopos: parâmetros e bloco. A busca local antes da busca
no pai implementa o sombreamento. Cada vínculo recebe um slot distinto.

O IR guarda cada resultado parcial num temporário. No exemplo atual,
t40 recebe 2 * 3, t42 recebe t40 + 1 e o slot v5 recebe t42.
Não se deve decorar os números: se o exemplo mudar, eles podem mudar.
apresentacao/rastreamento.txt registra os artefatos exatos do exemplo entregue.

### 4. Bytecode e VM

Abra exemplos/torre_hanoi.mplb. Mostre o cabeçalho MPLB 1, as definições
FUNC/END e as instruções da linha da atribuição.

PUSH empilha uma constante. LOAD lê um slot. BINARY consome primeiro o
operando direito e depois o esquerdo, calcula esquerda operador direita
e empilha o resultado. STORE grava o topo num slot.

CALL retira os argumentos e cria um registro com locais, parâmetros,
base da pilha e endereço de retorno. RETURN remove esse registro e
restaura o chamador. A VM executa um laço Python, não recursão Python.
As chamadas MPL usam uma pilha explícita com limite de 4096 registros.

O JSON no .mplb representa argumentos de instruções. Não contém o
programa-fonte nem a árvore. A VM pode executar o arquivo sem o .mpl.

### 5. Defeito reproduzível: separador Unicode

O caso do slide 6 foi identificado na implementação assistida. Não o
descreva como uma experiência pessoal anterior que não aconteceu. Reproduza,
entenda e explique o defeito tecnicamente, ou substitua por um problema
que vocês realmente tenham investigado durante o estudo.

- Sintoma: um texto contendo U+2028 era serializado com o caractere literal.
  A VM rejeitava o bytecode.
- Diagnóstico: str.splitlines() separa mais caracteres que apenas a quebra
  de linha comum. U+2028 dentro da constante dividia uma instrução em duas.
- Correção: json.dumps com ensure_ascii=True grava esse caractere como
  escape JSON na mesma linha física. json.loads restaura o texto original.
- Regressão: tests/test_backend.py, caso
  test_strings_preservam_escapes_unicode_e_separadores.

O gerador opcional de PDF também reproduz o formato defeituoso em memória,
sem modificar o compilador entregue, e confirma a saída correta da versão
atual. O sintoma reproduzido está em apresentacao/rastreamento.txt.

Outro caso para estudar é a divisão inteira: real x = 7 / 2; produz
3.000000. Converter os operandos antes de dividir produziria 3.500000.
O teste test_conversoes_no_consumo protege essa regra.

## Alteração ao vivo

O enunciado detalhado dá dez minutos para implementar a mudança e três
minutos para mostrar o resultado. Todas as mudanças abaixo são exercícios
para depois da versão obrigatória. Não altere a linguagem base sem o sorteio.

### Operador de potência **

1. Adicione o token de dois caracteres no lexer, antes de *.
2. Defina a precedência e a associatividade conforme a solicitação.
   Por exemplo, potência normalmente agrupa à direita. Confirme também
   como -2 ** 2 deve agrupar, pois isso determina sua relação com unários.
3. Adicione o nível no parser e produza binario **.
4. Valide tipos na semântica. Defina restrições de expoente e resultado.
5. O IR e gerador já transportam o símbolo de binários. Adicione a operação
   na VM, respeitando o tipo que a semântica aprovou.
6. Teste 2 ** 3, 2 + 3 ** 2, 2 ** 3 ** 2, -2 ** 2 e tipos inválidos.

### senaose

1. Adicione a palavra reservada e seu token.
2. No parser, traduza o encadeamento para um se dentro do bloco senao.
3. Preserve a posição do novo comando.
4. Os nós existentes permitem reutilizar análise semântica, IR e VM.
5. Teste o primeiro ramo verdadeiro, um ramo intermediário, senao final
   e o caso sem senao.

### escreva com dois argumentos

1. Aceite uma lista separada por vírgulas no parser.
2. Verifique todos os argumentos na semântica e recuse vazio.
3. Defina com o professor a separação e a quebra de linha desejadas.
4. Se cada argumento imprimir em sua própria linha, basta gerar WRITE
   para cada um. Para uma única linha com separador, ajuste a instrução
   ou crie uma operação de escrita sem quebra e finalize a linha.
5. Teste dois tipos diferentes e argumentos que chamem funções, preservando
   a ordem de avaliação.

### pare dentro de enquanto

1. Adicione a palavra reservada, o token e o comando pare; no parser.
2. Na semântica, acompanhe a profundidade dos laços e rejeite pare fora deles.
3. No gerador de IR, mantenha uma pilha de rótulos de fim de laço.
4. Traduza pare para jump ao rótulo do laço mais interno.
5. A VM já sabe executar JUMP. Teste laços aninhados e pare fora de laço.

### Curto-circuito para e e ou

1. O lexer e o parser já reconhecem os operadores.
2. A semântica deve continuar verificando os dois lados, mesmo quando
   um deles poderá não executar.
3. Na geração de IR, substitua a avaliação imediata dos dois filhos por
   desvios condicionais. Em e, o lado direito só executa se o esquerdo
   for verdadeiro. Em ou, só executa se o esquerdo for falso.
4. Garanta que ambos os caminhos definam o mesmo temporário de resultado.
5. Use uma função que imprime uma marca para provar quais lados executaram.
   Os testes atuais de avaliação obrigatória devem ser adaptados apenas
   na cópia em que a nova regra está sendo implementada.

## Parser manual e ferramentas geradoras

A versão entregue usa funções e laços escritos em Python. Em um gerador,
a gramática seria fornecida declarativamente para produzir o reconhecedor.
Ainda seria necessário construir a AST, verificar símbolos e tipos e
gerar código. O gerador reduz parte do trabalho de reconhecimento, mas
não substitui o projeto das demais fases. O enunciado proíbe esses
geradores nas entregas 1 e 2.

## Perguntas para ensaiar

- Por que <= precisa ser reconhecido antes de <?
- Por que a coluna começa em 1 e o erro de sintaxe aponta o token encontrado?
- Como a AST prova que a multiplicação tem maior precedência que a soma?
- Como o código distingue duas variáveis x em escopos diferentes?
- Por que coletar assinaturas antes de analisar os corpos?
- Onde a conversão inteiro para real acontece?
- Por que -7 % 3 dá -1 na MPL, apesar de o Python devolver 2?
- Como duas chamadas recursivas mantêm variáveis independentes?
- Por que um laço não basta, nesta análise estrutural conservadora,
  para garantir o retorno de uma função?
- Como demonstrar que executar usa o bytecode e não o fonte?
- Qual teste escreveria antes de alterar a linguagem?

## Recriar os slides

O PDF pronto não precisa de dependências para ser apresentado. Para editar
o conteúdo e regenerar, use apresentacao/gerar_pdf.py com ReportLab instalado
em um ambiente separado. Essa ferramenta não participa de compilar/executar,
make verificar, make prova ou make testes.
