# Testes do RISC-V Monociclo

Estes testes rodam os programas no `.circ` **sem abrir o Logisim** e comparam com um modelo
RV32IM de referência. A rigorosidade é a mesma dos testes do multiciclo
(`../testes_multiciclo`) e do pipeline (`../testes_pipeline`).

## Como rodar

```bash
./testar.py                          # bateria: teste_monociclo.s + t1..t9 + exhaustive_instruction
./testar.py teste_monociclo.s        # um programa só, com a assinatura caso a caso
./testar.py t2_beq.mem --traco       # mostra PC / instrução / escritas ciclo a ciclo
./testar.py --circ OUTRO.circ        # outro arquivo de circuito
```

Para cada programa, o `testar.py` compara com o modelo três coisas:

- o **PC a cada ciclo** (a sequência de instruções executadas);
- **cada escrita no banco de registradores**, na ordem;
- **cada escrita na memória de dados**, na ordem.

Qualquer diferença conta como falha, mesmo que o programa termine com o `a0` certo.

O `testar.sh` antigo continua aqui, mas só compara o caminho do PC.

### Na GUI do Logisim

1. Carregue `teste_monociclo.mem` na ROM de instruções (310,360) com botão direito → *Load Image*.
2. Deixe `Reset = 0` e dê uns **160 ciclos** de clock.
3. Confira a RAM de dados (890,360) a partir do endereço `0x2000`, que é a palavra **`0x800`**.

## O teste completo: `teste_monociclo.s`

É o **mesmo programa** do multiciclo (`../testes_multiciclo/teste_multiciclo.s`). Os dois
circuitos executam uma instrução por vez, então os casos e os valores esperados são idênticos.

São 57 casos, cobrindo as 12 instruções:

- LUI com o campo `inst[19:15]` apontando para registrador não nulo;
- MUL com negativos e com truncamento;
- SLTIU nos casos em que com sinal e sem sinal diferem;
- BGE com overflow em `rs1 - rs2`;
- **`rd == rs1`** em ADD, MUL, SLTIU, LW e JALR;
- **desvio para trás** em BEQ e BGE;
- LW logo depois de SW;
- JALR com `rs1 = x0`, imediato negativo, deslocamento ímpar e JALR seguido de JALR.

## Resultado em `RISCV_Monociclo.circ` (2026-09-27)

| programa | resultado |
|---|---|
| `teste_monociclo` (57 casos) | ✅ 157 instruções, 65 escritas no banco e 59 na memória: todas iguais ao modelo |
| `t1_originais` … `t7_bge`, `t9_x0` | ✅ |
| `exhaustive_instruction` | ✅ termina em `test_pass` (a0 = 1) |
| `t8_addi` | nota: limitação conhecida do ADDI (abaixo); não é instrução do grupo |

**Todas as 12 instruções funcionam no monociclo.**

### O teste pega erro?

Para conferir, reinjetei numa cópia do circuito os 3 erros que o monociclo já teve, mais um:

| defeito injetado | `teste_monociclo` acusou | outros programas que acusaram |
|---|---|---|
| LW com a palavra de controle `6` em vez de `c6` (erro real nº 1) | LW/SW: 6 de 6 | `t1`, `exhaustive` |
| SLTIU comparando com sinal (erro real nº 2) | SLTIU: os 3 casos com sinal ≠ sem sinal | `t3`, `exhaustive` |
| BEQ se comportando como BGE (erro real nº 3) | BEQ: os 2 casos `rs1 > rs2` (e, em cascata, o resto) | `t1`, `t2`. O `exhaustive` **não** pega |
| JALR sem zerar o bit 0 | JALR: o retorno com deslocamento ímpar | `exhaustive` |

### Detalhe do harness

O `MonoSim.java` grava o programa **direto no conteúdo da ROM**, depois de limpá-la.
O `Rom.loadImage` da API do Logisim 2.7.1 deixava a ROM inteira zerada para programas
curtos (`t8`, `t9`). O caminho do PC do `MonoSim` foi conferido contra o `run.py` antigo, que
edita o XML: é igual nos 11 programas.

## Arquivos

| arquivo | o que é |
|---|---|
| `testar.py` | **teste rigoroso**: modelo de referência × circuito (PC, escritas no banco, escritas na memória, assinatura) |
| `MonoSim.java` | harness do `testar.py`: grava o programa na ROM, dá clock e registra cada escrita |
| `teste_monociclo.s` / `.mem` | o teste completo (57 casos, as 12 instruções) |
| `Sim.java` | harness antigo (só PC e registradores no fim), usado pelo `run.py` |
| `run.py` | troca a ROM de instruções pelo `.mem` dado e chama o harness |
| `ref.py` | modelo RV32IM de referência (gera o traço esperado) |
| `asm.sh` | monta um `.s` para o formato `v2.0 raw` do Logisim |
| `testar.sh` | bateria antiga: compara só o caminho do PC |
| `corrigir.py` | aplica as 3 correções em um `.circ` e grava a versão corrigida |
| `RISCV_Monociclo_corrigido.circ` | resultado de `corrigir.py` — referência para conferir |
| `mem_controle_monociclo_corrigido` | ROM de controle já com `c6` no endereço 0x03 |

## Testes

| teste | cobre |
|---|---|
| `t1_originais` | LW, SW (com e sem deslocamento), ADD, SUB, AND, OR, BEQ — **regressão** |
| `t2_beq` | BEQ não pode desviar quando `rs1 > rs2` nem quando `rs1 < rs2` |
| `t3_sltiu` | SLTIU com `0xFFFFFFFF`, `-1` e `0x80000000` (comparação **sem** sinal) |
| `t4_lui` | LUI |
| `t5_mul` | MUL, inclusive negativos e truncamento em 32 bits |
| `t6_jalr` | JALR (desvio, `ra = PC+4`, alinhamento) |
| `t7_bge` | BGE com positivos, negativos e iguais (comparação **com** sinal) |
| `t8_addi` | ADDI — só documenta a limitação conhecida; **não segue a convenção do `a0`**, olhe `x6`/`x7`/`x28` na tabela de registradores |
| `../exhaustive_instruction.mem` | o teste grande que já existia |
| `teste_monociclo` | o teste completo (57 casos); tabela da assinatura no fim deste arquivo |

## Limitação conhecida: ADDI

O opcode OP-IMM (`0x13`) foi habilitado na ROM de controle por causa do SLTIU.
Isso faz o `addi` *quase* funcionar, mas com `funct3 = 0` o `ALU_Control` escolhe
entre ADD/SUB/MUL olhando `funct7`, que num I-type é `imm[11:5]`. Então:

- `addi t1, t0, 1`   → certo (`imm[11:5] = 0`)
- `addi t2, t0, 32`  → vira **MUL** (`imm[11:5] = 1`)
- `addi t3, t0, -1`  → vira **AND** (`imm[11:5] = 0x7F`)

Não é regressão: o circuito original não tinha OP-IMM nenhum, e ADDI não é
instrução do grupo 8. Se quiser fechar isso: ligar `ALUSrc` como entrada nova do
`ALU_Control` e usar `NOT ALUSrc` para zerar os dois flags de `funct7`
(com `ALUOp = 10`, `ALUSrc = 1` só acontece em OP-IMM).

## Assinatura esperada do `teste_monociclo`

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
