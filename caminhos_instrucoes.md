# Guia para desenhar o caminho de cada instrução (monociclo)

Todos os pontos abaixo foram conferidos no netlist do `RISCV_Monociclo.circ`, porta
por porta. As coordenadas são as do Logisim (aparecem no canto inferior esquerdo da
janela conforme você move o mouse) e servem para achar o bloco certo sem ambiguidade.

## Mapa dos blocos do circuito `main`

| # | bloco | âncora | portas relevantes |
|---|---|---|---|
| 1 | **PC** (`Register`) | (120,360) | saída (120,360) · entrada D (90,360) |
| 2 | Splitter do PC | (140,360) | tira os 2 bits baixos → endereço |
| 3 | **ROM de instruções** | (310,360) | endereço (170,360) · instrução (310,360) |
| 4 | **Instruction Decode** | (360,340) | opcode (360,340) · rd (360,350) · funct3 (360,360) · rs1 (360,370) · rs2 (360,380) · funct7 (360,390) |
| 5 | **Register Bank** | (540,370) | rs1 (510,350) · rs2 (510,360) · rd (510,370) · WriteData (510,380) · RegWrite (510,390) · saídas (540,370) e (540,380) |
| 6 | **ImmGen** | (540,450) | instrução (510,450) · imediato (540,450) |
| 7 | **ROM de controle** | (230,760) | endereço (90,760) · saída → splitter (540,700) |
| 8 | **ALU_Control** | (580,510) | ALUOp (550,500) · funct3 (550,510) · funct7 (550,520) · saída (580,510) |
| 9 | **Mux ALUSrc** | (610,380) | ent.0 (580,370) = rs2 · ent.1 (580,390) = imediato · sel (590,400) |
| 10 | **ALU** | (670,350) | A (640,350) · B (640,360) · ALUControl (640,370) · **Zero (670,350)** · **Result (670,360)** · **Less (670,370)** |
| 11 | Somador **PC + 4** | (240,270) | PC (200,280) · const. 4 (200,260) · saída (240,270) |
| 12 | **Shifter** (`<< 1`) | (610,300) | imediato (570,290) · saída (610,300) |
| 13 | Somador de **desvio** | (680,270) | PC (640,260) · imediato<<1 (640,280) · saída (680,270) |
| 14 | **Comparador `opcode == 0x67`** | (410,810) | opcode (370,800) · const. `0x67` (370,820) · **saída `éJALR` (410,810)** |
| 15 | **AND máscara `& 0xFFFFFFFE`** | (960,270) | ALU Result (930,260) · const. (930,280) · saída (960,270) |
| 16 | **Mux JALR do PC** | (400,240) | ent.0 (370,230) = PC+4 · ent.1 (370,250) = endereço mascarado · sel (380,260) = `éJALR` |
| 17 | **Mux de desvio** | (860,250) | ent.0 (830,240) · ent.1 (830,260) = alvo do desvio · sel (840,270) |
| 18 | NOT sobre `Less` | (700,370) | entrada (700,390) · saída (700,340) |
| 19 | **Mux de condição** | (710,310) | ent.0 (700,340) = `NOT Less` · ent.1 (720,340) = `Zero` · sel (730,330) · saída (710,310) |
| 20 | `BitSelector` + `NOT` do `funct3` | (1040,150) e (1000,230) | seleciona `funct3[2]` e inverte |
| 21 | **AND do Branch** | (750,280) | Branch (720,270) · condição (720,290) · saída (840,270) |
| 22 | **RAM** | (890,360) | endereço (750,360) · DataIn (750,380) · DataOut (890,360) |
| 23 | **Mux MemToReg** | (940,350) | ent.0 (910,340) = ALU · ent.1 (910,360) = RAM · sel (920,370) |
| 24 | **Mux JALR de write-back** | (320,490) | ent.0 (290,480) = normal · ent.1 (290,500) = PC+4 · sel (300,510) = `éJALR` |

**Retorno ao PC:** a saída do mux de desvio (860,250) dá a volta por cima do
circuito — (890,250) → (890,190) → (70,190) → (70,360) → entrada D do PC (90,360).
Esse fio longo do topo faz parte de **todas** as instruções.

---

## Trecho comum a todas as instruções (busca e decodificação)

Desenhe esse tronco em todas as cinco figuras, de preferência numa cor mais neutra
(cinza escuro), reservando a cor forte para o que é específico da instrução.

```
PC (1) ─► splitter (2) ─► endereço ─► ROM de instruções (3) ─► instrução
                                                                  │
                        ┌─────────────────────────────────────────┤
                        ▼                                         ▼
              Instruction Decode (4)                          ImmGen (6)
                        │
        ┌───────────────┼──────────────┬───────────────┐
        ▼               ▼              ▼               ▼
   opcode (7)      rs1/rs2/rd (5)   funct3/7 (8)   opcode ─► comparador 0x67 (14)
        │
        ▼
  ROM de controle (7) ─► splitter (540,700) ─► 8 sinais de controle

PC (1) ─► somador PC+4 (11)
```

---

## 3.2 JALR — `JALR rd, imm(rs1)`

**Cor sugerida:** dois tons — um para o cálculo do endereço, outro para o `PC + 4`.

**Caminho do dado (cálculo do endereço de destino)**

1. `rs1` (360,370) → Register Bank (5) → dado de `rs1` (540,370) → **ALU entrada A** (640,350)
2. ImmGen (6) → imediato (540,450) → (560,450) → (560,390) → **mux ALUSrc entrada 1** (580,390)
3. `ALUSrc = 1` → mux (9) → (620,380) → (620,360) → **ALU entrada B** (640,360)
4. `ALUOp = 00` → ALU_Control (8) força o código 2 → **ALU soma** `rs1 + imm`
5. **ALU Result** (670,360) → splitter (720,360) → (720,450) → (900,450) → (900,260) → **AND máscara** (15) com `0xFFFFFFFE`
6. Saída (960,270) → (970,270) → (970,170) → (350,170) → (350,250) → **mux JALR do PC entrada 1** (370,250)

**Caminho do controle**

7. opcode (360,340) → (370,340) → (370,710) → (280,710) → (280,800) → (370,800) → **comparador (14)** → `éJALR = 1` → seleciona os muxes (16) e (24)

**Caminho do PC**

8. Mux JALR (16) escolhe a entrada 1 → (400,240) → (830,240) → **mux de desvio entrada 0**
9. `Branch = 0` → mux (17) deixa passar → (890,250) → (890,190) → (70,190) → **PC**

**Caminho de escrita no banco**

10. Somador `PC + 4` (11) → (300,270) → (400,270) → (400,430) → (250,430) → (250,500) → **mux de write-back entrada 1** (290,500)
11. `éJALR = 1` → mux (24) → (320,490) → (470,490) → (470,380) → **WriteData do banco** (510,380)
12. `rd` (360,350) → (510,370); `RegWrite = 1` grava

**Apagar / deixar em cinza claro:** RAM (22), mux MemToReg (23), Shifter (12),
somador de desvio (13), mux de condição (19) e toda a lógica de `Branch` (18, 20, 21).

> **Legenda sugerida:** "Caminho do JALR. Em azul, o cálculo `rs1 + imm` pela ALU e a
> máscara do bit 0, que alimentam o mux do PC. Em laranja, `PC + 4` sendo desviado
> para o banco de registradores. O sinal `éJALR`, gerado pelo comparador de opcode,
> controla os dois muxes."

---

## 3.3 BGE — `BGE rs1, rs2, imm`

**Cor sugerida:** dois tons — um para a comparação, outro para o cálculo do alvo.

**Caminho da comparação**

1. `rs1` (360,370) e `rs2` (360,380) → Register Bank (5)
2. Dado de `rs1` (540,370) → **ALU entrada A** (640,350)
3. Dado de `rs2` (540,380) → (570,380) → (570,370) → **mux ALUSrc entrada 0** (580,370); `ALUSrc = 0` → **ALU entrada B**
4. `ALUOp = 01` → ALU_Control (8) força o código 6 (subtração)
5. Dentro da ALU, o `Comparator` em *2's Complement* gera a flag **`Less`** (670,370)
6. `Less` → (670,400) → (700,400) → **NOT** (18) → (700,340) → **mux de condição entrada 0**

**Caminho da seleção da condição**

7. `funct3` (360,360) → (430,360) → **`BitSelector`** (20), constante de seleção 2 → `funct3[2] = 1`
8. → **NOT** (1000,230) → `select = 0` → (730,330) → mux (19) escolhe a **entrada 0** (`NOT Less`)
9. Saída (710,310) → (710,300) → (720,300) → **AND do Branch entrada 1** (720,290)
10. `Branch = 1` da ROM de controle → (700,300) → (700,270) → **AND entrada 0** (720,270)
11. `AND` (21) = 1 → (840,270) → **select do mux de desvio**

**Caminho do endereço de destino**

12. ImmGen (6), formato B → imediato (540,450) → (560,450) → (560,290) → (570,290) → **Shifter** (12), `<< 1`
13. Saída (610,300) → (630,300) → (630,280) → **somador de desvio entrada 1** (640,280)
14. PC (120,360) → (140,300) → (460,300) → (460,270) → (640,270) → **entrada 0** (640,260)
15. Soma (680,270) → (690,270) → (690,260) → (830,260) → **mux de desvio entrada 1**
16. Mux (17) escolhe a entrada 1 → (890,250) → (890,190) → (70,190) → **PC**

**Apagar:** RAM (22), mux MemToReg (23), mux de write-back (24), comparador `0x67`
(14), AND máscara (15), mux JALR do PC (16). `RegWrite = 0`: nada é escrito no banco.

> **Legenda sugerida:** "Caminho do BGE. Em vermelho, a comparação: a flag `Less` da
> ALU, invertida, chega ao mux de condição. Em verde, o cálculo do alvo
> `PC + (imm << 1)`. O `funct3[2]`, invertido, seleciona `NOT Less` em vez de `Zero`
> — é o que distingue BGE de BEQ, que compartilham o opcode `0x63`."

**Figura complementar que vale a pena:** a mesma imagem para o **BEQ**, idêntica,
mudando só o destaque no mux de condição (entrada 1 = `Zero`). Coloca lado a lado e o
leitor entende o papel do mux sem ler uma linha de texto.

---

## 3.4 LUI — `LUI rd, imm20`

**Cor sugerida:** um tom só — o caminho é curto e é justamente esse o argumento.

1. ImmGen (6), formato U → `imm[31:12] << 12` → (540,450) → (560,450) → (560,390) → **mux ALUSrc entrada 1** (580,390)
2. `ALUSrc = 1` → mux (9) → (620,380) → (620,360) → **ALU entrada B** (640,360)
3. `ALUOp = 11` → ALU_Control (8) força o código **15**
4. **ALU** (10): a entrada B atravessa o mux de resultado sem passar por nenhuma unidade → **Result** (670,360)
5. Result → splitter (720,360) → (720,450) → (900,450) → (900,340) → **mux MemToReg entrada 0** (910,340)
6. `MemToReg = 0` → mux (23) → (960,350) → (960,540) → (270,540) → (270,480) → **mux de write-back entrada 0** (290,480)
7. `éJALR = 0` → mux (24) → (320,490) → (470,490) → (470,380) → **WriteData** (510,380)
8. `rd` (360,350) → (510,370); `RegWrite = 1` grava
9. PC: somador `PC + 4` (11) → (300,270) → (300,230) → **mux JALR entrada 0** (370,230) → mux (16) → (830,240) → **mux de desvio entrada 0** → (890,190) → (70,190) → **PC**

**Apagar:** Register Bank como *leitura* (a entrada A da ALU recebe `rs1`, mas o
valor é ignorado pelo código 15 — vale deixar essa seta cinza e pontilhada, é um
detalhe que o avaliador pode perguntar), RAM (22), Shifter (12), somador de desvio
(13), toda a lógica de `Branch` (18–21) e de JALR (14–16, 24).

> **Legenda sugerida:** "Caminho do LUI. O imediato montado pelo ImmGen atravessa a
> ALU sem sofrer operação (código 15, *passa B*) e vai direto ao banco de
> registradores. A entrada A da ALU, em cinza, recebe `rs1` mas é ignorada."

---

## 3.5 MUL — `MUL rd, rs1, rs2`

**Cor sugerida:** um tom para os dados, outro para a decodificação
`funct3`/`funct7` — é nela que está a decisão de projeto da instrução.

**Caminho dos dados**

1. `rs1` (360,370) → (510,350) e `rs2` (360,380) → (510,360) → **Register Bank** (5)
2. Dado de `rs1` (540,370) → (550,350) → (640,350) → **ALU entrada A**
3. Dado de `rs2` (540,380) → (550,380) → (570,380) → (570,370) → **mux ALUSrc entrada 0** (580,370)
4. `ALUSrc = 0` → mux (9) → (620,380) → (620,360) → **ALU entrada B** (640,360)
5. **ALU**: código 3 → o `Multiplier` de 32 bits → **Result** (670,360)
6. Write-back idêntico ao LUI, passos 5 a 8 (`MemToReg = 0`, `éJALR = 0` → `rd`)
7. PC: `PC + 4`, idêntico ao LUI, passo 9

**Caminho da decodificação (destacar em cor separada)**

8. `funct3` (360,360) → (430,360) → (430,510) → **ALU_Control entrada `funct3`** (550,510)
9. `funct7` (360,390) → (410,390) → (410,520) → **ALU_Control entrada `funct7`** (550,520)
10. Dentro do `ALU_Control`: `ALUOp = 10` → mux de `funct3` → `funct3 = 000` → mux de `funct7` → `funct7[0] = 1` → **código 3**
11. Saída (580,510) → (630,510) → (630,370) → **ALU entrada ALUControl** (640,370)

**Apagar:** ImmGen (6) e mux ALUSrc entrada 1, RAM (22), Shifter (12), somador de
desvio (13), lógica de `Branch` (18–21) e de JALR (14–16, 24).

> **Legenda sugerida:** "Caminho do MUL. Em azul, os dois operandos lidos do banco
> chegando à ALU. Em roxo, a decodificação: `funct3 = 000` leva ao mux de `funct7`,
> onde o bit `funct7[0] = 1` seleciona o código 3 (multiplicador). MUL reaproveita
> integralmente a palavra de controle de tipo R."

**Figura complementar opcional:** um recorte só do `ALU_Control` mostrando os dois
`BitSelector` e o mux de 4 entradas, com os valores de `funct7` de ADD, SUB e MUL
anotados ao lado. Explica a decisão de projeto melhor do que o datapath inteiro.

---

## 3.6 SLTIU — `SLTIU rd, rs1, imm12`

**Cor sugerida:** um tom para os dados, outro para a decodificação — mesmo esquema
do MUL, o que facilita a comparação entre as duas figuras.

**Caminho dos dados**

1. `rs1` (360,370) → (510,350) → **Register Bank** (5) → dado (540,370) → **ALU entrada A** (640,350)
2. ImmGen (6), formato I, **estendido com sinal** → (540,450) → (560,450) → (560,390) → **mux ALUSrc entrada 1** (580,390)
3. `ALUSrc = 1` → mux (9) → **ALU entrada B** (640,360)
4. **ALU**: código 4 → `Comparator` em *Unsigned* → `Bit Extender` (zero) → **Result** (670,360)
5. Write-back idêntico ao LUI, passos 5 a 8
6. PC: `PC + 4`, idêntico ao LUI, passo 9

**Caminho da decodificação**

7. `funct3` (360,360) → (430,360) → (430,510) → **ALU_Control** (550,510)
8. `ALUOp = 10` → mux de `funct3` → `funct3 = 011` → constante `0x4` → **código 4**
9. Saída (580,510) → (630,510) → (630,370) → **ALU** (640,370)

**Apagar:** a leitura de `rs2` (510,360) — naquela posição da instrução estão bits do
imediato, não um registrador; vale deixar essa seta cinza e pontilhada, é o contraste
com a figura do MUL. Também: RAM (22), Shifter (12), somador de desvio (13), lógica
de `Branch` (18–21) e de JALR (14–16, 24).

> **Legenda sugerida:** "Caminho do SLTIU. Difere do MUL apenas em dois pontos: o
> operando B vem do ImmGen (`ALUSrc = 1`) em vez do banco, e `funct3 = 011` seleciona
> o código 4 — o comparador sem sinal. O imediato é estendido **com** sinal; a
> comparação é **sem** sinal."

---

## Dicas práticas para montar as figuras

- **Exporte, não printe.** `File → Export Image` no Logisim gera PNG com fundo
  branco e traço limpo, legível impresso. Print de tela fica cinza e serrilhado.
- **Uma imagem-base só.** Exporte o `main` uma vez e faça as cinco marcações por
  cima da mesma imagem, no Google Slides, Inkscape ou até no PowerPoint. Além de mais
  rápido, garante que as cinco figuras fiquem no mesmo enquadramento — o leitor
  compara sem se reorientar.
- **Duas cores no máximo por figura**, mais o cinza do tronco comum. Três cores já
  ficam difíceis de seguir.
- **Setas de direção nos fios destacados.** Sem elas, o leitor não sabe para que lado
  o dado corre, principalmente no fio de retorno ao PC, que dá a volta pelo topo.
- **Numere os passos na própria imagem** (círculos com 1, 2, 3…) e use a mesma
  numeração da legenda. É o que transforma a figura em explicação, e não em
  ilustração.
