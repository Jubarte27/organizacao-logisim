# ERRO 3 -- BEQ virou BGE.
# Com o bug, "desvia = Branch AND (Zero OR NOT Less)", entao todo BEQ
# com rs1 >= rs2 desvia, mesmo sem serem iguais.
.globl _start
_start:
    lui   t0, 0x2               # t0 = 0x2000
    lui   t1, 0x1               # t1 = 0x1000
    sub   t2, x0, t1            # t2 = 0xFFFFF000  (negativo)

    beq   t0, t1, erro          # CASO A: 0x2000 == 0x1000 ? NAO. (rs1 > rs2)
    beq   t1, t0, erro          # CASO B: 0x1000 == 0x2000 ? NAO. (rs1 < rs2)
    beq   t0, t2, erro          # CASO C: positivo == negativo ? NAO. (rs1 > rs2)
    beq   t2, t0, erro          # CASO D: negativo == positivo ? NAO. (rs1 < rs2)
    beq   t0, t0, .L1           # CASO E: iguais -> TEM de desviar
    beq   x0, x0, erro
.L1:
    lui   a0, 0x1
passa:
    beq   x0, x0, passa
erro:
    add   a0, x0, x0
falha:
    beq   x0, x0, falha
