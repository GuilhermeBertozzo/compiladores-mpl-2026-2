# Preparação e envio

## Identificação

Turma B, Grupo 7.

| Integrante | RA | E-mail |
|---|---|---|
| Henrique Motta Canho | Não informado | Não informado |
| Guilherme Bertozzo | Não informado | Não informado |
| Yago Leme | Não informado | Não informado |

Ainda é necessário informar RAs, e-mails e a URL do repositório do grupo.

## Arquivos

- Repositório inteiro, incluindo mplc/, compilar, executar, Makefile,
  testes/, tests/, exemplos/, documentação e evidencias/.
- E1: evidencias/verificacao-1.txt.
- E2: evidencias/verificacao-2.txt.
- E3: evidencias/verificacao-3.txt.
- E4: evidencias/verificacao-4.txt e o exemplo Torre de Hanoi com sua saída.
- Apresentação: apresentacao/apresentacao-grupo-07.pdf.

As quatro entregas são cumulativas. O mesmo compilador completo pode ser
inspecionado até cada fase pelos modos --tokens, --ast, --tabela e --ir.

## Conferência no ambiente de correção

No Google Cloud Shell, clone o repositório do grupo e entre em sua raiz.
Não é necessário instalar pacotes Python.

```sh
python3 --version
make verificar E=4
make testes
make demonstracao
make prova
```

make prova verifica apenas o último commit. Se alterar o código, execute
novamente os testes, gere as quatro evidências e crie um novo commit antes
de repetir make prova. Verifique o código de saída das verificações:
o alvo make evidencias salva inclusive resultados com falha.

## Publicação do repositório

O remote origin do clone inicial aponta para o laboratório do professor.
O envio deve usar o repositório do grupo, não esse endereço. Após criar
ou escolher esse repositório, adicione-o como um remote separado chamado
grupo e publique o branch atual. Não é necessário apagar o histórico do
laboratório. A URL de destino depende da escolha do grupo.

## Formulário

Abra a [página oficial do trabalho](https://profluiz.mantovanitec.com/disciplinas/aulas/compiladores/trabalho.html),
selecione a entrega, identifique os integrantes, cole a URL do repositório
publicado e anexe a evidência correspondente. Guarde o recibo por e-mail.
O envio do formulário e a publicação remota não são substituídos pela
presença dos arquivos no computador.

## Datas do enunciado no repositório

| Etapa | Turma A | Turma B |
|---|---|---|
| E1 | 02/09 | 31/08 |
| E2 | 30/09 | 28/09 |
| E3 | 28/10 | 26/10 |
| E4 | 18/11 | 16/11 |
| Apresentação | 25/11 | 23/11 |

Fonte: arquivos entregas/ da revisão original de 2026-2. A data da E1
já passou em ambas as turmas considerando 09/09/2026. Se ela estiver
pendente, confirme diretamente com o professor como regularizar.
Os slides devem ser enviados até 23h59 do dia anterior à apresentação.

## Antes da defesa

Leia docs/DEFESA.md, rode todos os modos de despejo e pratique a mudança
de um operador ou comando. Cada integrante precisa conseguir localizar
as fases relevantes. Use um defeito que realmente investigou e consiga
reproduzir ao relatar a experiência, sem inventar uma história de depuração.
