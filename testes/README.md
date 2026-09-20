# Testes do RISC-V Monociclo

Banco de testes headless: roda os programas no `.circ` **sem abrir o Logisim**
e compara o traço de PC contra um modelo RV32IM de referência.

## Como rodar

```bash
./testar.sh                                 # testa ../RISCV_Monociclo.circ
./testar.sh RISCV_Monociclo_corrigido.circ  # testa a versão corrigida
```

Para rodar um teste só e ver o traço:

```bash
./run.py t2_beq.mem 20                      # traço do circuito
./ref.py t2_beq.mem 20                      # traço esperado
diff <(./ref.py t2_beq.mem 20) <(./run.py t2_beq.mem 20)
```

Para escrever um teste novo: crie `meu_teste.s`, rode `./asm.sh meu_teste.s`
(gera `meu_teste.mem`) e carregue esse `.mem` na ROM de instruções no Logisim
(botão direito → *Load Image*), ou passe para `./run.py`.

Convenção dos testes: `a0 = 0x1000` no fim = passou, `a0 = 0` = falhou.

## Arquivos

| arquivo | o que é |
|---|---|
| `Sim.java` | harness que carrega o `.circ` usando o jar do Logisim e dá clock ciclo a ciclo |
| `run.py` | troca a ROM de instruções pelo `.mem` dado e chama o harness |
| `ref.py` | modelo RV32IM de referência (gera o traço esperado) |
| `asm.sh` | monta um `.s` para o formato `v2.0 raw` do Logisim |
| `testar.sh` | roda todos os testes e mostra OK / FALHOU |
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
