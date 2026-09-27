# Evidências — texto pronto para fechar a seção do monociclo

Substitui ou expande a Seção 3.7 (*Verificação*) do `relatorio_monociclo.md`.

A especificação pede que "o relatório deve convencer o avaliador que as novas
instruções das organizações estão funcionando". Convencer é diferente de afirmar:
a estratégia abaixo usa **três camadas de evidência**, da mais fácil de conferir
para a mais rigorosa.

---

## Camada 1 — Um programa de demonstração, com uma figura

`testes/demo_final.s` executa **as 5 instruções novas e as 7 originais** em 39
instruções, e confere cada resultado com um `BEQ`. Qualquer conferência que falhe
desvia para `falha`. Ao terminar:

- **`a0 = 1`** → as 12 instruções produziram o resultado esperado;
- **`a0 = 0`** → alguma falhou.

O programa foi escrito para que **cada instrução deixe um valor reconhecível** num
registrador, de modo que a figura possa ser conferida a olho:

| reg. | valor final | produzido por | confere o quê |
|---|---|---|---|
| `s1` | `DEADB000` | **LUI** | imediato de 20 bits deslocado 12 posições |
| `s2` | `0F000000` | **MUL** | `0x3000 × 0x5000`, com truncamento em 32 bits |
| `s0` | `00000001` | **SLTIU** | `0 <u 0xFFFFFFFF` (com sinal daria 0) |
| `s9` | `CAFE0000` | **JALR** | a sub-rotina executou **e** retornou |
| `ra` | `00000078` | **JALR** | endereço de retorno = `PC + 4` da chamada |
| `s8` | `DEADB000` | **SW + LW** | o valor gravado na RAM foi lido de volta |
| `s3` | `00008000` | **ADD** | `0x3000 + 0x5000` |
| `s4` | `00002000` | **SUB** | `0x5000 − 0x3000` |
| `s5` | `00001000` | **AND** | `0x3000 AND 0x5000` |
| `s6` | `00007000` | **OR** | `0x3000 OR 0x5000` |
| `t4` | `FFFFD000` | — | `−0x3000`, o operando negativo usado no **BGE** |
| **`a0`** | **`00000001`** | — | **todas as conferências passaram** |

BGE e BEQ não deixam valor em registrador — são desvios. Eles são conferidos pelo
**fluxo**: o programa só alcança `a0 = 1` se os seis desvios do trecho de BGE/BEQ
tomarem a decisão certa, incluindo os dois casos em que o `beq` **não** pode
desviar (`rs1 > rs2` e `rs1 < rs2`).

> [FIGURA A — Logisim parado no laço de parada, mostrando o banco de registradores
> com os valores da tabela acima. **É a figura mais importante do relatório.**
> Recorte a região do banco de registradores e, se couber, marque com setas os
> cinco valores das instruções novas.]

Vale acrescentar uma frase indicando **onde o programa parou**, porque é o que
distingue sucesso de falha sem precisar ler `a0`:

- sucesso: laço em **`PC = 0x88`**;
- falha: laço oscilando entre **`0x8C` e `0x90`**.

---

## Camada 2 — O programa é discriminante, não passa por acaso

Um programa que passa não vale nada se passaria de qualquer jeito. Para mostrar que
`demo_final` de fato detecta defeito, **reintroduzimos** no circuito, um de cada vez,
os três defeitos encontrados durante a verificação e reexecutamos:

| circuito | `a0` | resultado |
|---|---|---|
| ROM de controle com `0x06` no LW (defeito 3.7.1) | `0` | **reprova** |
| `Comparator` do SLTIU em *2's Complement* (defeito 3.6) | `0` | **reprova** |
| Condição de desvio sem seleção por `funct3` (defeito 3.3) | `0` | **reprova** |
| **circuito entregue** | **`1`** | **aprova** |

Isso é o que dá peso à Camada 1: o mesmo programa que aprova o circuito entregue
reprova cada uma das três versões defeituosas.

> [FIGURA B — opcional, mas boa: tabela acima montada como figura, ou um print do
> terminal com as quatro execuções lado a lado.]

---

## Camada 3 — Traço de PC conferido ciclo a ciclo

As duas camadas anteriores verificam o **resultado**. Esta verifica o **percurso**.

Um interpretador RV32IM independente (`testes/ref.py`) gera o traço de PC esperado
para o mesmo binário, e um harness (`testes/Sim.java`) extrai o traço real do
circuito, carregando o `.circ` com o próprio `.jar` do Logisim e avançando o clock
ciclo a ciclo, sem abrir a interface gráfica. Os dois traços são comparados
posição a posição:

```
$ diff <(./ref.py demo_final.mem 60) <(./run.py demo_final.mem 60)
(sem diferenças)
```

O mesmo procedimento foi aplicado aos sete testes dirigidos e ao
`exhaustive_instruction`:

```
$ ./testar.sh
TESTE                   PC     a0       cobre
t1_originais            OK     00001000  LW, SW, ADD, SUB, AND, OR, BEQ (regressão)
t2_beq                  OK     00001000  BEQ: rs1>rs2, rs1<rs2, sinais opostos, iguais
t3_sltiu                OK     00001000  SLTIU: -1, 0xFFFFFFFF, 0x80000000
t4_lui                  OK     00001000  LUI: imediato 0 e bit 31
t5_mul                  OK     00001000  MUL: negativos e truncamento em 32 bits
t6_jalr                 OK     00001000  JALR: desvio, ra = PC+4, alinhamento
t7_bge                  OK     00001000  BGE: positivos, negativos, sinais opostos
demo_final              OK     00000001  as 12 instruções, programa de demonstração
exhaustive_instruction  OK     00000001  teste integrado
```

`PC = OK` significa que o traço bateu **ciclo a ciclo** do começo ao fim — não
apenas que o resultado final coincidiu. Um desvio tomado no momento errado, ainda
que o valor final saísse certo por acaso, apareceria aqui.

> [FIGURA C — print do terminal com a saída do `./testar.sh`.]

---

## Nota técnica para antecipar uma pergunta

Se o avaliador abrir o banco de registradores e olhar `x0`, pode encontrar um valor
diferente de zero. Isso é esperado e **não é um defeito**: a instrução
`jalr x0, 0(ra)`, usada como retorno de sub-rotina, tem `rd = x0` e o flip-flop
físico do registrador 0 chega a ser escrito. A **leitura** de `x0`, porém, é fixada
em zero por construção — a entrada 0 dos dois multiplexadores de leitura do
`Register Bank` vem de uma constante de 32 bits com valor 0, e não da saída do
registrador 0. O programa nunca enxerga o valor retido.

Isso foi verificado com um teste próprio (`testes/t9_x0.s`): após `add x0, s1, s1`
com `s1 = 0x5000`, o flip-flop retém `0xA000`, mas `sltiu a0, x0, 1` resulta 1 e
`add s2, x0, s1` resulta `0x5000` — ou seja, as duas leituras de `x0` devolveram 0.
Esse comportamento vem do circuito original e não foi alterado.

---

## Roteiro dos prints

1. Abra `RISCV_Monociclo.circ` no Logisim.
2. Botão direito na ROM de instruções → *Load Image* → `testes/demo_final.mem`.
3. *Simulate → Reset Simulation*, depois *Simulate → Ticks Enabled* (ou `Ctrl+K`).
4. Deixe rodar uns segundos e desabilite os ticks. O PC deve estar parado em `0x88`.
5. **Print 1 (Figura A):** banco de registradores com os valores da tabela.
6. **Print 2:** o PC parado em `0x88`, para provar que caiu no laço de sucesso.
7. **Print 3 (Figura C):** terminal com a saída do `./testar.sh`.

Dica: aumente o zoom antes de printar e recorte só a região de interesse. Um print
da janela inteira fica ilegível impresso.

---

## Parágrafo de fechamento sugerido

> As cinco instruções atribuídas ao Grupo 8 — JALR, BGE, LUI, MUL e SLTIU — foram
> implementadas na organização monociclo e verificadas em três níveis: um programa
> de demonstração que exercita as doze instruções suportadas e termina com
> `a0 = 1`; a confirmação de que esse mesmo programa reprova cada uma das três
> versões defeituosas encontradas durante o desenvolvimento; e a comparação do
> traço de PC, ciclo a ciclo, contra um interpretador RV32IM independente, para os
> nove programas de teste. As sete instruções que já existiam no circuito original
> continuam funcionando, o que é verificado explicitamente pelo teste
> `t1_originais` e pelo programa de demonstração.
