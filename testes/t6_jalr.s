# JALR -- instrucao nova do grupo (desvio + ra = PC+4 + mascara do bit 0).
.globl _start
_start:
    lui   s0, %hi(rotina)
    jalr  ra, %lo(rotina)(s0)   # chamada 1
    lui   t3, 0x7               # <- ponto de retorno
    beq   t1, t3, .L1           # rotina fez t1 = 0x7000 ?
    beq   x0, x0, falha
.L1:
    lui   s1, 0x1
    add   s2, s0, s1            # base com bit 12 setado, endereco continua alinhado
    sub   s2, s2, s1
    jalr  ra, %lo(rotina)(s2)   # chamada 2, mesmo alvo
    beq   t1, t3, .L2
    beq   x0, x0, falha
.L2:
    lui   a0, 0x1
passa:
    beq   x0, x0, passa
falha:
    add   a0, x0, x0
    beq   x0, x0, falha

rotina:
    lui   t1, 0x7
    jalr  x0, 0(ra)             # retorno
