# Regressao das instrucoes que JA existiam no circuito original:
#   LW, SW, ADD, SUB, AND, OR, BEQ
# (LUI e usado so para montar constantes -- sem ADDI nao ha outro jeito)
#   a0 = 1  -> passou     a0 = 0 -> falhou
.globl _start
_start:
    lui   s1, 0x1               # s1 = 0x00001000  base dos dados
    lui   t0, 0xABCDE           # t0 = 0xABCDE000
    lui   t1, 0xF               # t1 = 0x0000F000

    add   t2, t0, t1            # ADD  -> 0xABCED000
    sub   t3, t0, t1            # SUB  -> 0xABCCF000
    and   t4, t0, t1            # AND  -> 0x0000C000
    or    t5, t0, t1            # OR   -> 0xABCDF000

    sw    t2, 0(s1)             # SW  com deslocamento 0
    lw    t6, 0(s1)             # LW  com deslocamento 0
    beq   t6, t2, .L1
    beq   x0, x0, falha
.L1:
    sw    t3, 4(s1)             # SW  com deslocamento != 0  (pega ALUSrc)
    sw    t4, 8(s1)
    lw    a2, 4(s1)             # LW  com deslocamento != 0
    beq   a2, t3, .L2
    beq   x0, x0, falha
.L2:
    lw    a3, 8(s1)
    beq   a3, t4, .L3
    beq   x0, x0, falha
.L3:
    beq   t5, t4, falha         # BEQ nao tomado (t5 > t4)
    beq   t4, t5, falha         # BEQ nao tomado (t4 < t5)
    beq   t5, t5, .L4           # BEQ tomado (iguais)
    beq   x0, x0, falha
.L4:
    lui   a0, 0x1               # a0 != 0 => passou
passa:
    beq   x0, x0, passa
falha:
    add   a0, x0, x0
    beq   x0, x0, falha
