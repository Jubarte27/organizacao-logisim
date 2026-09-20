#!/usr/bin/env python3
"""
Aplica as 3 correcoes no RISCV_Monociclo.circ.
  ./corrigir.py entrada.circ saida.circ
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
x = open(src).read()

# ---------------------------------------------------------------- ERRO 1: LW
pat = re.compile(r'(<comp lib="4" loc="\(230,760\)" name="ROM">.*?<a name="contents">addr/data: 7 8\n)(.*?)(</a>)', re.S)
m = pat.search(x); assert m, 'ROM de controle nao encontrada'
rom = m.group(2)
assert rom.split()[3] == '6', 'valor inesperado no endereco 3: ' + rom.split()[3]
toks = rom.split(); toks[3] = 'c6'
novo = ' '.join(toks[:8]) + '\n' + ' '.join(toks[8:16]) + '\n' + ' '.join(toks[16:]) + '\n'
x = pat.sub(lambda mm: mm.group(1) + novo + mm.group(3), x, count=1)
print('ERRO 1 corrigido: ROM de controle [0x03] 6 -> c6')

# ------------------------------------------------------- ERRO 2: SLTIU sem sinal
alu = re.search(r'<circuit name="ALU">.*?</circuit>', x, re.S)
old = '<comp lib="3" loc="(390,540)" name="Comparator">\n      <a name="width" val="32"/>\n    </comp>'
new = '<comp lib="3" loc="(390,540)" name="Comparator">\n      <a name="width" val="32"/>\n      <a name="mode" val="unsigned"/>\n    </comp>'
assert x.count(old) == 1, 'comparador (390,540) nao encontrado (ou ambiguo)'
x = x.replace(old, new)
print('ERRO 2 corrigido: Comparator (390,540) do ALU -> mode=unsigned')

# --------------------------------------------------- ERRO 3: BEQ seleciona por funct3
main_start = x.index('<circuit name="main">')
main_end = x.index('</circuit>', main_start)
main = x[main_start:main_end]

# 3a) remove o OR de (710,310)
orgate = re.search(r'\s*<comp lib="1" loc="\(710,310\)" name="OR Gate">.*?</comp>', main, re.S)
assert orgate, 'OR gate (710,310) nao encontrado'
main = main[:orgate.start()] + main[orgate.end():]

# 3b) mux 1 bit facing north no mesmo lugar + logica de selecao (via tunnels)
add = '''
    <comp lib="2" loc="(710,310)" name="Multiplexer">
      <a name="facing" val="north"/>
      <a name="enable" val="false"/>
    </comp>
    <comp lib="0" loc="(690,330)" name="Tunnel">
      <a name="label" val="BEQsel"/>
    </comp>
    <comp lib="0" loc="(1200,700)" name="Tunnel">
      <a name="facing" val="west"/>
      <a name="label" val="BEQsel"/>
    </comp>
    <comp lib="0" loc="(1120,690)" name="Tunnel">
      <a name="facing" val="west"/>
      <a name="width" val="3"/>
      <a name="label" val="funct3"/>
    </comp>
    <comp lib="0" loc="(430,460)" name="Tunnel">
      <a name="facing" val="west"/>
      <a name="width" val="3"/>
      <a name="label" val="funct3"/>
    </comp>
    <comp lib="0" loc="(1120,710)" name="Constant">
      <a name="width" val="3"/>
      <a name="value" val="0x0"/>
    </comp>
    <comp lib="3" loc="(1160,700)" name="Comparator">
      <a name="width" val="3"/>
    </comp>
    <wire from="(1160,700)" to="(1200,700)"/>
'''
# separa o fio (430,360)-(430,510) para o tunnel funct3 encostar em (430,460)
oldw = '<wire from="(430,360)" to="(430,510)"/>'
assert oldw in main, 'fio do funct3 nao encontrado'
main = main.replace(oldw, '<wire from="(430,360)" to="(430,460)"/>\n    <wire from="(430,460)" to="(430,510)"/>')
main = main + add
x = x[:main_start] + main + x[main_end:]
print('ERRO 3 corrigido: OR (710,310) -> Multiplexer facing=north, select = (funct3 == 0)')

open(dst, 'w').write(x)
print('gravado em', dst)
