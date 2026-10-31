#!/usr/bin/env bash
# Gera samples CAD/BIM (se necessário) e executa a suíte de testes.
#
# Uso:
#   ./test.sh                 # gera samples se faltarem/desatualizados + roda toda a suíte
#   ./test.sh --samples       # só testes de samples (rápido)
#   ./test.sh --regen         # força regerar os samples (DXF/IFC mudam bytes: timestamps/GUIDs)
#   ./test.sh --gen-only      # só gera os samples
#   ./test.sh --check         # valida que o manifest versionado bate com o gerador (CI)
#   ./test.sh [args pytest]   # demais argumentos vão ao pytest (ex.: -k ifc -x)
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
GENERATOR="tests/samples/generate_samples.py"
MANIFEST="tests/samples/manifest.json"

REGEN=0; ONLY_GEN=0; CHECK=0; TARGET=("tests"); EXTRA=()
for arg in "$@"; do
  case "$arg" in
    --samples)  TARGET=("tests/test_samples_rigorous.py") ;;
    --regen)    REGEN=1 ;;
    --gen-only) ONLY_GEN=1; REGEN=1 ;;
    --check)    CHECK=1 ;;
    -h|--help)  sed -n '2,10p' "$0"; exit 0 ;;
    *)          EXTRA+=("$arg") ;;
  esac
done

if [ "$CHECK" = 1 ]; then
  # Bytes de DXF/IFC não são reprodutíveis, mas o manifest é: serve de contrato.
  cp "$MANIFEST" /tmp/manifest.expected.json
  "$PY" "$GENERATOR" >/dev/null
  if ! diff -q "$MANIFEST" /tmp/manifest.expected.json >/dev/null; then
    echo "❌ manifest.json divergente do gerador. Rode ./test.sh --gen-only e faça commit."
    cp /tmp/manifest.expected.json "$MANIFEST"; exit 1
  fi
  echo "✅ manifest em dia"
fi

# Gera se faltar manifest, se o gerador é mais novo, ou sob --regen
if [ "$REGEN" = 1 ] || [ ! -f "$MANIFEST" ] || [ "$GENERATOR" -nt "$MANIFEST" ]; then
  echo "▶ Gerando samples..."
  "$PY" "$GENERATOR"
fi
[ "$ONLY_GEN" = 1 ] && exit 0

echo "▶ Rodando pytest..."
exec "$PY" -m pytest "${TARGET[@]}" -q -rxX "${EXTRA[@]}"
