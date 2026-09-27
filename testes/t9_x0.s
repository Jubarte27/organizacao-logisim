# x0 tem de ser sempre 0, mesmo depois de uma instrucao tentar escrever nele.
.globl _start
_start:
    lui   s1, 0x5               # s1 = 0x00005000
    add   x0, s1, s1            # tenta gravar 0xA000 em x0
    sltiu a0, x0, 1             # a0 = 1 se x0 == 0
    beq   x0, s1, erro          # x0 == 0x5000 ? se sim, leitura de x0 quebrada
    add   s2, x0, s1            # s2 deve ser 0x5000 (x0 contribui com 0)
    beq   s2, s1, halt
erro:
    add   a0, x0, x0
halt:
    beq   x0, x0, halt
