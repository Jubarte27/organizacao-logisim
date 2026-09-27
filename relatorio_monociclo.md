# 3. RISC-V Monociclo

Grupo 8 — instruções implementadas: **JALR, BGE, LUI, MUL, SLTIU**.

O circuito de partida implementava apenas **LW, SW, ADD, SUB, AND, OR e BEQ**.
Todas continuam funcionando; a Seção 3.7 documenta como isso foi verificado.

A Seção 3.1 reúne as modificações **estruturais**, que servem a mais de uma
instrução. As Seções 3.2 a 3.6 tratam de uma instrução cada, na ordem da tabela da
especificação, e concentram apenas as decisões específicas de cada uma.

---

## 3.1 Modificações estruturais

Três blocos foram reorganizados antes de qualquer instrução ser implementada. O
circuito original decodificava por **comparação**: um comparador por valor esperado,
encadeando multiplexadores de 2 entradas. Cada instrução nova custava mais um
comparador e mais um nível de mux. Substituímos isso por **multiplexadores indexados
diretamente pelo campo da instrução**, com uma constante em cada entrada — o mux
passa a funcionar como uma tabela de consulta, e acrescentar uma instrução vira
ligar uma constante numa entrada que já existe.

### ImmGen — imediatos por formato

O gerador passou a decidir o formato a partir do opcode, e não da instrução. Uma ROM
mapeia opcode → formato, e esse código seleciona um mux cujas entradas são os cinco
montadores de imediato:

| formato | código | opcodes |
|---|---|---|
| I | 0 | `0x03` LW, `0x13` SLTIU, `0x67` JALR |
| S | 1 | `0x23` SW |
| B | 2 | `0x63` BEQ/BGE |
| U | 3 | `0x37` LUI |
| J | 4 | `0x6F` (JAL) |

Das cinco instruções novas, só o LUI exigiu montador novo. JALR e SLTIU reutilizaram
o formato I do LW, e BGE reutilizou o formato B do BEQ.

### ALU — mapa dos códigos de operação

| código | operação | origem |
|---|---|---|
| 0 / 1 / 2 / 6 | AND / OR / ADD / SUB | original |
| **3** | `A × B` (32 bits baixos) | **MUL** |
| **4** | `A <u B` | **SLTIU** |
| 5 | (livre) | reservado |
| **14** | `A ≥s B` | **BGE** |
| **15** | passa B | **LUI** |

A ALU também exporta duas flags usadas pela lógica de desvio: `Zero` (NOR de todos
os bits do resultado) e `Less`.

### ALU_Control — decodificação por multiplexadores indexados

O decodificador original usava dois `Comparator` de 3 bits sobre `funct3` (testando
`== 000` e `== 110`) encadeando multiplexadores de 2 entradas; qualquer outro
`funct3` caía na saída padrão, AND. Para `funct3 = 000`, um `Splitter` extraía
`funct7[5]` e um mux de 2 entradas escolhia entre ADD e SUB.

Substituímos a cadeia de comparadores por um **único mux de 8 entradas indexado
diretamente por `funct3`**, com uma constante por entrada, e alargamos o mux de
`funct7` de 2 para 4 entradas, passando a extrair dois bits em vez de um.

Mux final, indexado por `ALUOp`:

| `ALUOp` | resultado | usado por |
|---|---|---|
| `00` | força código 2 (ADD) | LW, SW, **JALR** |
| `01` | força código 6 (SUB) | BEQ, **BGE** |
| `10` | consulta a tabela de `funct3` | tipo R e OP-IMM |
| `11` | força código 15 (passa B) | **LUI** |

Mux de `funct3` e — só para `funct3 = 000`, onde ADD, SUB e MUL colidem — o mux de
`funct7`, selecionado por dois bits extraídos com `BitSelector`:

| `funct3` | código | | `funct7[5]` | `funct7[0]` | código |
|---|---|---|---|---|---|
| `000` | ver tabela ao lado → | | 0 | 0 | 2 (ADD) |
| `011` | 4 (**SLTIU**) | | 0 | 1 | 3 (**MUL**) |
| `101` | 14 | | 1 | 0 | 6 (SUB) |
| `110` | 1 (OR) | | | | |
| `111` | 0 (AND) | | | | |

As entradas `001`, `010` e `100` (SLL, SLT, XOR) não estão implementadas — também
não estavam no circuito original, onde caíam na saída padrão AND.

### Bloco de controle — ROM de opcodes

A ROM é endereçada pelos 7 bits do opcode e produz 8 bits de controle:

| bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|
| sinal | RegWrite | ALUSrc | MemWrite | ALUop1 | ALUop0 | MemToReg | MemRead | Branch |

Conteúdo final (endereços não listados valem `0x00`):

| endereço | instruções | valor | RegWrite | ALUSrc | MemWrite | ALUOp | MemToReg | MemRead | Branch | origem |
|---|---|---|---|---|---|---|---|---|---|---|
| `0x03` | LW | `0xC6` | 1 | 1 | 0 | `00` | 1 | 1 | 0 | original |
| `0x13` | SLTIU | `0xD0` | 1 | 1 | 0 | `10` | 0 | 0 | 0 | **nova** |
| `0x23` | SW | `0x60` | 0 | 1 | 1 | `00` | 0 | 0 | 0 | original |
| `0x33` | ADD/SUB/AND/OR/MUL | `0x90` | 1 | 0 | 0 | `10` | 0 | 0 | 0 | original |
| `0x37` | LUI | `0xD8` | 1 | 1 | 0 | `11` | 0 | 0 | 0 | **nova** |
| `0x63` | BEQ/BGE | `0x09` | 0 | 0 | 0 | `01` | 0 | 0 | 1 | original |
| `0x67` | JALR | `0xC0` | 1 | 1 | 0 | `00` | 0 | 0 | 0 | **nova** |

**Só três das cinco instruções exigiram palavra nova.** MUL entra pelo opcode
`0x33` e BGE pelo `0x63`, ambos já mapeados; as duas são distinguidas de suas
"irmãs" inteiramente por `funct3`/`funct7`. As seções seguintes não repetem esta
tabela — citam apenas o valor e comentam os bits que exigem justificativa.

> [IMAGEM GERAL 1 — Circuito `main` inteiro já modificado, com retângulos coloridos
> marcando os cinco pontos alterados e uma legenda de cores, repetida nos zooms.]

> [IMAGEM GERAL 2 — Circuito `ALU`, com o mux de 16 entradas e as entradas 3, 4, 14
> e 15 numeradas.]

> [IMAGEM GERAL 3 — Circuito `ALU_Control`, com os três muxes identificados.]

> [IMAGEM GERAL 4 — Circuito `ImmGen`: ROM de formatos, mux e os cinco montadores.]

> [IMAGEM GERAL 5 — ROM de controle no *Edit Contents*, com `0x13`, `0x37` e `0x67`
> destacados.]

---

## 3.2 JALR — `JALR rd, imm(rs1)`

Opcode `0x67`, formato I. Palavra de controle **`0xC0`** (nova).

JALR faz duas coisas que o caminho de dados original não sabia fazer: desviar para
um endereço **calculado pela ALU** (`rs1 + imm`), e escrever **`PC + 4`** no banco
de registradores. A especificação do RISC-V ainda exige que o **bit 0 do endereço
calculado seja zerado**.

**Decisões de projeto**

- **Reconhecimento por comparação de opcode, não por bit de controle.** Um
  `Comparator` de 7 bits compara o opcode com `0x67` e gera o sinal `éJALR`. A
  alternativa seria um nono bit na palavra de controle, o que obrigaria a mexer no
  splitter que distribui os sinais no `main`. O comparador mantém a ROM em 8 bits e
  deixa o sinal rastreável até sua origem no esquemático.

- **Dois multiplexadores, nenhum somador novo.** `éJALR` controla um mux no caminho
  do PC (entre o somador `PC + 4` e o mux de desvio condicional) e um mux no dado
  escrito no banco (depois do mux de `MemToReg`):

  ```
                              éJALR
                                |
     PC + 4 ──────────────► entrada 0 ┐
                                      ├─ MUX ─► mux de desvio ─► PC
     (ALU_out AND 0xFFFFFFFE) entrada 1 ┘

                              éJALR
                                |
     saída do mux MemToReg ► entrada 0 ┐
                                       ├─ MUX ─► Write Data do banco
     PC + 4 ──────────────► entrada 1 ┘
  ```

  O somador `PC + 4` passou a ter três consumidores (PC, os dois muxes). Nenhum
  somador foi acrescentado.

- **Máscara do bit 0 fora da ALU.** Um `AND` de 32 bits com a constante
  `0xFFFFFFFE` na saída da ALU, em vez de uma entrada nova no mux de resultado. A
  ALU continua fazendo apenas a soma (código 2), que já existia — daí `ALUOp = 00`
  e `ALUSrc = 1` na palavra de controle.

- **Ordem dos muxes no caminho do PC.** O mux do JALR vem antes do mux de desvio
  condicional, dando prioridade a um desvio tomado. Na prática as duas condições
  nunca coexistem, porque os opcodes são distintos; a ordem escolhida é a que exige
  menos fios. Por isso `Branch = 0` para o JALR: seu desvio é incondicional e não
  passa pela lógica de `Branch`.

> [IMAGEM 3.2 — Zoom no caminho do PC: `Comparator` com a constante `0x67`, o fio do
> sinal `éJALR` com setas para seus dois destinos, o mux do JALR, o `AND` com
> `0xFFFFFFFE` e o mux de write-back do banco.]

**Verificação:** teste `t6_jalr` (desvio, `ra = PC + 4`, alinhamento) e os três
casos do `exhaustive_instruction`, um deles com base de endereço com bit 0 setado.

---

## 3.3 BGE — `BGE rs1, rs2, imm`

Opcode `0x63`, `funct3 = 101`, formato B. **Reaproveita a palavra `0x09` do BEQ**,
sem alteração.

BGE compartilha o opcode com o BEQ, então a palavra de controle é necessariamente a
mesma e a distinção tem de acontecer no bloco operativo, a partir de `funct3`. O
circuito original decidia o desvio com uma porta só — `desvia = Branch AND Zero` —
e o BGE precisa de `NOT Less`.

**Decisões de projeto**

- **Comparador dedicado, não o bit de sinal da subtração.** Com `ALUOp = 01` a ALU
  subtrai, e seria possível deduzir `rs1 ≥s rs2` do bit de sinal do resultado.
  Rejeitamos: essa dedução falha em caso de *overflow* da subtração, por exemplo
  `0x7FFFFFFF − 0x80000000`. Usamos um `Comparator` de 32 bits em **2's
  Complement** operando direto sobre A e B, cuja saída `<` é exportada como a flag
  `Less` da ALU. Fica correto em todo o intervalo de 32 bits.

- **Seleção da condição por multiplexador.** Um mux de 1 bit escolhe qual flag
  alimenta a porta `AND` do `Branch`:

  ```
     NOT(Less) ─► entrada 0 ┐
                            ├─ MUX (1 bit) ──┐
     Zero      ─► entrada 1 ┘                ├─ AND ─► desvia
                       ▲          Branch ────┘
              select ──┘   select = NOT funct3[2]
  ```

  | instrução | `funct3` | select | entrada | condição |
  |---|---|---|---|---|
  | BEQ | `000` | 1 | `Zero` | `rs1 == rs2` |
  | BGE | `101` | 0 | `NOT Less` | `rs1 ≥s rs2` |

- **Decodificação por um único bit de `funct3`.** Como só existem BEQ (`000`) e BGE
  (`101`), o bit 2 basta para distinguir — um `BitSelector` e um `NOT`, a
  decodificação mais barata possível. A limitação é explícita: se BNE (`001`) ou
  BLT (`100`) forem acrescentadas depois, isso precisa virar uma decodificação
  completa de `funct3`, por exemplo um `Comparator` testando `funct3 == 000`.

- **Entrada 14 da ALU (`A ≥s B`).** As saídas `>` e `=` do mesmo comparador são
  combinadas por um `OR` e alimentam a entrada 14 do mux de resultado, permitindo
  materializar a comparação como valor de 32 bits. O desvio em si não a utiliza —
  com `ALUOp = 01` quem decide é a flag `Less`.

**Defeito encontrado na verificação.** A primeira implementação ligou o `NOT(Less)`
num `OR` com `Zero`, direto na porta `AND` do `Branch`:
`desvia = Branch AND (Zero OR NOT Less)`. Como a expressão **não consulta `funct3`**,
ela passou a valer também para o BEQ — todo `beq` com `rs1 > rs2` desviava
indevidamente, uma regressão em instrução pré-existente. O defeito não era detectado
pelo `exhaustive_instruction.s`, porque todos os seus `beq` caem em casos em que
`==` e `≥` coincidem; foi preciso escrever o teste dedicado `t2_beq`:

```
ciclo 0  PC=00000000   lui t0, 0x1       (t0 = 0x1000)
ciclo 1  PC=00000004   beq t0, x0, ERRO  (0x1000 == 0? não)
ciclo 2  PC=00000010   <<< desviou mesmo assim
```

Corrigido pela substituição do `OR` pelo multiplexador descrito acima.

> [IMAGEM 3.3 — **Figura comparativa.** À esquerda, o circuito original com
> `AND(Branch, Zero)`. À direita, a versão final com o mux, o `BitSelector` e o
> `NOT`. Dois prints colados lado a lado.]

**Verificação:** teste `t7_bge` (positivos, negativos, sinais opostos, iguais) e
`t2_beq`, que garante que o BEQ não foi afetado.

---

## 3.4 LUI — `LUI rd, imm20`

Opcode `0x37`, formato U. Palavra de controle **`0xD8`** (nova).

LUI grava `imm[31:12] << 12` em `rd`. Não lê registrador, não acessa memória, não
faz aritmética.

**Decisões de projeto**

- **Bypass na ALU em vez de soma com `x0`.** A implementação óbvia seria
  `x0 + imediato`, reaproveitando o somador — mas exigiria forçar `rs1 = x0` no
  caminho de dados, ou confiar no campo lixo que a codificação U deixa naquela
  posição. Em vez disso, acrescentamos ao mux de resultado da ALU uma **entrada
  ligada diretamente em B** (código 15). Como `ALUSrc = 1` já coloca o imediato em
  B, a ALU só precisa deixá-lo passar. Custo: um fio.

- **Deslocamento no ImmGen, não na ALU.** O montador do formato U já entrega
  `inst[31:12]` concatenado com 12 zeros. Nenhum deslocador foi acrescentado ao
  caminho de dados.

- **Código de ALU forçado por `ALUOp = 11`, não obtido de `funct3`.** O formato U
  não tem campo `funct3` — aqueles bits fazem parte do imediato. Foi essa a razão
  de o LUI precisar de palavra de controle própria, apesar de ser a instrução mais
  simples das cinco: `ALUOp = 11` era a única combinação livre no mux final do
  `ALU_Control`.

> [IMAGEM 3.4 — Zoom no mux de resultado da ALU, destacando a entrada 15 ligada
> direto na rede B, e no montador do formato U dentro do `ImmGen`.]

**Verificação:** teste `t4_lui`, incluindo imediato 0 e imediato com bit 31 setado.

---

## 3.5 MUL — `MUL rd, rs1, rs2`

Opcode `0x33`, `funct3 = 000`, `funct7 = 0000001`, formato R. **Reaproveita a
palavra `0x90` de tipo R**, sem alteração.

MUL colide com ADD e SUB: mesmo opcode, mesmo `funct3`. A distinção está inteiramente
em `funct7` — `0000000` para ADD, `0100000` para SUB, `0000001` para MUL.

**Decisões de projeto**

- **Alargamento do mux de `funct7`, em vez de um caso à parte.** O circuito original
  já extraía `funct7[5]` com um `Splitter` para escolher entre ADD e SUB num mux de
  2 entradas. Bastaria acrescentar um comparador para detectar `funct7 = 0000001` e
  mais um nível de mux — foi o que evitamos. Em vez disso, extraímos um **segundo
  bit**, `funct7[0]` (que vale 1 apenas em MUL), e os dois bits juntos passaram a
  selecionar um mux de **4 entradas**. O caminho crítico não cresce, e a
  tabela-verdade fica legível no próprio esquemático.

- **Escolha dos bits.** `funct7[5]` distingue SUB (`0100000`) e `funct7[0]` distingue
  MUL (`0000001`). Não é preciso comparar os 7 bits: entre as três instruções
  implementadas, esses dois bits já são suficientes. A combinação `11` não
  corresponde a nenhuma instrução válida e ficou ligada em 0.

- **Truncamento em 32 bits.** O `Multiplier` do Logisim já descarta os 32 bits altos
  do produto, que é a semântica de `MUL` no RV32M. `MULH`, `MULHSU` e `MULHU` não
  foram pedidas, então não há caminho para a parte alta do produto.

> [IMAGEM 3.5 — Zoom no `ALU_Control`, destacando os dois `BitSelector` sobre
> `funct7` e o mux de 4 entradas com as constantes 2, 3 e 6.]

**Verificação:** teste `t5_mul`, com operandos negativos, produto negativo e um caso
de truncamento (`0x12345000 × 0x1000`, cujos 32 bits baixos valem `0x45000000`).

---

## 3.6 SLTIU — `SLTIU rd, rs1, imm12`

Opcode `0x13` (OP-IMM), `funct3 = 011`, formato I. Palavra de controle **`0xD0`**
(nova — o opcode OP-IMM não existia no circuito original).

`SLTIU` grava 1 em `rd` se `rs1 <u sign_extend(imm)`. O detalhe que define a
instrução: **o imediato é estendido com sinal, mas a comparação é sem sinal.**
`SLTIU rd, x0, -1` significa "`0 <u 0xFFFFFFFF`?" e tem de resultar **1**.

**Decisões de projeto**

- **Reuso do slot 4 da ALU.** A entrada 4 do mux de resultado estava prevista no
  projeto original para um `SLT` com sinal que nunca foi implementado — a entrada
  correspondente do mux de `funct3` no `ALU_Control` estava solta. Reutilizamos esse
  slot com o `Comparator` em **Numeric Type = Unsigned**. A alternativa era usar a
  entrada 5, que está livre, preservando a 4 para um futuro `SLT`. As duas
  funcionam; optamos pelo reuso por ser a modificação mínima, e registramos a
  consequência: **o slot 4 passou a ser exclusivamente sem sinal**, e um `SLT` com
  sinal futuro deverá usar a entrada 5.

- **Extensão com zeros, não com sinal.** A saída `<` do comparador tem 1 bit e passa
  por um `Bit Extender` de 1 → 32 configurado como **zero**. Com extensão de sinal o
  resultado verdadeiro seria `0xFFFFFFFF` em vez de 1.

- **Dois comparadores distintos na ALU.** O do SLTIU em *Unsigned* e o do BGE em
  *2's Complement* operam sobre as mesmas redes A e B, mas são componentes separados
  porque os modos são incompatíveis. A duplicação é intencional.

**Defeito encontrado na verificação.** Ao reutilizar o slot 4, o `Comparator`
permaneceu com o atributo **2's Complement** herdado do `SLT`, e a comparação
executada era `0 < -1` em vez de `0 <u 0xFFFFFFFF`. O erro só se manifesta quando o
bit 31 de algum operando vale 1, por isso passava despercebido em casos simples:

| operação | com sinal (errado) | sem sinal (correto) |
|---|---|---|
| `sltiu t0, x0, 1` | 1 | 1 |
| `sltiu t0, x0, -1` | **0** | **1** |
| `sltiu t0, t2, 1`, `t2 = 0xFFFFFFFF` | **1** | **0** |
| `sltiu t0, t4, 1`, `t4 = 0x80000000` | **1** | **0** |

Corrigido trocando o atributo para **Unsigned**. A comparação com sinal usada pelo
BGE não foi afetada, por ser um componente separado.

> [IMAGEM 3.6 — Zoom nos dois `Comparator` da ALU, lado a lado, com a tabela de
> atributos aberta mostrando `Unsigned` em um e `2's Complement` no outro.]

**Verificação:** teste `t3_sltiu`, com `-1`, `0xFFFFFFFF` e `0x80000000`.

---

## 3.7 Verificação

A verificação não foi feita apenas clicando no simulador. Foi montado um **banco de
testes automatizado** (`Trabalho01/testes/`) com três peças:

1. **Harness headless** (`Sim.java`) — carrega o `.circ` usando o próprio `.jar` do
   Logisim como biblioteca, avança o clock ciclo a ciclo e lê o PC e o banco de
   registradores, sem abrir a interface gráfica.
2. **Modelo de referência** (`ref.py`) — interpretador RV32IM independente, que
   produz o traço de PC esperado para o mesmo programa.
3. **Comparador** (`testar.sh`) — roda os dois e aponta o **primeiro ciclo em que os
   traços divergem**, o que leva direto à instrução culpada.

Sete programas foram escritos em assembly e montados com `riscv64-unknown-elf-as`,
além do `exhaustive_instruction.s` que já existia. Resultado final:

```
TESTE                   PC     a0       cobre
t1_originais            OK     00001000  LW, SW, ADD, SUB, AND, OR, BEQ (regressão)
t2_beq                  OK     00001000  BEQ: rs1>rs2, rs1<rs2, sinais opostos, iguais
t3_sltiu                OK     00001000  SLTIU: -1, 0xFFFFFFFF, 0x80000000
t4_lui                  OK     00001000  LUI: imediato 0 e bit 31
t5_mul                  OK     00001000  MUL: negativos e truncamento em 32 bits
t6_jalr                 OK     00001000  JALR: desvio, ra = PC+4, alinhamento
t7_bge                  OK     00001000  BGE: positivos, negativos, sinais opostos
exhaustive_instruction  OK     00000001  teste integrado
```

`PC = OK` significa que o traço de PC bateu **ciclo a ciclo** com o modelo de
referência, do começo ao fim. O `exhaustive_instruction` termina no laço de
`test_pass`, com `a0 = 1`.

### Regressão encontrada no LW

Além dos dois defeitos descritos nas Seções 3.3 e 3.6, o banco de testes encontrou
uma terceira regressão, sem relação com as instruções novas: a palavra de controle
do opcode `0x03` estava em `0x06` em vez de `0xC6` — o dígito `C` se perdeu numa
edição da ROM feita para acrescentar o LUI. Sem `RegWrite`, o `lw` lia da memória
mas não escrevia em `rd`; sem `ALUSrc`, o endereço virava `rs1 + rs2` em vez de
`rs1 + imm`. Corrigido no endereço `0x03` da ROM.

### Observação sobre a metodologia

Os três defeitos têm uma característica em comum: todos surgiram onde uma instrução
nova **compartilha um recurso** com uma pré-existente — BGE com BEQ (o opcode),
SLTIU com SLT (o slot da ALU), LUI com LW (a mesma ROM). Nenhum foi detectado por
inspeção do esquemático, e o do BEQ não era detectado nem pelo teste integrado, por
falta de um caso que distinguisse `==` de `≥`.

Um teste que passa não prova que a instrução está correta; prova apenas que aquele
conjunto de casos está correto. Por isso cada instrução ganhou um teste dedicado com
casos de fronteira escolhidos a partir da lógica implementada, e não apenas casos
representativos.

> [IMAGEM GERAL 6 — Saída do `./testar.sh` no terminal, tudo `OK`.]

> [IMAGEM GERAL 7 — Logisim com o `exhaustive_instruction.mem` carregado, parado no
> laço de `test_pass`, mostrando `a0 = 1` nos pinos de debug. É a figura que
> "convence o avaliador" pedida na especificação.]

---

## 3.8 Limitação conhecida — ADDI

Habilitar o opcode OP-IMM (`0x13`) para o SLTIU faz com que outras instruções tipo I
aritméticas sejam parcialmente aceitas. Para `ADDI` (`funct3 = 000`), o
`ALU_Control` consulta `funct7` para escolher entre ADD, SUB e MUL — mas em formato
I esses bits são `imm[11:5]`:

| instrução | `imm[11:5]` | operação executada |
|---|---|---|
| `addi t1, t0, 1` | `0000000` | ADD (correto por acaso) |
| `addi t2, t0, 32` | `0000001` | **MUL** |
| `addi t3, t0, -1` | `1111111` | **AND** |

Isso **não é regressão**: o circuito original não implementava OP-IMM, e `ADDI` não
faz parte das instruções atribuídas ao Grupo 8. O único OP-IMM implementado e testado
é o `SLTIU` (`funct3 = 011`), que não passa pelo mux de `funct7`.

A correção seria pequena: levar `ALUSrc` como entrada adicional do `ALU_Control` e
usar `NOT ALUSrc` para zerar os dois bits extraídos de `funct7`. Com `ALUOp = 10`,
`ALUSrc = 1` ocorre exclusivamente em OP-IMM.
