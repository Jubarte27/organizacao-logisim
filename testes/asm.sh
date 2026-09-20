#!/bin/bash
# asm.sh prog.s  ->  prog.mem  (formato "v2.0 raw" do Logisim)
set -e
AS=riscv64-unknown-elf-as; LD=riscv64-unknown-elf-ld; OC=riscv64-unknown-elf-objcopy
command -v $AS >/dev/null || { AS=riscv64-linux-gnu-as; LD=riscv64-linux-gnu-ld; OC=riscv64-linux-gnu-objcopy; }
src="$1"; base="${src%.s}"; tmp=$(mktemp -d)
$AS -march=rv32im -mabi=ilp32 -o "$tmp/o.o" "$src"
$LD -m elf32lriscv -Ttext=0 --no-relax -o "$tmp/o.elf" "$tmp/o.o"
$OC -O binary --only-section=.text "$tmp/o.elf" "$tmp/o.bin"
python3 - "$tmp/o.bin" > "$base.mem" <<'PY'
import sys,struct
d=open(sys.argv[1],'rb').read()
d+=b'\0'*((-len(d))%4)
ws=[struct.unpack('<I',d[i:i+4])[0] for i in range(0,len(d),4)]
print('v2.0 raw')
for i in range(0,len(ws),8):
    print(' '.join('%x'%w for w in ws[i:i+8]))
PY
rm -rf "$tmp"; echo "gerado $base.mem ($(( $(wc -w < "$base.mem") - 2 )) instrucoes)"
