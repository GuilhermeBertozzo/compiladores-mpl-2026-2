#!/usr/bin/env bash
# Confere se o pull request mexe so na pasta de UM grupo e se ela segue as regras do README.
set -u
BASE="${1:?uso: conferir-pr.sh <commit-base>}"
falhas=0
falha() { echo "::error::$1"; falhas=$((falhas+1)); }

mapfile -t arquivos < <(git diff --name-only --diff-filter=ACMRD "$BASE"...HEAD)
if [ "${#arquivos[@]}" -eq 0 ]; then falha "O pull request nao altera nenhum arquivo."; exit 1; fi

declare -A pastas=()
for f in "${arquivos[@]}"; do
  case "$f" in
    grupos/*/*) pastas["$(echo "$f" | cut -d/ -f2)"]=1 ;;
    *) falha "Arquivo fora da pasta do grupo: $f" ;;
  esac
done

if [ "${#pastas[@]}" -gt 1 ]; then
  falha "O pull request mexe em mais de um grupo: ${!pastas[*]}. Um pull request por grupo."
fi

for p in "${!pastas[@]}"; do
  [[ "$p" =~ ^turma[AB]-[a-z0-9]+(-[a-z0-9]+)*$ ]] || falha "Nome de pasta invalido: grupos/$p (use turmaA-... ou turmaB-..., minusculas, numeros e hifen)."
  [ -f "grupos/$p/GRUPO.md" ] || falha "Falta grupos/$p/GRUPO.md (copie o GRUPO-modelo.md e preencha)."
  if [ -f "grupos/$p/GRUPO.md" ] && grep -Eqi '[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}' "grupos/$p/GRUPO.md"; then
    falha "grupos/$p/GRUPO.md tem um endereco de e-mail. Repositorio publico: tire dados pessoais."
  fi
  while IFS= read -r -d '' g; do falha "Arquivo gerado nao deve ir: $g"; done < <(find "grupos/$p" \( -name '__pycache__' -o -name '*.pyc' -o -name '*.class' -o -name '.git' -o -name 'evidencias' \) -print0 2>/dev/null)
  while IFS= read -r -d '' g; do falha "Arquivo acima de 10 MB: $g"; done < <(find "grupos/$p" -type f -size +10M -print0 2>/dev/null)
done

if [ "$falhas" -gt 0 ]; then echo "$falhas problema(s). Corrija e faca push de novo no mesmo branch."; exit 1; fi
echo "Tudo certo: o pull request mexe so em grupos/${!pastas[*]}/."
