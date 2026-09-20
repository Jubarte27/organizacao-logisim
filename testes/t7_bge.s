# BGE -- instrucao nova do grupo (comparacao COM sinal).
.globl _start
_start:
    lui   t0, 0x2               # t0 = +0x2000
    lui   t1, 0x1               # t1 = +0x1000
    sub   t2, x0, t1            # t2 = -0x1000

    bge   t0, t1, .L1           # +maior >= +menor -> desvia
    beq   x0, x0, falha
.L1:
    bge   t1, t0, falha         # +menor >= +maior -> NAO desvia
    bge   t1, t1, .L2           # iguais -> desvia
    beq   x0, x0, falha
.L2:
    bge   t0, t2, .L3           # positivo >= negativo -> desvia
    beq   x0, x0, falha
.L3:
    bge   t2, t0, falha         # negativo >= positivo -> NAO desvia
    bge   t2, t2, .L4           # negativos iguais -> desvia
    beq   x0, x0, falha
.L4:
    sub   t4, x0, t0            # t4 = -0x2000
    bge   t2, t4, .L5           # -0x1000 >= -0x2000 -> desvia
    beq   x0, x0, falha
.L5:
    bge   t4, t2, falha         # -0x2000 >= -0x1000 -> NAO desvia
    lui   a0, 0x1
passa:
    beq   x0, x0, passa
falha:
    add   a0, x0, x0
    beq   x0, x0, falha
