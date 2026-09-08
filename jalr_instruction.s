.section .text
.globl _start

# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
_start:
    # --------------------------------------------------------------------------
    # 0. Bootstrap Constants (strictly without ADDI / LI / MV)
    # --------------------------------------------------------------------------
    sltiu s1, x0, 1             # s1 = 1 (0 < 1 unsigned)
    add   s2, s1, s1            # s2 = 2
    add   s3, s2, s1            # s3 = 3
    add   s4, s2, s2            # s4 = 4
    mul   s5, s4, s3            # s5 = 12 (offset to capture subroutine address)

    # --------------------------------------------------------------------------
    # 1. Standard JALR Call & Return (Immediate pair %hi/%lo)
    #    Target: subroutine_standard
    # --------------------------------------------------------------------------
    lui   t0, %hi(subroutine_standard)
    jalr  ra, %lo(subroutine_standard)(t0)
.L_ret1:
    beq   a0, s1, .L_chk1       # verify subroutine incremented a0 to 1
    beq   x0, x0, fail
.L_chk1:
    and   t1, ra, s1            # verify return address alignment (ra[0] == 0)
    beq   t1, x0, .L_chk2
    beq   x0, x0, fail
.L_chk2:

    # --------------------------------------------------------------------------
    # 2. Immediate Offsets in JALR (positive and negative)
    #    s10 now contains the exact runtime entry address of subroutine_standard
    # --------------------------------------------------------------------------
    # Positive offset: base = s10 - 4, target = (s10 - 4) + 4 = s10
    sub   t0, s10, s4
    jalr  ra, 4(t0)
.L_ret2:
    beq   a0, s2, .L_chk3       # a0 == 2
    beq   x0, x0, fail
.L_chk3:

    # Negative offset: base = s10 + 4, target = (s10 + 4) - 4 = s10
    add   t0, s10, s4
    jalr  ra, -4(t0)
.L_ret3:
    beq   a0, s3, .L_chk4       # a0 == 3
    beq   x0, x0, fail
.L_chk4:

    # --------------------------------------------------------------------------
    # 3. Hardware LSB Clearing: target = (rs1 + offset) & ~1
    # --------------------------------------------------------------------------
    or    t0, s10, s1           # set bit 0 (odd address)
    jalr  ra, 0(t0)             # hardware clears bit 0, lands at s10 safely
.L_ret4:
    add   s6, s3, s1            # s6 = 4
    beq   a0, s6, .L_chk5       # a0 == 4
    beq   x0, x0, fail
.L_chk5:

    # --------------------------------------------------------------------------
    # 4. Indirect Jump via Memory (SW, LW, MUL, JALR)
    # --------------------------------------------------------------------------
    lui   t1, %hi(scratch_mem)
    sw    s10, %lo(scratch_mem)(t1)  # write subroutine pointer to memory
    lw    t2, %lo(scratch_mem)(t1)   # read back pointer

    # Safeguard: verify memory held s10; if read returns 0, fail instead of loop
    beq   t2, s10, .L_mem_valid
    beq   x0, x0, fail
.L_mem_valid:
    jalr  ra, 0(t2)                  # call via memory-loaded pointer
.L_ret5:
    add   s7, s6, s1            # s7 = 5
    beq   a0, s7, .L_chk6       # a0 == 5
    beq   x0, x0, fail
.L_chk6:

    # --------------------------------------------------------------------------
    # 5. Register Overlap Hazard (rd == rs1)
    #    Target address is computed from t0 before t0 is overwritten with PC + 4
    # --------------------------------------------------------------------------
    lui   t0, %hi(subroutine_overwrite)
    jalr  t0, %lo(subroutine_overwrite)(t0)
.L_ret6:
    add   s8, s7, s1            # s8 = 6
    beq   a0, s8, .L_chk7       # a0 == 6
    beq   x0, x0, fail
.L_chk7:

    # --------------------------------------------------------------------------
    # 6. Branch & Distance Validation (SUB & BGE)
    # --------------------------------------------------------------------------
    sub   t0, s10, ra
    bge   s10, ra, pass         # s10 is located past _start, so s10 >= ra
    beq   x0, x0, fail

# ------------------------------------------------------------------------------
# Terminal Handlers
# ------------------------------------------------------------------------------
pass:
    sltiu a0, x0, 1             # a0 = 1 (pass flag)
    beq   x0, x0, pass          # terminal success loop

fail:
    add   a0, x0, x0            # a0 = 0 (fail flag)
    beq   x0, x0, fail          # terminal failure loop

# ------------------------------------------------------------------------------
# Subroutines
# ------------------------------------------------------------------------------
subroutine_standard:
    add   a0, a0, s1            # a0 += 1
    lui   t4, %hi(.L_sub_body)
    jalr  s10, %lo(.L_sub_body)(t4)
.L_sub_body:
    # jalr saved (PC + 4) into s10, which is .L_sub_body (12 bytes past entry)
    sub   s10, s10, s5          # s10 = (entry + 12) - 12 = exact entry address
    jalr  x0, 0(ra)             # return via ra, discard link (rd = x0)

subroutine_overwrite:
    add   a0, a0, s1            # a0 += 1
    jalr  x0, 0(t0)             # return via link stored in t0

# ------------------------------------------------------------------------------
# Scratch Data (written before read; no pre-initialized values required)
# ------------------------------------------------------------------------------
.section .data
scratch_mem:
    .word 0