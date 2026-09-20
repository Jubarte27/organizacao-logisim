#!/bin/bash
# testar.sh [arquivo.circ]  -- roda todos os testes e compara com o modelo de referencia.
cd "$(dirname "$0")"
CIRC="${1:-../RISCV_Monociclo.circ}"
N=200
echo "circuito: $CIRC"
printf '%-18s %-8s %-10s %s\n' TESTE PC a0 DIVERGENCIA
for m in t*.mem ../exhaustive_instruction.mem; do
  nome=$(basename "$m" .mem)
  [ "$nome" = exhaustive_instruction ] && N=400 || N=200
  ./run.py "$m" $N --circ "$CIRC" > /tmp/sim.$$ 2>/dev/null
  ./ref.py "$m" $N                 > /tmp/ref.$$
  d=$(diff <(grep PC= /tmp/ref.$$) <(grep PC= /tmp/sim.$$) | grep '^>' | head -1 | sed 's/^> *//')
  a0=$(grep -E '^x10 ' /tmp/sim.$$ | awk '{print $3}'); [ -z "$a0" ] && a0=00000000
  if [ -z "$d" ]; then st=OK; else st=FALHOU; fi
  printf '%-18s %-8s %-10s %s\n' "$nome" "$st" "a0=$a0" "$d"
  rm -f /tmp/sim.$$ /tmp/ref.$$
done
