#!/usr/bin/env python3
"""
Roda um programa no RISC-V Monociclo do Logisim, sem abrir a GUI.

  ./run.py programa.mem [ciclos] [--circ ARQ.circ]

Substitui o conteudo da ROM de instrucoes (310,360) do circuito 'main'
pelo arquivo .mem dado, grava um .circ temporario e chama o harness Java.
"""
import re, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CIRC = os.path.join(HERE, '..', 'RISCV_Monociclo.circ')
JAR = '/usr/share/logisim/logisim.jar'

def patch_rom(circ_text, loc, contents):
    pat = re.compile(r'(<comp lib="4" loc="\(' + re.escape(loc) +
                     r'\)" name="ROM">.*?<a name="contents">)(.*?)(</a>)', re.S)
    header = re.match(r'\s*addr/data:\s*\d+\s+\d+', pat.search(circ_text).group(2)).group(0)
    body = contents.strip()
    if body.startswith('v2.0 raw'):
        body = body[len('v2.0 raw'):].strip()
    new = header + '\n' + body + '\n'
    out, n = pat.subn(lambda m: m.group(1) + new + m.group(3), circ_text, count=1)
    assert n == 1, 'ROM ' + loc + ' nao encontrada'
    return out

def main():
    args = [a for a in sys.argv[1:]]
    circ = DEFAULT_CIRC
    if '--circ' in args:
        i = args.index('--circ'); circ = args[i+1]; del args[i:i+2]
    prog = args[0]
    cycles = int(args[1]) if len(args) > 1 else 60

    text = open(circ).read()
    text = patch_rom(text, '310,360', open(prog).read())

    tmp = tempfile.NamedTemporaryFile('w', suffix='.circ', delete=False, dir=HERE)
    tmp.write(text); tmp.close()
    try:
        out = subprocess.run(['java', '-cp', JAR + ':' + HERE, 'Sim', tmp.name, str(cycles)],
                             capture_output=True, text=True)
        sys.stdout.write(out.stdout)
        sys.stderr.write(out.stderr)
    finally:
        os.unlink(tmp.name)

main()
