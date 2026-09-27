# ==============================================================================
# demo_final.s -- programa de demonstracao para o relatorio.
#
# Exercita as 5 instrucoes novas (LUI, MUL, SLTIU, JALR, BGE) e as 7 originais
# (LW, SW, ADD, SUB, AND, OR, BEQ). Cada instrucao deixa um valor RECONHECIVEL
# num registrador s*, e cada resultado e' conferido por um BEQ: se qualquer um
# falhar, o programa desvia para 'falha' e a0 termina em 0.
#
#   a0 = 1  -> todas as 12 instrucoes produziram o resultado esperado
#   a0 = 0  -> alguma falhou
# ==============================================================================
.globl _start
_start:
    # ---- SLTIU ---------------------------------------------------- s0 = 1
    sltiu s0, x0, 1             # 0 <u 1  -> 1
    sltiu t0, x0, -1            # 0 <u 0xFFFFFFFF -> 1  (com sinal daria 0)
    beq   t0, s0, .c1
    beq   x0, x0, falha
.c1:
    # ---- LUI ------------------------------------------- s1 = 0xDEADB000
    lui   s1, 0xDEADB

    # ---- MUL ------------------------------------------- s2 = 0x0F000000
    lui   t1, 0x3               # t1 = 0x00003000
    lui   t2, 0x5               # t2 = 0x00005000
    mul   s2, t1, t2            # 0x3000 * 0x5000 = 0x0F000000
    lui   t3, 0xF000
    beq   s2, t3, .c2
    beq   x0, x0, falha
.c2:
    # ---- ADD / SUB / AND / OR (originais) --------------------------------
    add   s3, t1, t2            # s3 = 0x00008000
    sub   s4, t2, t1            # s4 = 0x00002000
    and   s5, t1, t2            # s5 = 0x00001000
    or    s6, t1, t2            # s6 = 0x00007000

    # ---- SW / LW (originais) --------------------------- s8 = 0xDEADB000
    lui   s7, 0x20              # s7 = 0x00020000  (base da memoria de dados)
    sw    s1, 0(s7)
    lw    s8, 0(s7)
    beq   s8, s1, .c3
    beq   x0, x0, falha
.c3:
    # ---- BGE (com sinal) -------------------------------------------------
    sub   t4, x0, t1            # t4 = -0x3000
    bge   t2, t1, .c4           # 0x5000 >= 0x3000  -> desvia
    beq   x0, x0, falha
.c4:
    bge   t4, t1, falha         # -0x3000 >= 0x3000 -> NAO desvia
    bge   t1, t4, .c5           # 0x3000 >= -0x3000 -> desvia
    beq   x0, x0, falha
.c5:
    # ---- BEQ (regressao: nao pode desviar com rs1 != rs2) ----------------
    beq   t2, t1, falha         # 0x5000 == 0x3000 ? NAO  (rs1 > rs2)
    beq   t1, t2, falha         # 0x3000 == 0x5000 ? NAO  (rs1 < rs2)

    # ---- JALR ------------------------------------------ s9 = 0xCAFE0000
    lui   t5, %hi(rotina)
    jalr  ra, %lo(rotina)(t5)   # chama; 'rotina' devolve via jalr x0, 0(ra)
    lui   t6, 0xCAFE0
    beq   s9, t6, .c6
    beq   x0, x0, falha
.c6:
    sltiu a0, x0, 1             # a0 = 1  -> TUDO CERTO
passa:
    beq   x0, x0, passa         # laco de parada (sucesso)

falha:
    add   a0, x0, x0            # a0 = 0  -> alguma instrucao falhou
    beq   x0, x0, falha         # laco de parada (falha)

rotina:
    lui   s9, 0xCAFE0
    jalr  x0, 0(ra)             # retorno
