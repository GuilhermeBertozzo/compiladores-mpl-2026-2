# Registro de validação

Verificação realizada localmente com Python 3.12.14, usando a biblioteca padrão.
O corpus original e o verificador do professor foram preservados.

| Verificação | Resultado | Evidência |
|---|---|---|
| E1 | 20/20 | ../evidencias/verificacao-1.txt |
| E2, cumulativa | 36/36 | ../evidencias/verificacao-2.txt |
| E3, cumulativa | 70/70 | ../evidencias/verificacao-3.txt |
| E4, cumulativa | 93/93 | ../evidencias/verificacao-4.txt |
| Testes adicionais | 63 testes aprovados | make testes |
| Demonstração | Saída idêntica ao arquivo esperado | exemplos/torre_hanoi.saida |

Os testes adicionais verificam precedência, erros, sombreamento,
reinicialização de variáveis em laços, passagem por valor, ordem de avaliação,
conversões, recursão direta e mútua, limites de pilha, execução sem fonte,
posições de erros em comandos de várias linhas e preservação de Unicode.

O PDF tem oito páginas: seis da apresentação principal e duas de apoio.
Todas foram renderizadas e inspecionadas. O rastreamento de tokens, árvore,
tabela, IR e bytecode foi extraído da implementação, não transcrito por
suposição. A ferramenta geradora verifica a saída da demonstração e
reproduz em memória o defeito discutido no slide 6.

## Decisões explícitas

- A análise de retorno é estrutural e conservadora. Não avalia condições
  constantes. Um enquanto, mesmo com condição verdadeiro, exige retorno
  após o laço numa função que retorna valor. Um teste adicional inicialmente
  assumia outra regra e foi corrigido para a política descrita no README.
- O inicializador de uma variável é resolvido antes de inserir a nova
  declaração. Assim, num sombreamento, ele pode ler o valor externo.
- Inteiros usam o tipo int do Python e reais usam float. A conversão
  inteiro para real ocorre apenas nos pontos previstos pela linguagem.
- O IR imprime constantes reais em notação decimal para manter o formato
  legível sem confundir expoentes com operadores da linguagem.

## Alcance

As evidências comprovam o corpus público. O corpus privado do professor
não está disponível, e não se presume aprovação nele.
A versão principal de Python coincide com a exigida na correção, mas
isso não equivale a uma execução já feita no Google Cloud Shell.
make prova foi executado com Python 3.12.14 sobre um clone limpo do commit
49c97e7. As quatro entregas passaram (20/20, 36/36, 70/70 e 93/93),
e o comando terminou com código de saída 0. A atualização posterior deste
registro é apenas documental.
