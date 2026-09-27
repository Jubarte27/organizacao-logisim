#!/usr/bin/env python3
"""
Testa um programa no RISCV_Pipeline.circ sem abrir o Logisim.

  ./testar.py [programa.s|programa.mem] [--circ ARQ.circ] [--traco]

  padrao: teste_pipeline.s em ../RISCV_Pipeline.circ

1. Monta o .s (../testes/asm.sh) se preciso.
2. Roda o programa num modelo RV32IM de referencia (sem pipeline).
3. Confere se o programa respeita as regras deste pipeline (sem forwarding:
   distancia >= 4 entre escrita e leitura; nops nos 3 delay slots dos desvios).
   Se respeitar, o resultado no pipeline TEM que ser igual ao do modelo.
4. Roda o circuito (PipeSim.java) e compara:
   - a sequencia de escritas no banco de registradores (estagio WB);
   - a sequencia de escritas na memoria de dados (estagio MEM);
   - a "assinatura" (palavras gravadas a partir do endereco 0), caso a caso,
     usando os comentarios das linhas GUARDA/DESVIO do .s como descricao.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = '/usr/share/logisim/logisim.jar'
M = 0xFFFFFFFF
NOP = 0x00000013
DISTANCIA = 4          # leitura precisa estar >= 4 instrucoes depois da escrita
DELAY_SLOTS = 3        # BEQ/BGE resolvem no MEM
JALR_FLUSH = 3         # JALR descarta as 3 seguintes

def s32(v): return v - (1 << 32) if v & 0x80000000 else v

# ---------------------------------------------------------------- programa
def load_mem(path):
    toks = open(path).read().split()
    if toks[0] == 'v2.0': toks = toks[2:]
    words = []
    for t in toks:
        if '*' in t:
            n, v = t.split('*'); words += [int(v, 16)] * int(n)
        else:
            words.append(int(t, 16))
    return words

REG = ['zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2', 's0', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
       'a6', 'a7', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6']

def campos(ins):
    op = ins & 0x7F; rd = (ins >> 7) & 31; f3 = (ins >> 12) & 7
    rs1 = (ins >> 15) & 31; rs2 = (ins >> 20) & 31; f7 = ins >> 25
    iimm = s32((ins >> 20) | (0xFFFFF000 if ins & 0x80000000 else 0))
    simm = s32(((ins >> 7) & 31) | ((ins >> 25) << 5) | (0xFFFFF000 if ins & 0x80000000 else 0))
    bimm = s32((((ins >> 8) & 15) << 1) | (((ins >> 25) & 63) << 5) | (((ins >> 7) & 1) << 11)
               | (0xFFFFF000 if ins & 0x80000000 else 0))
    return op, rd, f3, rs1, rs2, f7, iimm, simm, bimm

def disasm(ins):
    op, rd, f3, rs1, rs2, f7, iimm, simm, bimm = campos(ins)
    r = lambda i: REG[i]
    if ins == NOP: return 'nop'
    if op == 0x33:
        n = {(0, 0): 'add', (0, 0x20): 'sub', (0, 1): 'mul', (7, 0): 'and', (6, 0): 'or'}.get((f3, f7), 'r?')
        return '%s %s,%s,%s' % (n, r(rd), r(rs1), r(rs2))
    if op == 0x13:
        n = {0: 'addi', 3: 'sltiu'}.get(f3, 'opimm?')
        return '%s %s,%s,%d' % (n, r(rd), r(rs1), iimm)
    if op == 0x03: return 'lw %s,%d(%s)' % (r(rd), iimm, r(rs1))
    if op == 0x23: return 'sw %s,%d(%s)' % (r(rs2), simm, r(rs1))
    if op == 0x63:
        n = {0: 'beq', 5: 'bge'}.get(f3, 'b?')
        return '%s %s,%s,%+d' % (n, r(rs1), r(rs2), bimm)
    if op == 0x37: return 'lui %s,0x%x' % (r(rd), ins >> 12)
    if op == 0x67: return 'jalr %s,%d(%s)' % (r(rd), iimm, r(rs1))
    return '?%08x' % ins

# ---------------------------------------------------------------- modelo de referencia
def referencia(words, max_passos=20000, unificada=False):
    """Executa RV32IM (subconjunto). Devolve traco dinamico, escritas e estado final.
    unificada=True: instrucoes e dados na mesma memoria (multiciclo)."""
    x = [0] * 32; pc = 0
    mem = {4 * i: w for i, w in enumerate(words)} if unificada else {}
    vistos = set()
    traco = []          # (pc, ins, lidos, escrito, desviou)
    wb, st = [], []     # escritas no banco (pc, rd, val) e na memoria (pc, end, val)
    for _ in range(max_passos):
        if unificada: ins = mem.get(pc, 0)
        else: ins = words[pc >> 2] if (pc >> 2) < len(words) else 0
        op, rd, f3, rs1, rs2, f7, iimm, simm, bimm = campos(ins)
        a, b = x[rs1], x[rs2]
        npc = (pc + 4) & M; w = None; lidos = (); desviou = False
        if op == 0x33:
            lidos = (rs1, rs2)
            if f7 == 1 and f3 == 0: w = (a * b) & M
            elif f3 == 0: w = (a - b) & M if f7 == 0x20 else (a + b) & M
            elif f3 == 7: w = a & b
            elif f3 == 6: w = a | b
            else: raise ValueError('R-type nao suportado em %08x' % pc)
        elif op == 0x13:
            lidos = (rs1,)
            if f3 == 0: w = (a + iimm) & M
            elif f3 == 3: w = int(a < (iimm & M))
            else: raise ValueError('OP-IMM nao suportado em %08x' % pc)
        elif op == 0x03:
            lidos = (rs1,); w = mem.get((a + iimm) & M & ~3, 0)
        elif op == 0x23:
            lidos = (rs1, rs2); ad = (a + simm) & M & ~3; mem[ad] = b; st.append((pc, ad, b))
        elif op == 0x63:
            lidos = (rs1, rs2)
            desviou = {0: a == b, 5: s32(a) >= s32(b)}[f3]
            if desviou: npc = (pc + bimm) & M
        elif op == 0x37:
            w = ins & 0xFFFFF000
        elif op == 0x67:
            lidos = (rs1,); w = (pc + 4) & M; npc = (a + iimm) & ~1 & M
        elif ins == 0:
            pass        # bolha (opcode 0 = palavra de controle 0 no pipeline)
        else:
            raise ValueError('opcode %02x nao suportado em %08x' % (op, pc))
        escrito = rd if (w is not None and rd != 0) else None
        if escrito is not None:
            x[rd] = w; wb.append((pc, rd, w))
        traco.append((pc, ins, lidos, escrito, desviou))
        if ins == 0x00000063:   # beq x0,x0,0 : laco final
            break
        estado = (npc, tuple(x), len(st))
        if estado in vistos:    # estado da maquina repetiu: laco infinito (fim do programa)
            break
        vistos.add(estado)
        pc = npc
    else:
        raise RuntimeError('programa nao chegou a um laco final')
    return traco, wb, st, x, mem

def confere_hazards(traco, words):
    """Posicao de cada instrucao no pipeline e violacoes das regras do circuito."""
    problemas = []; ult_escrita = {}; slot = 0
    for pc, ins, lidos, escrito, desviou in traco:
        for r in lidos:
            if r and r in ult_escrita and slot - ult_escrita[r][0] < DISTANCIA:
                problemas.append('%08x %-22s le %s escrito em %08x (distancia %d < %d)' % (
                    pc, disasm(ins), REG[r], ult_escrita[r][1], slot - ult_escrita[r][0], DISTANCIA))
        if escrito is not None: ult_escrita[escrito] = (slot, pc)
        op = ins & 0x7F
        if op == 0x63:
            for k in range(1, DELAY_SLOTS + 1):
                i = (pc >> 2) + k
                if i < len(words) and words[i] != NOP:
                    problemas.append('%08x %-22s delay slot %08x nao e nop' % (pc, disasm(ins), pc + 4 * k))
            slot += 1 + (DELAY_SLOTS if desviou else 0)
        elif op == 0x67:
            slot += 1 + JALR_FLUSH
        else:
            slot += 1
    return slot, problemas

# ---------------------------------------------------------------- circuito
def roda_circuito(circ, mem, ciclos):
    cls = os.path.join(HERE, 'PipeSim.class')
    if not os.path.exists(cls) or os.path.getmtime(cls) < os.path.getmtime(os.path.join(HERE, 'PipeSim.java')):
        subprocess.run(['javac', '--release', '8', '-nowarn', '-cp', JAR, 'PipeSim.java'], cwd=HERE, check=True,
                       stderr=subprocess.DEVNULL)
    out = subprocess.run(['java', '-cp', JAR + ':' + HERE, 'PipeSim', circ, mem, str(ciclos)],
                         capture_output=True, text=True).stdout
    wb, st, regs, dmem, linhas = [], [], {}, {}, []
    parte = 'ciclos'
    for l in out.splitlines():
        if l.startswith('---- registradores'): parte = 'regs'; continue
        if l.startswith('---- memoria'): parte = 'mem'; continue
        if parte == 'ciclos':
            linhas.append(l)
            c = int(l.split()[1])
            m = re.search(r' WB=(\S+):(\S+)', l)
            if m and m.group(1) != '0':
                wb.append((c, m.group(1), m.group(2)))
            m = re.search(r' MEM=(\S+):(\S+)', l)
            if m: st.append((c, m.group(1), m.group(2)))
        elif parte == 'regs':
            k, v = l.split(' = '); regs[int(k[1:])] = v
        else:
            k, v = l.split(' = '); dmem[int(k.strip('[]'), 16)] = v
    if not linhas:
        raise RuntimeError('o harness nao gerou saida (circuito nao abriu?)')
    return wb, st, regs, dmem, linhas

def assinatura(src, base=0, flush=True):
    """Descricao de cada palavra da assinatura, na ordem das linhas GUARDA/DESVIO do .s."""
    casos = [(base, '[JALR] instrucoes logo depois de um JALR (tem que ficar 0: flush)', 0)] if flush else []
    end = base + (4 if flush else 0); dentro_macro = False
    for l in open(src):
        s = l.strip()
        if s.startswith('.macro'): dentro_macro = True; continue
        if s.startswith('.endm'): dentro_macro = False; continue
        if dentro_macro: continue
        if re.match(r'(GUARDA|DESVIO)\b', s):
            desc = s.split('#', 1)[1].strip() if '#' in s else s
            esp = None
            if '=>' in desc:
                e = desc.split('=>')[1].strip().lower()
                esp = {'desviou': 0x1000, 'nao desviou': 0x2000}.get(e)
                if esp is None:
                    try: esp = int(e, 16)
                    except ValueError: pass
                desc = desc.split('=>')[0].strip()
            casos.append((end, desc, esp)); end += 4
    return casos

# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    circ = os.path.join(HERE, '..', 'RISCV_Pipeline.circ')
    if '--circ' in args:
        i = args.index('--circ'); circ = args[i + 1]; del args[i:i + 2]
    traco_on = '--traco' in args
    args = [a for a in args if a != '--traco']
    prog = args[0] if args else os.path.join(HERE, 'teste_pipeline.s')
    src = None
    if prog.endswith('.s'):
        src = prog
        subprocess.run(['bash', os.path.join(HERE, '..', 'testes', 'asm.sh'), prog], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        prog = prog[:-2] + '.mem'
    elif os.path.exists(prog[:-4] + '.s'):
        src = prog[:-4] + '.s'
    words = load_mem(prog)

    traco, wb_ref, st_ref, x_ref, mem_ref = referencia(words)
    slots, problemas = confere_hazards(traco, words)
    print('circuito : %s' % os.path.relpath(circ))
    print('programa : %s  (%d instrucoes, %d executadas, ~%d ciclos no pipeline)' % (
        os.path.relpath(prog), len(words), len(traco), slots + 4))
    if problemas:
        print('\n!! o programa NAO respeita as regras do pipeline -- resultado nao e confiavel:')
        for p in problemas: print('   ' + p)
    else:
        print('regras do pipeline (distancia >= 4, nops nos delay slots): OK')

    wb, st, regs, dmem, linhas = roda_circuito(os.path.abspath(circ), os.path.abspath(prog), slots + 12)
    if traco_on:
        print('\n'.join(linhas))

    # --- escritas no banco, na ordem
    print('\n== Escritas no banco de registradores (WB), na ordem ==')
    div = 0
    for i, (pc, rd, v) in enumerate(wb_ref):
        if i >= len(wb):
            print('   FALTOU  %08x %-24s %s <- %08x (o circuito parou de escrever)' % (pc, disasm(words[pc >> 2]), REG[rd], v))
            div += 1; break
        c, rd2, v2 = wb[i]
        if str(rd) != rd2:
            print('   DIVERGIU no ciclo %d: esperado %08x %-22s %s <- %08x ; circuito escreveu x%s <- %s'
                  % (c, pc, disasm(words[pc >> 2]), REG[rd], v, rd2, v2))
            print('            (fluxo de controle diferente a partir daqui -- comparacao de escritas parou)')
            div += 1; break
        if '%08x' % v != v2:
            print('   ERRADO  %08x %-24s %-4s esperado %08x  circuito %s' % (pc, disasm(words[pc >> 2]), REG[rd], v, v2))
            div += 1
    else:
        if len(wb) > len(wb_ref):
            c, rd2, v2 = wb[len(wb_ref)]
            print('   SOBROU  ciclo %d: x%s <- %s (escrita que o modelo nao faz)' % (c, rd2, v2)); div += 1
    if not div: print('   %d escritas, todas iguais ao modelo' % len(wb_ref))

    print('\n== Escritas na memoria de dados (MEM), na ordem ==')
    div = 0
    for i, (pc, ad, v) in enumerate(st_ref):
        if i >= len(st):
            print('   FALTOU  %08x %-24s [%08x] <- %08x' % (pc, disasm(words[pc >> 2]), ad, v)); div += 1; break
        c, ad2, v2 = st[i]
        if '%08x' % ad != ad2 or '%08x' % v != v2:
            print('   ERRADO  %08x %-24s esperado [%08x] <- %08x  circuito [%s] <- %s (ciclo %d)'
                  % (pc, disasm(words[pc >> 2]), ad, v, ad2, v2, c)); div += 1
    if len(st) > len(st_ref):
        for c, ad2, v2 in st[len(st_ref):]:
            print('   SOBROU  ciclo %d: [%s] <- %s (escrita que o modelo nao faz)' % (c, ad2, v2)); div += 1
    if not div: print('   %d escritas, todas iguais ao modelo' % len(st_ref))

    # --- assinatura caso a caso
    if src:
        print('\n== Assinatura (memoria de dados a partir do endereco 0) ==')
        print('   %-7s %-6s %-10s %-10s %s' % ('', 'end.', 'esperado', 'circuito', 'caso'))
        resumo = {}
        for end, desc, esp_coment in assinatura(src):
            esp = mem_ref.get(end, 0)
            if esp_coment is not None and esp_coment != esp:
                print('   (aviso: comentario do .s diz %08x, modelo calcula %08x)' % (esp_coment, esp))
            got = dmem.get(end, '00000000')
            ok = got == '%08x' % esp
            tag = re.match(r'\[(\S+?)\]', desc); tag = tag.group(1) if tag else '?'
            resumo.setdefault(tag, [0, 0]); resumo[tag][0 if ok else 1] += 1
            print('   %-7s 0x%03x  %08x   %-10s %s' % ('OK' if ok else 'FALHOU', end, esp, got, desc))
        print('\n== Resumo por instrucao ==')
        for tag, (ok, bad) in resumo.items():
            print('   %-6s %s' % (tag, 'OK (%d casos)' % ok if not bad else 'FALHOU em %d de %d casos' % (bad, ok + bad)))

if __name__ == '__main__':
    main()
