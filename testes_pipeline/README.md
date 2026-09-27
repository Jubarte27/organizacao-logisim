# Testes do RISC-V Pipeline (`../RISCV_Pipeline.circ`)

Roda o programa no circuito **sem abrir o Logisim** e compara com um modelo RV32IM de
referência. Um único programa (`teste_pipeline.s`) usa as 12 instruções:

- originais: `LW SW ADD SUB AND OR BEQ`
- grupo 8: `JALR BGE LUI MUL SLTIU`

## Como rodar

```bash
./testar.py                          # teste_pipeline.s em ../RISCV_Pipeline.circ
./testar.py --circ OUTRO.circ        # outro arquivo de circuito
./testar.py meu.s --traco            # outro programa, mostrando PC / IF/ID / WB / MEM ciclo a ciclo
```

O script faz quatro coisas:

1. monta o `.s` com `../testes/asm.sh`;
2. roda o modelo de referência;
3. confere se o programa respeita as regras do pipeline (abaixo). Se respeitar, o
   resultado no circuito **tem** que ser igual ao do modelo;
4. roda o circuito (`PipeSim.java`) e compara, nesta ordem:
   - toda escrita no banco (WB);
   - toda escrita na memória (MEM);
   - a assinatura, caso a caso.

### Na GUI do Logisim

1. Carregue `teste_pipeline.mem` na RAM de instruções (240,550), com botão direito → *Load Image*.
2. Deixe `Reset = 0` e dê uns **240 ciclos** de clock.
3. Confira a RAM de dados (960,560) contra a tabela abaixo. A RAM é endereçada por
   **palavra**, então a coluna "palavra" é o que aparece nela.

## Regras do pipeline (herdadas do circuito original do professor)

Todas foram medidas em simulação e conferidas no netlist do original:

- **Sem forwarding e sem detecção de hazard.** O banco grava na mesma borda em que o ID/EX
  captura os operandos. Quem lê um registrador tem que estar **pelo menos 4 instruções
  depois** de quem escreve (3 `nop` no meio).
- **BEQ/BGE resolvem no estágio MEM.** O original não tem flush para desvio, então as
  **3 instruções seguintes sempre executam** (delay slots). No teste elas são sempre `nop`.
- **JALR**: a implementação do grupo faz flush das 3 instruções seguintes (`flush = Reset OR isJALR(EX/MEM)`).

O `testar.py` verifica as duas primeiras regras no traço dinâmico antes de rodar o circuito.

## Estado atual (2026-09-27): ✅ todas as 12 instruções passam

Depois das 5 correções abaixo, aplicadas no `RISCV_Pipeline.circ`:

- 42/42 escritas no banco e 52/52 escritas na memória iguais ao modelo;
- 49/49 casos da assinatura.

As seções seguintes registram o que estava errado e como foi corrigido.

## Problemas encontrados em 2026-09-26 (todos corrigidos em 2026-09-27)

| instrução | estado em 26/09 (antes das correções) | casos |
|---|---|---|
| LW, SW | ✅ | 5/5 (deslocamento 0, +4, −4, +2044) |
| ADD, SUB, AND | ✅ | 5/5 |
| **OR** (original) | ❌ **regressão** | 0/1 |
| BEQ | ✅ | 5/5 (inclusive `rs1 > rs2` e `rs1 < rs2`, que não podem desviar) |
| BGE | ✅ | 9/9 (inclusive negativos e `0x7FFFF000 >= 0x80000000`) |
| **LUI** | ❌ | 2/4 (só acerta quando `inst[19:15]` aponta para um registrador que vale 0) |
| **MUL** | ❌ | 0/5 (calcula ADD) |
| **SLTIU** | ❌ | 3/7 (calcula AND; só "acerta" quando o AND dá o mesmo valor) |
| **JALR** | ⚠️ | 6/7: endereço, `rd = pc+4`, imediato negativo, zerar o bit 0 e o flush estão certos. Falha quando a instrução logo depois de um JALR é outro JALR |

### 1. OR: constante apagada no `ALU_Control` (regressão)

Circuito `ALU_Control`, mux **(530,370)**, que tem `select = (funct3 == 6)`. No original,
a entrada 1 **(500,380)** recebia a `Constant` 4 bits `0x1` (código do OR), que estava em
(490,380). Essa constante foi apagada e a entrada ficou solta. Durante o OR o código da
ALU fica `xxxx` e o valor gravado é lixo: no teste saiu igual ao resultado da instrução
anterior.

**Correção:** `Constant` 4 bits `0x1` na entrada 1 do mux (500,380).

### 2. MUL: mux selecionado pelo bit errado do `funct7`

Circuito `ALU_Control`, mux **(480,520)** (0 = ADD/SUB, 1 = constante `8` = MUL). O select
**(460,540)** está ligado na saída **de baixo** do splitter do `funct7` **(310,500)**, que é
o `funct7[6]`. O MUL tem `funct7 = 0000001`, então precisa do `funct7[0]`, que é a saída
**de cima** (330,430). Do jeito que está, o MUL sempre cai em ADD. O ALU_Control manda
`0010`; `0x3000 * 0x1000` vira `0x4000`.

**Correção:** levar o select do mux (480,520) para a saída de cima do splitter. A alternativa
sem mexer em fio, que foi a validada: no splitter (310,500), atributo `Bit 0` = 6 e `Bit 6` = 0.

### 3. SLTIU: não chega na ALU e o `ALU_Control` manda para AND

Dois problemas, os dois precisam ser corrigidos.

- **ALU:** o `Comparator` **sem sinal** (190,500) → `Bit Extender` (410,510). A **saída
  do Bit Extender está solta**; não vai para nenhuma entrada do mux de resultado (370,220).
- **ALU_Control:** com `ALUOp = 10` e `funct3 = 3`, o caminho cai na constante `0`
  **(420,310)**, o "senão" do mux (470,320), e sai o código 0 = **AND**.
  `0x1000 <u 0xFFFFF800` vira `0x1000 & 0xFFFFF800 = 0x1000`.

**Correção validada:**

1. `ALU`: ligar a saída do Bit Extender (410,510) na **entrada 3** do mux de resultado
   (330,170), por túnel. É a entrada livre usada aqui.
2. `ALU_Control`: trocar a constante `0` de (420,310) por um mux de 4 bits com
   `select = (funct3 == 3)` (`Comparator` 3 bits contra `Constant 3`), entrada 0 = `0`
   (AND, `funct3 = 7`) e entrada 1 = `3` (SLTIU).

### 4. LUI: soma o registrador apontado por `inst[19:15]`

A ROM de controle tem `0x37 → 0x84` (ALUOp = 00, ALUSrc = 1), então a ALU faz
**`rs1 + imm`**. Só que o campo `rs1` do LUI (`inst[19:15]`) é parte do imediato de
20 bits:

- `lui t1, 0x12345` lê `x8`;
- `lui t2, 0xFFFFF` lê `x31`.

O resultado só sai certo se esse registrador valer 0.

**Correção validada**, a mesma ideia do monociclo ("passa B"):

1. `ALU`: ligar o operando B (pino (90,240)) na **entrada 15** do mux de resultado (330,290).
2. `ALU_Control`: constante **(610,220)**, que é a entrada do `ALUOp = 11` no mux (690,210):
   `0x0` → **`0xF`**.
3. `Control`, ROM (330,70): endereço `0x37`: `84` → **`87`** (ALUOp = 11).

### 5. JALR: o flush não zera o `isJALR` do ID/EX

`flush` limpa o IF/ID e o registrador de controle do ID/EX (500,130), mas **não** o
registrador `isJALR` do ID/EX **(500,370)**, cujo CLR está no Reset.

Se a instrução logo depois de um JALR também é um JALR, esse `isJALR = 1` chega ao EX/MEM.
Isso acontece, por exemplo, numa chamada cujo ponto de retorno é um `ret`. O resultado:

- o PC é desviado de novo;
- um novo flush mata a primeira instrução da função chamada;
- a função não executa.

No teste é o caso da palavra 2. `f_jj` nunca roda e o programa segue direto para `depois_jj`.

**Correção validada:** a entrada do `isJALR` do EX/MEM **(710,370)** passa a receber
`isJALR(ID/EX) AND NOT flush`, em vez do fio direto de (500,370).

### Validação das correções

Antes de irem para o circuito, as 5 correções foram validadas numa cópia do `.circ`.
Com elas o teste passa inteiro:

- 42/42 escritas no banco e 52/52 na memória iguais ao modelo;
- 49/49 casos da assinatura.

Aplicando uma correção por vez, cada uma conserta só a sua instrução.

## Assinatura esperada

`0x00001000` = desviou, `0x00002000` = não desviou.

| palavra | endereço | esperado | caso |
|---|---|---|---|
| 0 | 0x000 | `00000000` | [JALR] instrucoes logo depois de um JALR (tem que ficar 0: flush) |
| 1 | 0x004 | `00000400` | [JALR] jalr ra,sub_a(x0): ra = pc+4 |
| 2 | 0x008 | `00001000` | [JALR] jalr seguido de jalr: f_jj executou |
| 3 | 0x00c | `80000000` | [LUI] lui 0x80000 |
| 4 | 0x010 | `12345000` | [LUI] lui 0x12345 (campo rs1 -> s0) |
| 5 | 0x014 | `fffff000` | [LUI] lui 0xFFFFF (campo rs1 -> t6) |
| 6 | 0x018 | `00001000` | [LUI] lui 0x00001 |
| 7 | 0x01c | `acb0e000` | [ADD] 0xABC07000 + 0x00F07000 |
| 8 | 0x020 | `aad00000` | [SUB] 0xABC07000 - 0x00F07000 |
| 9 | 0x024 | `00c07000` | [AND] 0xABC07000 & 0x00F07000 |
| 10 | 0x028 | `abf07000` | [OR]  0xABC07000 \| 0x00F07000 |
| 11 | 0x02c | `55300000` | [SUB] 0x00F07000 - 0xABC07000 |
| 12 | 0x030 | `00000000` | [ADD] -0x1000 + 0x1000 |
| 13 | 0x034 | `03000000` | [MUL] 0x3000 * 0x1000 |
| 14 | 0x038 | `fd000000` | [MUL] -0x1000 * 0x3000 |
| 15 | 0x03c | `01000000` | [MUL] -0x1000 * -0x1000 |
| 16 | 0x040 | `31000000` | [MUL] 0xABC07000 * 0x7000 (trunca) |
| 17 | 0x044 | `00000000` | [MUL] 0x1000 * 0 |
| 18 | 0x048 | `00000001` | [SLTIU] 0 <u 1 |
| 19 | 0x04c | `00000000` | [SLTIU] 0 <u 0 |
| 20 | 0x050 | `00000001` | [SLTIU] 0 <u 0xFFFFFFFF (com sinal daria 0) |
| 21 | 0x054 | `00000000` | [SLTIU] 0xFFFFF000 <u 5 (com sinal daria 1) |
| 22 | 0x058 | `00000001` | [SLTIU] 0x1000 <u 0xFFFFF800 (com sinal daria 0) |
| 23 | 0x05c | `00000000` | [SLTIU] 0x1000 <u 0x7FF |
| 24 | 0x060 | `00000001` | [SLTIU] 0xFFFFF000 <u 0xFFFFFFFF |
| 25 | 0x064 | `abc07000` | [LW/SW] mem[0x1000] |
| 26 | 0x068 | `00f07000` | [LW/SW] mem[0x1004] |
| 27 | 0x06c | `fffff000` | [LW/SW] mem[0x0FFC] (deslocamento negativo) |
| 28 | 0x070 | `80000000` | [LW/SW] mem[0x17FC] (deslocamento 2044) |
| 29 | 0x074 | `00000000` | [LW/SW] mem[0x1008] nunca escrita |
| 30 | 0x078 | `00001000` | [BEQ] 0x1000 == 0x1000 |
| 31 | 0x07c | `00002000` | [BEQ] 0x1000 == 0x2000 (rs1 < rs2) |
| 32 | 0x080 | `00002000` | [BEQ] 0x2000 == 0x1000 (rs1 > rs2) |
| 33 | 0x084 | `00002000` | [BEQ] -0x1000 == 0x1000 |
| 34 | 0x088 | `00001000` | [BEQ] 0 == 0 |
| 35 | 0x08c | `00001000` | [BGE] 0x2000 >= 0x1000 |
| 36 | 0x090 | `00002000` | [BGE] 0x1000 >= 0x2000 |
| 37 | 0x094 | `00001000` | [BGE] iguais |
| 38 | 0x098 | `00002000` | [BGE] -0x1000 >= 0x1000 (sem sinal desviaria) |
| 39 | 0x09c | `00001000` | [BGE] 0x1000 >= -0x1000 (sem sinal nao desviaria) |
| 40 | 0x0a0 | `00001000` | [BGE] 0x7FFFF000 >= 0x80000000 (overflow no rs1-rs2) |
| 41 | 0x0a4 | `00002000` | [BGE] 0x80000000 >= 0x7FFFF000 |
| 42 | 0x0a8 | `00001000` | [BGE] negativos iguais |
| 43 | 0x0ac | `00001000` | [BGE] 0 >= -0x1000 |
| 44 | 0x0b0 | `00000414` | [JALR] jalr t6,-24(ra): t6 = pc+4 |
| 45 | 0x0b4 | `00001000` | [JALR] voltou de sub_a em ra+12 (bit 0 zerado) |
| 46 | 0x0b8 | `00002000` | [JALR] voltou de sub_b (retorno em t6) |
| 47 | 0x0bc | `00000028` | [JALR] ra escrito pela chamada de f_jj |
| 48 | 0x0c0 | `00002000` | [FIM] programa chegou ao fim |

## Observação (não é regressão)

A ROM habilitou o opcode OP-IMM (`0x13 → 0x86`) para o SLTIU. Com isso o `addi` passa
pelo mesmo caminho do tipo R, e com `funct3 = 0` o `ALU_Control` decide ADD/SUB/MUL
olhando `funct7`, que num I-type é `imm[11:5]`. O `nop` (`addi x0,x0,0`) continua
inofensivo. Um `addi` com imediato ≥ 1024 ou negativo, porém, vira SUB ou MUL. Isso
também vale para `li`/`mv`. No original o ADDI nem existia, e ele não é instrução do grupo.

## Arquivos

| arquivo | o que é |
|---|---|
| `teste_pipeline.s` / `.mem` | o programa de teste (fonte comentada / imagem para *Load Image*) |
| `testar.py` | modelo de referência + checagem de hazards + comparação com o circuito |
| `PipeSim.java` | harness: carrega o `.circ` com o jar do Logisim original, carrega o programa na RAM de instruções e dá clock |
