# ERRO 2 -- SLTIU compara com sinal.
.globl _start
_start:
    sltiu t1, x0, 1             # 0 <u 1 -> 1     (da 1 nos dois casos)

    sltiu t0, x0, -1            # 0 <u 0xFFFFFFFF -> 1
    beq   t0, t1, .L1           #   com o bug (com sinal): 0 < -1 -> 0
    beq   x0, x0, falha
.L1:
    sub   t2, x0, t1            # t2 = 0xFFFFFFFF
    sltiu t3, t2, 1             # 0xFFFFFFFF <u 1 -> 0
    beq   t3, x0, .L2           #   com o bug: -1 < 1 -> 1
    beq   x0, x0, falha
.L2:
    sltiu t4, t2, -1            # 0xFFFFFFFF <u 0xFFFFFFFF -> 0
    beq   t4, x0, .L3
    beq   x0, x0, falha
.L3:
    lui   t5, 0x80000           # t5 = 0x80000000 (negativo com sinal)
    sltiu t6, t5, 1             # 0x80000000 <u 1 -> 0
    beq   t6, x0, .L4           #   com o bug: -2^31 < 1 -> 1
    beq   x0, x0, falha
.L4:
    sltiu a1, x0, 0             # 0 <u 0 -> 0
    beq   a1, x0, .L5
    beq   x0, x0, falha
.L5:
    lui   a0, 0x1
passa:
    beq   x0, x0, passa
falha:
    add   a0, x0, x0
    beq   x0, x0, falha
