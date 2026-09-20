# LUI -- instrucao nova do grupo.
.globl _start
_start:
    lui   t0, 0x12345           # t0 = 0x12345000
    lui   t1, 0x12345
    beq   t0, t1, .L1
    beq   x0, x0, falha
.L1:
    lui   t2, 0xFFFFF           # t2 = 0xFFFFF000
    lui   t3, 0x1               # t3 = 0x00001000
    add   t4, t2, t3            # estoura para 0
    beq   t4, x0, .L2
    beq   x0, x0, falha
.L2:
    lui   t5, 0                 # LUI com imediato 0 -> 0
    beq   t5, x0, .L3
    beq   x0, x0, falha
.L3:
    lui   t6, 0x80000           # bit 31
    sub   a1, x0, t6            # -0x80000000 = 0x80000000
    beq   a1, t6, .L4
    beq   x0, x0, falha
.L4:
    lui   a0, 0x1
passa:
    beq   x0, x0, passa
falha:
    add   a0, x0, x0
    beq   x0, x0, falha
