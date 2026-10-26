# Compiladores MPL — 2026-2

Vitrine dos compiladores da **Minha pequena linguagem (MPL)** escritos pelos grupos de
**Compiladores** — Ciência da Computação, UNISAGRADO, 2026-2.
Prof. Luiz Ricardo Mantovani da Silva.

O enunciado, a linguagem e o verificador estão em
[compiladores-lab](https://github.com/LuizRMSilva1973/compiladores-lab). Este repositório
guarda a **versão final** de cada grupo, para ficar como portfólio de vocês.

---

## Quando postar

**Só depois da apresentação da sua turma:**

| Turma | Apresentação | Pode abrir o pull request a partir de |
|---|---|---|
| Turma B (segunda) | 23/11 | 23/11, depois da aula |
| Turma A (quarta) | 25/11 | 25/11, depois da aula |

O repositório é público e todos os grupos fazem o mesmo compilador. Pull request aberto
antes da apresentação da sua turma fica visível para todo mundo, por isso **será fechado
sem ser aceito**. Isso protege o trabalho de vocês.

---

## Como postar

1. Faça um **fork** deste repositório (botão *Fork*, no alto da página).
2. No seu fork, crie a pasta do grupo:

   ```
   grupos/turmaB-nome-do-grupo/
   ```

   Comece com `turmaA-` ou `turmaB-`; no resto, só letras minúsculas, números e hífen. Nada de espaço ou acento.
3. Copie para essa pasta o compilador do grupo, **a mesma versão apresentada**
   (o conteúdo do repositório de vocês, sem a pasta `.git`).
4. Copie o modelo [`GRUPO.md`](GRUPO-modelo.md) para dentro da pasta e preencha, inclusive o link do
   repositório do grupo, **com o histórico de commits do semestre**. Se ele for privado, deem acesso de
   leitura ao usuário `LuizRMSilva1973`.
5. Faça commit, `git push` para o seu fork e abra um **pull request** para este repositório.

Um pull request por grupo. Quem abre é um integrante; os outros aparecem no `GRUPO.md`.

---

## Regras

- **Só a pasta do seu grupo.** O pull request não pode alterar nada fora de
  `grupos/turmaX-nome-do-grupo/`. Uma verificação automática confere isso e fica vermelha
  se algo estiver fora do lugar.
- **Sem dados pessoais.** Repositório público: nada de RA, e-mail, telefone ou endereço.
  No `GRUPO.md`, cada integrante coloca o nome como quiser que apareça.
- **Sem arquivos gerados.** Não incluam `__pycache__/`, `.class`, executáveis, `evidencias/`
  nem arquivos acima de 10 MB.
- O código continua sendo de vocês. Se quiserem uma licença, coloquem um arquivo `LICENSE`
  dentro da pasta do grupo.

---

## Pré-aceitação: o que é conferido

Todo pull request passa por uma pré-aceitação automática **antes** de o professor olhar.
O resultado aparece na aba *Checks* do pull request.

**Recusam o pull request sozinhos:**
- pasta fora do padrão, arquivo fora da pasta do grupo ou `GRUPO.md` faltando;
- pull request aberto antes da apresentação da turma;
- falta de `compilar` ou `executar` na raiz da pasta;
- biblioteca que não seja da biblioteca padrão, ou gerador de parser (ANTLR, PLY, lark, yacc e parentes).

**Vão para o laudo:**
- o resultado do **verificador oficial** do `compiladores-lab`, baixado na hora (não o que está na pasta de vocês);
- números de qualidade do código (tamanho de cada fase e das funções).

Depois disso, o professor faz uma **revisão própria**, que inclui um corpus de testes que não é público,
comparação entre os trabalhos, o histórico de commits do repositório do grupo e análise de autoria,
com apoio de ferramentas, inclusive de IA. Nada disso é publicado. Indício nunca vale como prova:
a apresentação, com a alteração ao vivo, continua sendo o que mostra quem escreveu o compilador.

---

## Rodar o compilador de um grupo

Cada pasta segue o contrato do `compiladores-lab`, então funciona igual:

```bash
cd grupos/turmaB-nome-do-grupo
./compilar programa.mpl
./executar programa.mplb
```
