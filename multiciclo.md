# Estados:

0.  fetch
1.  decode/calculo endereco branch
2.  endereco ld/st
3.  memread
4.  memtoreg
5.  store
6.  R-type
7.  writeback
8.  condicional do branch
9.  OPP-IMM type
    Saída: 0x2A00 ou 0b010_1010_0000_0000
    - ALUop = 10
    - AluSrcA = 10
    - AluSrcB = 10
10. LUI -> imediato para reg
    Saída: 0x3800 ou 0b011_1000_0000_0000
    - ALUop = 11
    - ALUsrcB = 10

11. 
12. Colocar pc+4 em aluout
    Saída: 0x500  0b000_0101_0000_0000
    - ALUop = 00
    - ALUsrcB = 01
    - ALUsrcA = 01
13. Jump incondicional para endereço em resultante da soma rs1 + imm. link register
    Saída: 0xA82  0b000_1010_1000_0010
    - ALUop = 00
    - ALUsrcB = 10
    - ALUsrcA = 10
    - PCSource = 0
    - PCWrite = 1
    - RegWrite = 1
14. 
15. 

### LUI: (0x37)
rd = imm << 12

Fluxo:
> 0x0 -> 0x1 -> 0xA -> 0x7


### JALR: (0x67)
goto: rs1 + (imm & ~1)
rd = PC + 4
Fluxo:
> 0x0 -> 0x1 ->  0xC -> 0xD

### MUL: tipo r padrão

### SLTIU (0x13 - OPP-IMM)
rd=rs1 < imm
Fluxo:
> 0x0 -> 0x1 ->  0x9 -> 0x7
