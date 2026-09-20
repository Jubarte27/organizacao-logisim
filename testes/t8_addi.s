# ADDI nao e' instrucao do grupo nem do circuito original, mas o opcode
# OP-IMM (0x13) foi habilitado na ROM de controle por causa do SLTIU.
# Este teste mostra o que acontece com ADDI.
.globl _start
_start:
    lui   t0, 0x1
    addi  t1, t0, 1             # imm pequeno: imm[11:5] = 0  -> funct7 = 0
    addi  t2, t0, 32            # imm = 32   : imm[11:5] = 1  -> parece funct7 de MUL
    addi  t3, t0, -1            # imm = -1   : imm[11:5] = 0x7F
    beq   x0, x0, halt
halt:
    beq   x0, x0, halt
