# =============================================================================
# teste_monociclo.s -- testa TODAS as instrucoes do RISCV_Monociclo.circ
#
#   originais do circuito : LW  SW  ADD  SUB  AND  OR  BEQ
#   novas (grupo 8)       : JALR  BGE  LUI  MUL  SLTIU
#
# E' o mesmo programa de ../testes_multiciclo/teste_multiciclo.s (os dois circuitos
# executam uma instrucao por vez, entao os casos e os valores esperados sao iguais).
#
# Como ler o resultado
#   Cada caso grava UMA palavra na RAM de dados, em sequencia, a partir de 0x2000.
#   O valor esperado esta no comentario "=>" de cada linha GUARDA / DESVIO.
#   Desvios:  0x00001000 = desviou    0x00002000 = nao desviou
#   0x2000 tem que terminar em 0 (instrucoes logo depois de um JALR nao podem executar).
#   A ultima palavra (FIM) = 0x00002000 indica que o programa chegou ao laco "fim".
#
# Constantes so com LUI, ADD e SUB (nao ha ADDI).
# @assinatura 0x2000
# =============================================================================
    .option norelax
    .set SIG, 4                 # deslocamento da proxima palavra (0 = sombra do JALR)

    .macro GUARDA reg           # assinatura[SIG] <- reg
        sw   \reg, SIG(gp)
        .set SIG, SIG + 4
    .endm

    .macro SOMBRA               # instrucao que nunca pode executar (fica depois de um JALR)
        sw   s2, 0(gp)
    .endm

    # DESVIO instr, rs1, rs2 : assinatura <- 0x1000 se desviou, 0x2000 se nao
    .macro DESVIO instr, a, b
        \instr \a, \b, 1f
        sw   s3, SIG(gp)        # nao desviou
        beq  x0, x0, 2f
1:      sw   s2, SIG(gp)        # desviou
2:
        .set SIG, SIG + 4
    .endm

    .globl _start
_start:
    beq  x0, x0, inicio         # pula as sub-rotinas (ficam perto do endereco 0
                                # para o JALR com endereco absoluto em x0)

# ----------------------------------------------------------------------------
# Sub-rotinas dos testes de JALR
# ----------------------------------------------------------------------------
sub_a:                          # chamada com  jalr ra, sub_a(x0)
    GUARDA ra                   # [JALR] jalr ra,sub_a(x0): ra = pc+4 => 0x000002a0
    jalr x0, 13(ra)             # volta para ra+12 (13 impar: bit 0 tem que ser zerado)
    SOMBRA
    SOMBRA
    SOMBRA

caso_rr:                        # chamada com  jalr t5, caso_rr(x0)  (t5 = volta_rr)
    jalr t5, 0(t5)              # rd == rs1: pula para o t5 ANTIGO, grava t5 = caso_rr+4
    SOMBRA

caso_jj:                        # JALR cujo ponto de retorno e' outro JALR
    jalr ra, %lo(f_jj)(x0)      # chama f_jj ...
    jalr x0, 0(s9)              # ... que volta para ca; este jalr vai para depois_jj
    SOMBRA
f_jj:
    GUARDA s2                   # [JALR] jalr seguido de jalr: f_jj executou => 0x00001000
    jalr x0, 0(ra)
    SOMBRA

# ----------------------------------------------------------------------------
# Preparo das constantes
# ----------------------------------------------------------------------------
inicio:
    lui  gp, 0x2                # gp  = 0x00002000   (base da assinatura)
    lui  s2, 0x1                # s2  = 0x00001000   (marca "desviou")
    lui  s3, 0x2                # s3  = 0x00002000   (marca "nao desviou")
    lui  s4, 0x3                # s4  = 0x00003000
    lui  s5, 0xABC07            # s5  = 0xABC07000   (A)
    lui  s6, 0x00F07            # s6  = 0x00F07000   (B)
    lui  s8, 0x80000            # s8  = 0x80000000   (menor inteiro)
    lui  s11, 0x7               # s11 = 0x00007000
    lui  s0, 0x1                # s0  = 0x00001000   (x8, usado no teste de LUI)
    lui  t6, 0x00F07            # t6  = 0x00F07000   (x31, usado no teste de LUI)
    sub  s7, x0, s2             # s7  = 0xFFFFF000   (-0x1000)
    sub  s10, s8, s2            # s10 = 0x7FFFF000   (maior positivo aqui)

# ----------------------------------------------------------------------------
# LUI -- rd = imm20 << 12 (nao pode depender do registrador em inst[19:15])
# ----------------------------------------------------------------------------
    lui  t0, 0x80000            # inst[19:15] = x0
    lui  t1, 0x12345            # inst[19:15] = 8  (s0 = 0x1000)
    lui  t2, 0xFFFFF            # inst[19:15] = 31 (t6 = 0x00F07000)
    lui  t3, 0x00001            # inst[19:15] = x0
    GUARDA t0                   # [LUI] lui 0x80000 => 0x80000000
    GUARDA t1                   # [LUI] lui 0x12345 (campo rs1 -> s0) => 0x12345000
    GUARDA t2                   # [LUI] lui 0xFFFFF (campo rs1 -> t6) => 0xfffff000
    GUARDA t3                   # [LUI] lui 0x00001 => 0x00001000

# ----------------------------------------------------------------------------
# ADD / SUB / AND / OR  (originais)
# ----------------------------------------------------------------------------
    add  t0, s5, s6
    sub  t1, s5, s6
    and  t2, s5, s6
    or   t3, s5, s6
    sub  t4, s6, s5
    add  t5, s7, s2
    GUARDA t0                   # [ADD] 0xABC07000 + 0x00F07000 => 0xacb0e000
    GUARDA t1                   # [SUB] 0xABC07000 - 0x00F07000 => 0xaad00000
    GUARDA t2                   # [AND] 0xABC07000 & 0x00F07000 => 0x00c07000
    GUARDA t3                   # [OR]  0xABC07000 | 0x00F07000 => 0xabf07000
    GUARDA t4                   # [SUB] 0x00F07000 - 0xABC07000 => 0x55300000
    GUARDA t5                   # [ADD] -0x1000 + 0x1000 => 0x00000000
    add  t0, t0, t0
    GUARDA t0                   # [ADD] rd = rs1 = rs2: 0xACB0E000 * 2 => 0x5961c000

# ----------------------------------------------------------------------------
# MUL -- 32 bits baixos do produto (tem que diferir de ADD em todos os casos)
# ----------------------------------------------------------------------------
    mul  t0, s4, s2
    mul  t1, s7, s4
    mul  t2, s7, s7
    mul  t3, s5, s11
    mul  t4, s2, x0
    add  t5, s4, x0
    mul  t5, t5, t5
    GUARDA t0                   # [MUL] 0x3000 * 0x1000 => 0x03000000
    GUARDA t1                   # [MUL] -0x1000 * 0x3000 => 0xfd000000
    GUARDA t2                   # [MUL] -0x1000 * -0x1000 => 0x01000000
    GUARDA t3                   # [MUL] 0xABC07000 * 0x7000 (trunca) => 0x31000000
    GUARDA t4                   # [MUL] 0x1000 * 0 => 0x00000000
    GUARDA t5                   # [MUL] rd = rs1 = rs2: 0x3000 * 0x3000 => 0x09000000

# ----------------------------------------------------------------------------
# SLTIU -- imediato estendido COM sinal, comparacao SEM sinal
# ----------------------------------------------------------------------------
    sltiu t0, x0, 1
    sltiu t1, x0, 0
    sltiu t2, x0, -1
    sltiu t3, s7, 5
    sltiu t4, s2, -2048
    sltiu t5, s2, 2047
    sltiu a1, s7, -1
    add   a2, s7, x0
    sltiu a2, a2, -2048
    GUARDA t0                   # [SLTIU] 0 <u 1 => 0x00000001
    GUARDA t1                   # [SLTIU] 0 <u 0 => 0x00000000
    GUARDA t2                   # [SLTIU] 0 <u 0xFFFFFFFF (com sinal daria 0) => 0x00000001
    GUARDA t3                   # [SLTIU] 0xFFFFF000 <u 5 (com sinal daria 1) => 0x00000000
    GUARDA t4                   # [SLTIU] 0x1000 <u 0xFFFFF800 (com sinal daria 0) => 0x00000001
    GUARDA t5                   # [SLTIU] 0x1000 <u 0x7FF => 0x00000000
    GUARDA a1                   # [SLTIU] 0xFFFFF000 <u 0xFFFFFFFF => 0x00000001
    GUARDA a2                   # [SLTIU] rd = rs1: 0xFFFFF000 <u 0xFFFFF800 => 0x00000001

# ----------------------------------------------------------------------------
# SW / LW  (originais) -- base s2 = 0x1000, deslocamentos 0, +4, -4, +2044
# ----------------------------------------------------------------------------
    sw   s5, 0(s2)
    lw   t0, 0(s2)              # logo depois do SW no mesmo endereco
    sw   s6, 4(s2)
    sw   s7, -4(s2)
    sw   s8, 2044(s2)
    lw   t1, 4(s2)
    lw   t2, -4(s2)
    lw   t3, 2044(s2)
    lw   t4, 8(s2)
    add  t5, s2, x0
    lw   t5, 4(t5)              # rd = rs1
    GUARDA t0                   # [LW/SW] mem[0x1000] (LW logo apos o SW) => 0xabc07000
    GUARDA t1                   # [LW/SW] mem[0x1004] => 0x00f07000
    GUARDA t2                   # [LW/SW] mem[0x0FFC] (deslocamento negativo) => 0xfffff000
    GUARDA t3                   # [LW/SW] mem[0x17FC] (deslocamento 2044) => 0x80000000
    GUARDA t4                   # [LW/SW] mem[0x1008] nunca escrita => 0x00000000
    GUARDA t5                   # [LW/SW] lw t5,4(t5) (rd = rs1) => 0x00f07000

# ----------------------------------------------------------------------------
# BEQ  (original) -- nao pode desviar quando rs1 != rs2
# ----------------------------------------------------------------------------
    DESVIO beq, s2, s2          # [BEQ] 0x1000 == 0x1000 => desviou
    DESVIO beq, s2, s3          # [BEQ] 0x1000 == 0x2000 (rs1 < rs2) => nao desviou
    DESVIO beq, s3, s2          # [BEQ] 0x2000 == 0x1000 (rs1 > rs2) => nao desviou
    DESVIO beq, s7, s2          # [BEQ] -0x1000 == 0x1000 => nao desviou
    DESVIO beq, x0, x0          # [BEQ] 0 == 0 => desviou
    add  t2, x0, x0
laco_beq:                       # desvio para tras (imediato negativo)
    add  t2, t2, s2
    beq  t2, s2, laco_beq       # volta 1 vez (t2 = 0x1000), sai com t2 = 0x2000
    GUARDA t2                   # [BEQ] laco com desvio para tras => 0x00002000

# ----------------------------------------------------------------------------
# BGE -- comparacao COM sinal
# ----------------------------------------------------------------------------
    DESVIO bge, s3, s2          # [BGE] 0x2000 >= 0x1000 => desviou
    DESVIO bge, s2, s3          # [BGE] 0x1000 >= 0x2000 => nao desviou
    DESVIO bge, s2, s2          # [BGE] iguais => desviou
    DESVIO bge, s7, s2          # [BGE] -0x1000 >= 0x1000 (sem sinal desviaria) => nao desviou
    DESVIO bge, s2, s7          # [BGE] 0x1000 >= -0x1000 (sem sinal nao desviaria) => desviou
    DESVIO bge, s10, s8         # [BGE] 0x7FFFF000 >= 0x80000000 (overflow no rs1-rs2) => desviou
    DESVIO bge, s8, s10         # [BGE] 0x80000000 >= 0x7FFFF000 => nao desviou
    DESVIO bge, s7, s7          # [BGE] negativos iguais => desviou
    DESVIO bge, x0, s7          # [BGE] 0 >= -0x1000 => desviou
    add  t0, s4, x0             # t0 = 0x3000
    add  t1, x0, x0             # t1 = voltas * 0x1000
laco_bge:                       # desvio para tras (imediato negativo)
    add  t1, t1, s2
    sub  t0, t0, s2
    bge  t0, x0, laco_bge       # t0 = 0x2000, 0x1000, 0, -0x1000 -> 4 voltas
    GUARDA t1                   # [BGE] laco com desvio para tras (4 voltas) => 0x00004000

# ----------------------------------------------------------------------------
# JALR
# ----------------------------------------------------------------------------
    beq  x0, x0, chama_a        # pula sub_b (ela fica aqui para o -24 abaixo ser fixo)
sub_b:                          # chamada com  jalr t6, -24(ra)   (ra = link_a = sub_b+24)
    GUARDA t6                   # [JALR] jalr t6,-24(ra): t6 = pc+4 => 0x000002b4
    jalr x0, 0(t6)              # volta para o link
    SOMBRA
    SOMBRA
    SOMBRA
chama_a:
    jalr ra, %lo(sub_a)(x0)     # rs1 = x0, imediato = endereco absoluto de sub_a
link_a:
    SOMBRA                      # nunca executam: sub_a volta direto para ret_a = ra + 12
    SOMBRA
    SOMBRA
ret_a:
    GUARDA s2                   # [JALR] voltou de sub_a em ra+12 (bit 0 zerado) => 0x00001000
    jalr t6, -24(ra)            # rs1 = ra, imediato NEGATIVO (link_a-24 = sub_b), rd = t6
    GUARDA s3                   # [JALR] voltou de sub_b (retorno em t6) => 0x00002000
    jalr t5, %lo(caso_rr)(x0)   # t5 = volta_rr
volta_rr:
    GUARDA t5                   # [JALR] jalr t5,0(t5) (rd = rs1): t5 = pc+4 => 0x0000001c
    jalr s9, %lo(caso_jj)(x0)   # s9 = endereco de depois_jj
depois_jj:
    GUARDA ra                   # [JALR] ra escrito pela chamada de f_jj => 0x00000024

# ----------------------------------------------------------------------------
# Fim
# ----------------------------------------------------------------------------
    GUARDA s3                   # [FIM] programa chegou ao fim => 0x00002000
fim:
    beq  x0, x0, fim
