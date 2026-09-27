# Testes do RISC-V Multiciclo (`../RISCV_Multiciclo.circ`)

Estes testes rodam os programas no circuito **sem abrir o Logisim** e comparam o resultado
com um modelo RV32IM de referência. É o mesmo modelo de `../testes_pipeline/testar.py`,
rodando aqui com memória única.

## Como rodar

```bash
./testar.py                          # bateria: teste_multiciclo.s + todos os testes do monociclo
./testar.py teste_multiciclo.s       # um programa só, com a assinatura caso a caso
./testar.py prog.s --traco           # mostra estado da FSM / PC / escritas ciclo a ciclo
./testar.py --circ OUTRO.circ        # outro arquivo de circuito
```

Para cada programa, o script compara com o modelo três coisas:

- a sequência de instruções buscadas (o PC em cada estado 0);
- cada escrita no banco de registradores;
- cada escrita na memória.

Qualquer diferença conta como falha.

A bateria roda o `teste_multiciclo.s` e os programas de `../testes/` (`t1`…`t9` e
`exhaustive_instruction`). Esses programas foram feitos para o monociclo, mas são
sequenciais e gravam dados a partir de `0x1000`, então servem sem mudança para a memória
única do multiciclo.

### Na GUI do Logisim

1. Carregue `teste_multiciclo.mem` na RAM (430,310) com botão direito → *Load Image*.
2. Deixe `RESET = 0` e dê uns **610 ciclos** de clock.
3. A memória é **única** (instruções + dados), então a assinatura fica a partir do
   endereço `0x2000`. A RAM é endereçada por palavra: procure a partir da palavra **`0x800`**.

## O que o `teste_multiciclo.s` cobre

As 12 instruções, com os mesmos casos do teste do pipeline:

- LUI com o campo `inst[19:15]` apontando para registrador não nulo;
- MUL com negativos e com truncamento;
- SLTIU nos casos em que com sinal e sem sinal dão resultados diferentes;
- BGE com overflow na subtração;
- JALR com `rs1 = x0`, imediato negativo, deslocamento ímpar e JALR seguido de JALR.

Além disso, casos que fazem sentido num multiciclo:

- **`rd == rs1`** em ADD, MUL, SLTIU, LW e JALR (`jalr t5, 0(t5)`). O registrador de
  destino é escrito no mesmo ciclo em que o operando antigo ainda precisa valer;
- **desvio para trás** (imediato negativo) em BEQ e BGE, em laços;
- **LW logo depois de SW** no mesmo endereço.

Não há NOPs: o multiciclo executa uma instrução por vez.

## Resultado em `RISCV_Multiciclo.circ` (2026-09-27)

| programa | resultado |
|---|---|
| `teste_multiciclo` (57 casos) | ✅ tudo igual ao modelo (157 instruções, 605 ciclos) |
| `t1_originais` … `t7_bge`, `t9_x0` | ✅ |
| `exhaustive_instruction` | ✅ termina em `test_pass` (a0 = 1) |
| `t8_addi` | nota: igual ao monociclo, `addi` com `imm[11:5] ≠ 0` vira MUL/AND. ADDI não é instrução do grupo; esse programa só documenta isso |

**Todas as 12 instruções funcionam no multiciclo.** A análise do netlist confirma os
caminhos:

- FSM: LUI 0→1→10→7, JALR 0→1→12→13, OP-IMM 0→1→9→7.
- ALU: 3 = MUL, 4 = SLTU, 14 = `A <s B` (usado pelo BGE via `Zero`), 15 = passa B.
- `postALU` zera o bit 0 só quando o opcode é JALR.

### O teste pega erro?

Para conferir, injetei 3 defeitos numa cópia do circuito e rodei o teste em cada uma:

| defeito injetado | o teste acusou |
|---|---|
| SLTIU comparando com sinal (`ALU_Control`: código 4 → 14) | SLTIU: falham os 3 casos com sinal ≠ sem sinal |
| LUI com ALUop = 10 em vez de 11 (FSM, estado 10) | LUI e, em cascata, tudo que usa constantes |
| JALR sem zerar o bit 0 (`postALU`) | JALR: o retorno com deslocamento ímpar (`13(ra)`) |

## Assinatura esperada

`0x00001000` = desviou, `0x00002000` = não desviou.

| palavra na RAM | endereço | esperado | caso |
|---|---|---|---|
| 0x800 | 0x2000 | `00000000` | [JALR] instrucoes logo depois de um JALR nao podem executar (tem que ficar 0) |
| 0x801 | 0x2004 | `000002a0` | [JALR] jalr ra,sub_a(x0): ra = pc+4 |
| 0x802 | 0x2008 | `00001000` | [JALR] jalr seguido de jalr: f_jj executou |
| 0x803 | 0x200c | `80000000` | [LUI] lui 0x80000 |
| 0x804 | 0x2010 | `12345000` | [LUI] lui 0x12345 (campo rs1 -> s0) |
| 0x805 | 0x2014 | `fffff000` | [LUI] lui 0xFFFFF (campo rs1 -> t6) |
| 0x806 | 0x2018 | `00001000` | [LUI] lui 0x00001 |
| 0x807 | 0x201c | `acb0e000` | [ADD] 0xABC07000 + 0x00F07000 |
| 0x808 | 0x2020 | `aad00000` | [SUB] 0xABC07000 - 0x00F07000 |
| 0x809 | 0x2024 | `00c07000` | [AND] 0xABC07000 & 0x00F07000 |
| 0x80a | 0x2028 | `abf07000` | [OR]  0xABC07000 \| 0x00F07000 |
| 0x80b | 0x202c | `55300000` | [SUB] 0x00F07000 - 0xABC07000 |
| 0x80c | 0x2030 | `00000000` | [ADD] -0x1000 + 0x1000 |
| 0x80d | 0x2034 | `5961c000` | [ADD] rd = rs1 = rs2: 0xACB0E000 * 2 |
| 0x80e | 0x2038 | `03000000` | [MUL] 0x3000 * 0x1000 |
| 0x80f | 0x203c | `fd000000` | [MUL] -0x1000 * 0x3000 |
| 0x810 | 0x2040 | `01000000` | [MUL] -0x1000 * -0x1000 |
| 0x811 | 0x2044 | `31000000` | [MUL] 0xABC07000 * 0x7000 (trunca) |
| 0x812 | 0x2048 | `00000000` | [MUL] 0x1000 * 0 |
| 0x813 | 0x204c | `09000000` | [MUL] rd = rs1 = rs2: 0x3000 * 0x3000 |
| 0x814 | 0x2050 | `00000001` | [SLTIU] 0 <u 1 |
| 0x815 | 0x2054 | `00000000` | [SLTIU] 0 <u 0 |
| 0x816 | 0x2058 | `00000001` | [SLTIU] 0 <u 0xFFFFFFFF (com sinal daria 0) |
| 0x817 | 0x205c | `00000000` | [SLTIU] 0xFFFFF000 <u 5 (com sinal daria 1) |
| 0x818 | 0x2060 | `00000001` | [SLTIU] 0x1000 <u 0xFFFFF800 (com sinal daria 0) |
| 0x819 | 0x2064 | `00000000` | [SLTIU] 0x1000 <u 0x7FF |
| 0x81a | 0x2068 | `00000001` | [SLTIU] 0xFFFFF000 <u 0xFFFFFFFF |
| 0x81b | 0x206c | `00000001` | [SLTIU] rd = rs1: 0xFFFFF000 <u 0xFFFFF800 |
| 0x81c | 0x2070 | `abc07000` | [LW/SW] mem[0x1000] (LW logo apos o SW) |
| 0x81d | 0x2074 | `00f07000` | [LW/SW] mem[0x1004] |
| 0x81e | 0x2078 | `fffff000` | [LW/SW] mem[0x0FFC] (deslocamento negativo) |
| 0x81f | 0x207c | `80000000` | [LW/SW] mem[0x17FC] (deslocamento 2044) |
| 0x820 | 0x2080 | `00000000` | [LW/SW] mem[0x1008] nunca escrita |
| 0x821 | 0x2084 | `00f07000` | [LW/SW] lw t5,4(t5) (rd = rs1) |
| 0x822 | 0x2088 | `00001000` | [BEQ] 0x1000 == 0x1000 |
| 0x823 | 0x208c | `00002000` | [BEQ] 0x1000 == 0x2000 (rs1 < rs2) |
| 0x824 | 0x2090 | `00002000` | [BEQ] 0x2000 == 0x1000 (rs1 > rs2) |
| 0x825 | 0x2094 | `00002000` | [BEQ] -0x1000 == 0x1000 |
| 0x826 | 0x2098 | `00001000` | [BEQ] 0 == 0 |
| 0x827 | 0x209c | `00002000` | [BEQ] laco com desvio para tras |
| 0x828 | 0x20a0 | `00001000` | [BGE] 0x2000 >= 0x1000 |
| 0x829 | 0x20a4 | `00002000` | [BGE] 0x1000 >= 0x2000 |
| 0x82a | 0x20a8 | `00001000` | [BGE] iguais |
| 0x82b | 0x20ac | `00002000` | [BGE] -0x1000 >= 0x1000 (sem sinal desviaria) |
| 0x82c | 0x20b0 | `00001000` | [BGE] 0x1000 >= -0x1000 (sem sinal nao desviaria) |
| 0x82d | 0x20b4 | `00001000` | [BGE] 0x7FFFF000 >= 0x80000000 (overflow no rs1-rs2) |
| 0x82e | 0x20b8 | `00002000` | [BGE] 0x80000000 >= 0x7FFFF000 |
| 0x82f | 0x20bc | `00001000` | [BGE] negativos iguais |
| 0x830 | 0x20c0 | `00001000` | [BGE] 0 >= -0x1000 |
| 0x831 | 0x20c4 | `00004000` | [BGE] laco com desvio para tras (4 voltas) |
| 0x832 | 0x20c8 | `000002b4` | [JALR] jalr t6,-24(ra): t6 = pc+4 |
| 0x833 | 0x20cc | `00001000` | [JALR] voltou de sub_a em ra+12 (bit 0 zerado) |
| 0x834 | 0x20d0 | `00002000` | [JALR] voltou de sub_b (retorno em t6) |
| 0x835 | 0x20d4 | `0000001c` | [JALR] jalr t5,0(t5) (rd = rs1): t5 = pc+4 |
| 0x836 | 0x20d8 | `00000024` | [JALR] ra escrito pela chamada de f_jj |
| 0x837 | 0x20dc | `00002000` | [FIM] programa chegou ao fim |

## Arquivos

| arquivo | o que é |
|---|---|
| `teste_multiciclo.s` / `.mem` | o programa de teste (fonte comentada / imagem para *Load Image*) |
| `testar.py` | roda o modelo e o circuito e compara (bateria inteira ou um programa) |
| `MultiSim.java` | harness: carrega o `.circ` com o jar do Logisim original, carrega o programa na RAM e dá clock |
