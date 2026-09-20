# MUL -- instrucao nova do grupo (so os 32 bits baixos).
.globl _start
_start:
    lui   t0, 0x1               # t0 = 0x00001000
    mul   t1, t0, t0            # 0x1000 * 0x1000 = 0x01000000
    lui   t2, 0x1000
    beq   t1, t2, .L1
    beq   x0, x0, falha
.L1:
    sub   t3, x0, t0            # t3 = -0x1000
    mul   t4, t3, t0            # -0x1000 * 0x1000 = -0x01000000
    sub   t5, x0, t2
    beq   t4, t5, .L2
    beq   x0, x0, falha
.L2:
    mul   t6, t3, t3            # (-0x1000)*(-0x1000) = +0x01000000
    beq   t6, t2, .L3
    beq   x0, x0, falha
.L3:
    lui   a1, 0x12345
    mul   a2, a1, t0            # 0x12345000 * 0x1000 -> low32 = 0x45000000
    lui   a3, 0x45000
    beq   a2, a3, .L4
    beq   x0, x0, falha
.L4:
    mul   a4, t0, x0            # x * 0 = 0
    beq   a4, x0, .L5
    beq   x0, x0, falha
.L5:
    lui   a0, 0x1
passa:
    beq   x0, x0, passa
falha:
    add   a0, x0, x0
    beq   x0, x0, falha
