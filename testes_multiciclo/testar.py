#!/usr/bin/env python3
"""
Testa programas no RISCV_Multiciclo.circ sem abrir o Logisim.

  ./testar.py                      # bateria: teste_multiciclo.s + testes do monociclo
  ./testar.py prog.s|prog.mem      # um programa, com detalhes
  opcoes: --circ ARQ.circ   --traco (mostra estado/PC/escritas ciclo a ciclo)

Para cada programa:
1. roda um modelo RV32IM de referencia (memoria unica, como no multiciclo);
2. roda o circuito (MultiSim.java);
3. compara a sequencia de instrucoes buscadas (PC em cada estado 0), as escritas no
   banco de registradores e as escritas na memoria. Qualquer diferenca = falha.
4. se o .s tiver linhas GUARDA/DESVIO, mostra a assinatura caso a caso.
"""
import importlib.util, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = '/usr/share/logisim/logisim.jar'
CIRC = os.path.join(HERE, '..', 'RISCV_Multiciclo.circ')

# modelo de referencia e desmontador: os mesmos do teste do pipeline
_spec = importlib.util.spec_from_file_location('modelo', os.path.join(HERE, '..', 'testes_pipeline', 'testar.py'))
modelo = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(modelo)
disasm, REG = modelo.disasm, modelo.REG

def monta(prog):
    if prog.endswith('.s'):
        subprocess.run(['bash', os.path.join(HERE, '..', 'testes', 'asm.sh'), prog], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return prog, prog[:-2] + '.mem'
    src = prog[:-4] + '.s'
    return (src if os.path.exists(src) else None), prog

def roda_circuito(circ, mem, ciclos):
    cls = os.path.join(HERE, 'MultiSim.class')
    if not os.path.exists(cls) or os.path.getmtime(cls) < os.path.getmtime(os.path.join(HERE, 'MultiSim.java')):
        subprocess.run(['javac', '--release', '8', '-nowarn', '-cp', JAR, 'MultiSim.java'], cwd=HERE, check=True,
                       stderr=subprocess.DEVNULL)
    out = subprocess.run(['java', '-cp', JAR + ':' + HERE, 'MultiSim', os.path.abspath(circ),
                          os.path.abspath(mem), str(ciclos)], capture_output=True, text=True).stdout
    busca, wb, st, regs, dmem, linhas = [], [], [], {}, {}, []
    parte = 'ciclos'
    for l in out.splitlines():
        if l.startswith('---- registradores'): parte = 'regs'; continue
        if l.startswith('---- memoria'): parte = 'mem'; continue
        if parte == 'ciclos':
            linhas.append(l)
            c = int(l.split()[1])
            if ' E=0 ' in l: busca.append((c, re.search(r'PC=(\S+)', l).group(1)))
            m = re.search(r' WB=(\S+):(\S+)', l)
            if m and m.group(1) != '0': wb.append((c, m.group(1), m.group(2)))
            m = re.search(r' MEM=(\S+):(\S+)', l)
            if m: st.append((c, m.group(1), m.group(2)))
        elif parte == 'regs':
            k, v = l.split(' = '); regs[int(k[1:])] = v
        else:
            k, v = l.split(' = '); dmem[int(k.strip('[]'), 16)] = v
    if not linhas:
        raise RuntimeError('o harness nao gerou saida (circuito nao abriu?)')
    return busca, wb, st, regs, dmem, linhas

def base_assinatura(src):
    for l in open(src):
        m = re.search(r'@assinatura\s+(0x[0-9a-fA-F]+)', l)
        if m: return int(m.group(1), 16)
    return 0

def testa(prog, circ, detalhe, traco=False):
    src, mem = monta(prog)
    words = modelo.load_mem(mem)
    traco_ref, wb_ref, st_ref, x_ref, mem_ref = modelo.referencia(words, unificada=True)
    busca, wb, st, regs, dmem, linhas = roda_circuito(circ, mem, 5 * len(traco_ref) + 20)
    if traco: print('\n'.join(linhas))
    erros = []
    # o modelo para no laco final; o que o circuito faz depois de buscar a instrucao
    # seguinte a ultima do modelo (voltas extras do laco) nao entra na comparacao
    if len(busca) > len(traco_ref):
        corte = busca[len(traco_ref)][0]
        wb = [w for w in wb if w[0] < corte]; st = [w for w in st if w[0] < corte]

    # 1. instrucoes buscadas, na ordem
    for i, (pc, ins, _, _, _) in enumerate(traco_ref):
        if i >= len(busca):
            erros.append('BUSCA   parou antes de buscar %08x %s' % (pc, disasm(ins))); break
        c, pc2 = busca[i]
        if pc2 != '%08x' % pc:
            ant = traco_ref[i - 1] if i else None
            erros.append('BUSCA   ciclo %d: esperado buscar %08x %s, circuito buscou %s%s' % (
                c, pc, disasm(ins), pc2,
                ' (depois de %08x %s)' % (ant[0], disasm(ant[1])) if ant else ''))
            break
    # 2. escritas no banco
    for i, (pc, rd, v) in enumerate(wb_ref):
        if i >= len(wb):
            erros.append('WB      faltou %08x %-22s %s <- %08x' % (pc, disasm(mem_ins(words, pc)), REG[rd], v)); break
        c, rd2, v2 = wb[i]
        if str(rd) != rd2:
            erros.append('WB      ciclo %d: esperado %08x %s: %s <- %08x ; circuito x%s <- %s' % (
                c, pc, disasm(mem_ins(words, pc)), REG[rd], v, rd2, v2)); break
        if '%08x' % v != v2:
            erros.append('WB      %08x %-22s %-4s esperado %08x  circuito %s' % (pc, disasm(mem_ins(words, pc)), REG[rd], v, v2))
    if len(wb) > len(wb_ref):
        c, rd2, v2 = wb[len(wb_ref)]
        erros.append('WB      sobrou: ciclo %d x%s <- %s (escrita que o modelo nao faz)' % (c, rd2, v2))
    # 3. escritas na memoria
    for i, (pc, ad, v) in enumerate(st_ref):
        if i >= len(st):
            erros.append('MEM     faltou %08x %-22s [%08x] <- %08x' % (pc, disasm(mem_ins(words, pc)), ad, v)); break
        c, ad2, v2 = st[i]
        if '%08x' % ad != ad2 or '%08x' % v != v2:
            erros.append('MEM     %08x %-22s esperado [%08x] <- %08x  circuito [%s] <- %s' % (
                pc, disasm(mem_ins(words, pc)), ad, v, ad2, v2))
    for c, ad2, v2 in st[len(st_ref):]:
        erros.append('MEM     sobrou: ciclo %d [%s] <- %s' % (c, ad2, v2))

    ciclos = busca[len(traco_ref)][0] if len(busca) > len(traco_ref) else None
    resumo = dict(nome=os.path.basename(mem)[:-4], n=len(traco_ref), ciclos=ciclos, erros=erros,
                  a0=regs.get(10, '00000000'), a0_ref='%08x' % x_ref[10])

    if detalhe:
        print('circuito : %s' % os.path.relpath(circ))
        print('programa : %s  (%d instrucoes executadas%s)' % (
            os.path.relpath(mem), len(traco_ref), ', %d ciclos' % ciclos if ciclos else ''))
        print('\n== Comparacao com o modelo (busca, escritas no banco, escritas na memoria) ==')
        if erros:
            for e in erros: print('   ' + e)
        else:
            print('   %d instrucoes buscadas, %d escritas no banco, %d na memoria: tudo igual ao modelo'
                  % (len(traco_ref), len(wb_ref), len(st_ref)))
        if src:
            casos = modelo.assinatura(src, base=base_assinatura(src))
            if casos:
                casos[0] = (casos[0][0], '[JALR] instrucoes logo depois de um JALR nao podem executar (tem que ficar 0)', 0)
                print('\n== Assinatura (a partir de 0x%x) ==' % casos[0][0])
                print('   %-7s %-7s %-10s %-10s %s' % ('', 'end.', 'esperado', 'circuito', 'caso'))
                porinstr = {}
                for end, desc, esp_coment in casos:
                    esp = mem_ref.get(end, 0)
                    if esp_coment is not None and esp_coment != esp:
                        print('   (aviso: comentario do .s diz %08x, modelo calcula %08x)' % (esp_coment, esp))
                    got = dmem.get(end, '00000000'); ok = got == '%08x' % esp
                    tag = re.match(r'\[(\S+?)\]', desc); tag = tag.group(1) if tag else '?'
                    porinstr.setdefault(tag, [0, 0])[0 if ok else 1] += 1
                    print('   %-7s 0x%04x  %08x   %-10s %s' % ('OK' if ok else 'FALHOU', end, esp, got, desc))
                print('\n== Resumo por instrucao ==')
                for tag, (ok, bad) in porinstr.items():
                    print('   %-6s %s' % (tag, 'OK (%d casos)' % ok if not bad else 'FALHOU em %d de %d casos' % (bad, ok + bad)))
    return resumo

def mem_ins(words, pc):
    return words[pc >> 2] if (pc >> 2) < len(words) else 0

NOTAS = {'t8_addi': 'esperado: ADDI nao e instrucao do grupo (limitacao conhecida, ver README)'}

def main():
    args = sys.argv[1:]
    circ = CIRC
    if '--circ' in args:
        i = args.index('--circ'); circ = args[i + 1]; del args[i:i + 2]
    traco = '--traco' in args
    args = [a for a in args if a != '--traco']
    if args:
        testa(args[0], circ, True, traco); return

    progs = [os.path.join(HERE, 'teste_multiciclo.s')]
    tdir = os.path.join(HERE, '..', 'testes')
    progs += sorted(os.path.join(tdir, f) for f in os.listdir(tdir) if re.match(r't\d.*\.mem$', f))
    progs.append(os.path.join(HERE, '..', 'exhaustive_instruction.mem'))
    print('circuito: %s\n' % os.path.relpath(circ))
    print('%-24s %-7s %6s %7s  %-10s %-10s %s' % ('PROGRAMA', 'RESULT.', 'INSTR', 'CICLOS', 'a0', 'a0 esper.', 'PRIMEIRA DIFERENCA'))
    for p in progs:
        r = testa(p, circ, False)
        res = 'OK' if not r['erros'] else ('(nota)' if r['nome'] in NOTAS else 'FALHOU')
        dif = r['erros'][0] if r['erros'] else ''
        if r['erros'] and r['nome'] in NOTAS: dif = NOTAS[r['nome']] + ' | ' + dif.split(None, 1)[1]
        print('%-24s %-7s %6d %7s  %-10s %-10s %s' % (r['nome'], res, r['n'],
              r['ciclos'] or '-', r['a0'], r['a0_ref'], dif))
    print()
    testa(progs[0], circ, True)

if __name__ == '__main__':
    main()
