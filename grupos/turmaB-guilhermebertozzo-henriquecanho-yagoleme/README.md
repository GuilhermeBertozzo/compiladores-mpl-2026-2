# Compilador MPL

Trabalho semestral de Compiladores, Prof. Luiz Ricardo Mantovani da Silva.
Implementação em Python, usando exclusivamente a biblioteca padrão.
O laboratório original está documentado em [README_LABORATORIO.md](README_LABORATORIO.md).

**Turma B, Grupo 7**

- Henrique Motta Canho
- Guilherme Bertozzo
- Yago Leme

RAs e e-mails serão informados no formulário de envio.

## Execução

Na raiz deste repositório, com Python 3 e make disponíveis:

```sh
./compilar exemplos/torre_hanoi.mpl
./executar exemplos/torre_hanoi.mplb
make verificar E=4
python3 -m unittest discover -s tests -v
```

O ambiente oficial é Python 3.12 no Google Cloud Shell. O compilador não
requer pip, ambientes virtuais, bibliotecas externas, internet ou instalação.
Os materiais da apresentação já incluem o PDF pronto. A ferramenta opcional
para regenerá-lo tem dependências separadas e não participa da compilação.

### Inspeção das fases

```sh
./compilar --tokens exemplos/torre_hanoi.mpl
./compilar --ast exemplos/torre_hanoi.mpl
./compilar --tabela exemplos/torre_hanoi.mpl
./compilar --ir exemplos/torre_hanoi.mpl
```

Cada opção interrompe o processo na fase indicada, não gera arquivo e imprime
apenas seu artefato. A compilação normal gera um arquivo textual .mplb ao lado
do fonte e fica silenciosa. Erros têm fase, linha e coluna em stderr.
Os códigos de saída são 0 (sucesso), 1 (compilação) e 2 (execução).

## Organização

| Arquivo | Responsabilidade |
|---|---|
| mplc/lexico.py | Scanner manual, tokens e posições |
| mplc/sintatico.py | Parser por descida recursiva e AST |
| mplc/semantica.py | Resolução de nomes, tipos e análise de retorno |
| mplc/intermediario.py | AST anotada para código de três endereços |
| mplc/gerador.py | Código intermediário para instruções da VM |
| mplc/vm.py | Execução com pilha e registros de ativação |
| mplc/principal.py | Integração das fases e linha de comando |
| tests/ | Testes adicionais da implementação |
| testes/ | Corpus e gabaritos originais do professor |
| exemplos/torre_hanoi.mpl | Programa de demonstração |
| exemplos/torre_hanoi.saida | Saída esperada da demonstração |

## E1: tabela de tokens

O scanner percorre caracteres, reconhece comentários antes do operador de
divisão e operadores de dois caracteres antes dos de um caractere. Após
reconhecer um identificador completo, consulta a tabela de palavras reservadas.
As expressões abaixo descrevem o reconhecimento, sem usar gerador de lexer.

| Reconhecimento | Tipo do token |
|---|---|
| [0-9]+ | INTEIRO |
| [0-9]+\.[0-9]+ | REAL |
| verdadeiro, falso | LOGICO |
| Aspas duplas, conteúdo e escapes válidos, aspas duplas | TEXTO |
| [A-Za-z_][A-Za-z_0-9]*, exceto palavras reservadas | ID |
| funcao | FUNCAO |
| retorne | RETORNE |
| se / senao | SE / SENAO |
| enquanto | ENQUANTO |
| escreva | ESCREVA |
| inteiro / real / logico / texto / vazio | TIPO_INTEIRO / TIPO_REAL / TIPO_LOGICO / TIPO_TEXTO / TIPO_VAZIO |
| e / ou / nao | E / OU / NAO |
| + / - / * / / / % | MAIS / MENOS / VEZES / DIVIDE / RESTO |
| == / != | IGUAL / DIFERENTE |
| < / <= / > / >= | MENOR / MENOR_IGUAL / MAIOR / MAIOR_IGUAL |
| = | ATRIBUI |
| ( / ) | ABRE_PAR / FECHA_PAR |
| { / } | ABRE_CHAVE / FECHA_CHAVE |
| , / ; | VIRGULA / PONTO_VIRGULA |
| Fim da entrada | FIM_ARQUIVO, lexema vazio |

TEXTO admite apenas os escapes de nova linha, tabulação, aspas e barra
invertida listados em [LINGUAGEM.md](LINGUAGEM.md). O lexema conserva aspas e
escapes originais. Textos não atravessam linhas. Comentários // terminam
na quebra de linha e /* ... */ terminam no primeiro fechamento, sem aninhar.
Espaço, tabulação, CR e LF não geram tokens. Linha e coluna começam em 1
e a posição gravada é sempre a do início do token.

## E2: gramática implementada

EBNF: { X } significa repetição, [ X ] significa opcional, | separa alternativas.
ID e literais são tokens do scanner.

```ebnf
programa     = { funcao } ;
funcao       = "funcao" retorno ID "(" [ parametros ] ")" bloco ;
retorno      = tipo | "vazio" ;
tipo         = "inteiro" | "real" | "logico" | "texto" ;
parametros   = tipo ID { "," tipo ID } ;
bloco        = "{" { comando } "}" ;
comando      = declaracao | atribuicao | condicional | repeticao
             | escrita | retorno_cmd | chamada ";" | bloco ;
declaracao   = tipo ID [ "=" expressao ] ";" ;
atribuicao   = ID "=" expressao ";" ;
condicional  = "se" "(" expressao ")" bloco [ "senao" bloco ] ;
repeticao    = "enquanto" "(" expressao ")" bloco ;
escrita      = "escreva" "(" expressao ")" ";" ;
retorno_cmd  = "retorne" [ expressao ] ";" ;
expressao    = disjuncao ;
disjuncao    = conjuncao { "ou" conjuncao } ;
conjuncao    = igualdade { "e" igualdade } ;
igualdade    = relacao { ("==" | "!=") relacao } ;
relacao      = soma { ("<" | "<=" | ">" | ">=") soma } ;
soma         = produto { ("+" | "-") produto } ;
produto      = unario { ("*" | "/" | "%") unario } ;
unario       = ("nao" | "-") unario | primario ;
primario     = literal | ID | chamada | "(" expressao ")" ;
chamada      = ID "(" [ expressao { "," expressao } ] ")" ;
literal      = INTEIRO | REAL | LOGICO | TEXTO ;
```

Cada nível de precedência chama o seguinte, mais forte. Laços montam os
binários à esquerda, portanto 10 - 4 - 3 equivale a (10 - 4) - 3.
Unários são empilhados e montados de trás para frente, agrupando à direita. Uma chamada
como comando pode descartar um valor retornado. Não há comandos de
expressão arbitrários, como 1 + 2;.

A AST usa nós com rótulo, filhos ordenados, linha, coluna e anotações.
O despejo oficial usa dois espaços por nível. A fase semântica acrescenta
tipos e vínculos sem alterar os rótulos exibidos.

## E3: escopos e tipos

Cada escopo é um objeto com um dicionário ordenado de símbolos e um ponteiro
para o pai. A busca começa no escopo atual e sobe até encontrar o nome, o
que implementa sombreamento. Os escopos também ficam numa lista pela ordem
de abertura, permitindo o despejo determinístico exigido pelo contrato.
Cada variável recebe um slot exclusivo, como v2_x, que o IR mapeia para um
nome compacto como v0. Assim duas variáveis com o mesmo nome não compartilham
armazenamento na VM.

O escopo global guarda funções. Cada função abre um escopo para parâmetros
e outro para seu bloco. Cada bloco adicional abre seu próprio escopo,
inclusive quando vazio. O inicializador é analisado antes de inserir a nova
variável, podendo acessar um nome externo que será sombreado após a declaração.
Um nome local também esconde uma função global de mesmo nome.

A primeira passada coleta todas as assinaturas. A segunda verifica corpos,
argumentos, atribuições, condições e retornos, permitindo chamadas adiantadas
e recursão mútua. A única conversão implícita é inteiro para real.
Condições exigem logico e chamadas vazio só são aceitas como comando.

Retorne garante retorno. Um bloco garante retorno se algum comando da
sequência garante. Um se só garante retorno quando possui senao e ambos os
ramos garantem. Enquanto não garante retorno, mesmo com condição literal
verdadeira. Código após retorne ainda é verificado, embora não seja executado.

## E4: código intermediário e execução

O gerador de IR decompõe expressões em operações com temporários, emitindo
rótulos e desvios para condicionais e repetições. As instruções conservam a
posição do comando para atribuir erros de execução à linha correta.
O gerador de bytecode traduz o IR para uma máquina de pilha, e a VM executa
essas instruções, sem interpretar o fonte nem recorrer a eval ou exec.

Os detalhes do arquivo e o conjunto de instruções estão na seção
[Instruções da VM](#instruções-da-vm) abaixo.

A conversão ocorre no ponto de consumo: em real x = 7 / 2;, a divisão
inteira produz 3 e só depois o valor vira real, imprimindo 3.000000.
A divisão inteira trunca em direção a zero e o resto satisfaz
a = (a / b) * b + (a % b). Os dois operandos de e/ou são avaliados.

Cada chamada tem seus próprios locais, temporários, base na pilha de operandos
e ponto de continuação. Isso preserva as variáveis de chamadas recursivas.
Parâmetros são passados por valor. A execução verifica divisão/resto por
zero e estouro de pilha e usa o código de saída 2.

### Instruções da VM

O arquivo começa com MPLB 1. FUNC ["nome", "retorno", ["slot", ...]]
inicia uma função e END encerra sua definição. Cada instrução tem a forma
linha:coluna OPCODE [argumentos em JSON]. Os números de linha e coluna
identificam o comando original em MPL. JSON serve apenas para representar
os argumentos e escapar textos, não para guardar a AST.

Na tabela, S é o restante da pilha e o topo está à direita.

| Instrução | Efeito na pilha e execução |
|---|---|
| PUSH [valor] | S passa a S, valor |
| LOAD [slot] | S passa a S, locais[slot] |
| STORE [slot] | S, valor passa a S e grava valor no slot local |
| I2R [] | S, inteiro passa a S, real |
| BINARY [op, tipo] | S, esquerda, direita passa a S, resultado |
| UNARY [op, tipo] | S, operando passa a S, resultado |
| LABEL [rotulo] | Não altera a pilha, marca um destino |
| JUMP [rotulo] | Não altera a pilha, transfere controle para o rótulo |
| JUMP_FALSE [rotulo] | Remove a condição do topo e salta se falsa |
| CALL [nome, n] | Retira n argumentos e cria um registro de ativação |
| RETURN [tem_valor] | Encerra o registro, restaura a base e devolve zero ou um valor |
| WRITE [tipo] | Remove um valor e imprime sua representação MPL mais uma quebra de linha |
| TRAP [mensagem] | Interrompe com erro de execução na posição da instrução |

BINARY recebe os operadores aritméticos, relacionais ou lógicos da MPL.
UNARY recebe - ou nao. O tipo no opcode é o dos operandos após conversão.
LABEL é resolvido no carregamento. A VM valida destinos de salto e chamadas
antes de iniciar principal. Seus limites são 4096 registros de ativação
e 65536 valores na pilha de operandos, independentes da recursão do Python.

## Demonstração e apresentação

[Torre de Hanoi](exemplos/torre_hanoi.mpl) imprime os sete movimentos de três
discos, calcula recursivamente a quantidade de movimentos e confere o total.
Demonstra recursão, funções vazio e inteiro, parâmetros texto, concatenação,
condições, atribuições e precedência.

O [roteiro de defesa](docs/DEFESA.md) orienta a apresentação e o estudo das
alterações ao vivo. Os materiais em apresentacao/ são editáveis e devem
ser revisados e identificados pelo grupo antes do envio.

## Verificação e entrega

```sh
make verificar E=1
make verificar E=2
make verificar E=3
make verificar E=4
python3 -m unittest discover -s tests -v
make evidencias E=1
make evidencias E=2
make evidencias E=3
make evidencias E=4
make prova
```

As entregas são cumulativas. make prova testa um clone do último commit,
por isso é necessário commitar código, testes, documentação e evidências.
Os arquivos e gabaritos originais de testes/ e verificar.py são preservados.
Os testes adicionais exercitam casos além do corpus público, mas não dão
acesso ao corpus privado do professor.

Para enviar, identifique o grupo no formulário oficial, informe a URL do
repositório do grupo e anexe evidencias/verificacao-N.txt. Faça o push antes.
Os slides devem ser renomeados para apresentacao-grupo-NN.pdf e enviados
até 23h59 do dia anterior à apresentação. As datas por turma constam nos
arquivos originais de entregas/.