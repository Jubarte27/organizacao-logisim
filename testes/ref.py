#!/usr/bin/env python3
"""
Modelo de referencia RV32IM (so o subconjunto usado nos testes).
Gera o traco de PC esperado, no mesmo formato do harness Sim.java.

  ./ref.py programa.mem [ciclos]
"""
import sys

M = 0xFFFFFFFF
def s32(v): return v - (1 << 32) if v & 0x80000000 else v

def load_mem(path):
    txt = open(path).read().split()
    if txt[0] == 'v2.0': txt = txt[2:]
    words, i = [], 0
    for tok in txt:
        if '*' in tok:
            n, v = tok.split('*'); words += [int(v, 16)] * int(n)
        else:
            words.append(int(tok, 16))
    return words

def run(words, cycles):
    x = [0] * 32
    mem = {}
    pc = 0
    trace = []
    for _ in range(cycles + 1):
        trace.append(pc)
        idx = pc >> 2
        ins = words[idx] if idx < len(words) else 0
        op = ins & 0x7F
        rd = (ins >> 7) & 0x1F
        f3 = (ins >> 12) & 7
        rs1 = (ins >> 15) & 0x1F
        rs2 = (ins >> 20) & 0x1F
        f7 = (ins >> 25) & 0x7F
        iimm = s32((ins >> 20) | (0xFFFFF000 if ins & 0x80000000 else 0))
        simm = s32(((ins >> 7) & 0x1F) | ((ins >> 25) << 5) | (0xFFFFF000 if ins & 0x80000000 else 0))
        bimm = s32((((ins >> 8) & 0xF) << 1) | (((ins >> 25) & 0x3F) << 5) |
                   (((ins >> 7) & 1) << 11) | (0xFFFFF000 if ins & 0x80000000 else 0))
        uimm = ins & 0xFFFFF000
        jimm = s32((((ins >> 21) & 0x3FF) << 1) | (((ins >> 20) & 1) << 11) |
                   (((ins >> 12) & 0xFF) << 12) | (0xFFF00000 if ins & 0x80000000 else 0))
        a, b = x[rs1], x[rs2]
        npc = (pc + 4) & M
        if op == 0x33:                                   # R-type
            if f7 == 1:                                  # M extension
                r = {0: lambda: (a * b) & M}[f3]()
            else:
                r = {0: (lambda: (a - b) & M) if f7 == 0x20 else (lambda: (a + b) & M),
                     1: lambda: (a << (b & 31)) & M,
                     2: lambda: int(s32(a) < s32(b)),
                     3: lambda: int(a < b),
                     4: lambda: a ^ b,
                     5: lambda: (s32(a) >> (b & 31)) & M if f7 == 0x20 else a >> (b & 31),
                     6: lambda: a | b,
                     7: lambda: a & b}[f3]()
            if rd: x[rd] = r
        elif op == 0x13:                                 # OP-IMM
            r = {0: lambda: (a + iimm) & M,
                 2: lambda: int(s32(a) < iimm),
                 3: lambda: int(a < (iimm & M)),
                 4: lambda: a ^ (iimm & M),
                 6: lambda: a | (iimm & M),
                 7: lambda: a & (iimm & M),
                 1: lambda: (a << (iimm & 31)) & M,
                 5: lambda: ((s32(a) >> (iimm & 31)) & M) if (f7 == 0x20) else (a >> (iimm & 31))}[f3]()
            if rd: x[rd] = r
        elif op == 0x03:                                 # LOAD (so LW)
            addr = (a + iimm) & M
            if rd: x[rd] = mem.get(addr & ~3, 0)
        elif op == 0x23:                                 # STORE (so SW)
            mem[(a + simm) & ~3 & M] = b
        elif op == 0x63:                                 # BRANCH
            take = {0: a == b, 1: a != b, 4: s32(a) < s32(b), 5: s32(a) >= s32(b),
                    6: a < b, 7: a >= b}[f3]
            if take: npc = (pc + bimm) & M
        elif op == 0x37:                                 # LUI
            if rd: x[rd] = uimm
        elif op == 0x17:                                 # AUIPC
            if rd: x[rd] = (pc + uimm) & M
        elif op == 0x6F:                                 # JAL
            if rd: x[rd] = (pc + 4) & M
            npc = (pc + jimm) & M
        elif op == 0x67:                                 # JALR
            t = (a + iimm) & ~1 & M
            if rd: x[rd] = (pc + 4) & M
            npc = t
        pc = npc
    return trace, x

if __name__ == '__main__':
    words = load_mem(sys.argv[1])
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    trace, x = run(words, cycles)
    for i, pc in enumerate(trace):
        print('ciclo %5d  PC=%08x' % (i, pc))
    print('---- registradores ----')
    for i, v in enumerate(x):
        if v: print('%-4s = %08x' % ('x%d' % i, v))
