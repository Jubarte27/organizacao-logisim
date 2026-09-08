.section .text
.globl _start

# ------------------------------------------------------------------------------
# Subroutines placed at the start so no padding NOPs are emitted into .text.
# ------------------------------------------------------------------------------
# Entry point 0: Jump over test subroutines into main test suite
beq x0, x0, _start

# Subroutine for testing JALR
subroutine_target:
    add  a0, a0, s5              # a0 = a0 + 5
    jalr x0, 0(ra)              # return to caller via JALR (raw return)

subroutine_entry2:
    add  a1, a1, s3              # a1 = a1 + 3
    jalr x0, 0(ra)              # return to caller via JALR

# ------------------------------------------------------------------------------
# Main Test Suite
# ------------------------------------------------------------------------------
_start:
    # --------------------------------------------------------------------------
    # Bootstrap Constants (without ADDI or LI)
    # --------------------------------------------------------------------------
    add   s0, x0, x0            # s0 = 0
    sltiu s1, x0, 1             # s1 = 1  (0 < 1 unsigned is true)
    add   s2, s1, s1            # s2 = 2  (1 + 1)
    add   s3, s2, s1            # s3 = 3  (2 + 1)
    add   s4, s2, s2            # s4 = 4  (2 + 2)
    add   s5, s4, s1            # s5 = 5  (4 + 1)
    add   s6, s3, s3            # s6 = 6  (3 + 3)

    # --------------------------------------------------------------------------
    # 1. Exhaustive Testing: SLTIU (Set Less Than Immediate Unsigned)
    # --------------------------------------------------------------------------
    # Case 1.1: 0 < 1 -> 1
    sltiu t0, x0, 1
    beq   t0, s1, .L_sltiu_1
    beq   x0, x0, test_fail
.L_sltiu_1:

    # Case 1.2: 0 < 0 -> 0
    sltiu t0, x0, 0
    beq   t0, x0, .L_sltiu_2
    beq   x0, x0, test_fail
.L_sltiu_2:

    # Case 1.3: 1 < 1 -> 0
    sltiu t0, s1, 1
    beq   t0, x0, .L_sltiu_3
    beq   x0, x0, test_fail
.L_sltiu_3:

    # Case 1.4: 1 < 2 -> 1
    sltiu t0, s1, 2
    beq   t0, s1, .L_sltiu_4
    beq   x0, x0, test_fail
.L_sltiu_4:

    # Case 1.5: 2 < 1 -> 0
    sltiu t0, s2, 1
    beq   t0, x0, .L_sltiu_5
    beq   x0, x0, test_fail
.L_sltiu_5:

    # Case 1.6: 0 < -1 (sign-extended imm -1 is 0xFFFFFFFF unsigned) -> 1
    sltiu t0, x0, -1
    beq   t0, s1, .L_sltiu_6
    beq   x0, x0, test_fail
.L_sltiu_6:

    # Case 1.7: 0xFFFFFFFF < 1 (unsigned max < 1) -> 0
    sub   t1, x0, s1            # t1 = 0 - 1 = 0xFFFFFFFF (-1)
    sltiu t0, t1, 1
    beq   t0, x0, .L_sltiu_7
    beq   x0, x0, test_fail
.L_sltiu_7:

    # Case 1.8: 0xFFFFFFFF < -1 (0xFFFFFFFF < 0xFFFFFFFF) -> 0
    sltiu t0, t1, -1
    beq   t0, x0, .L_sltiu_8
    beq   x0, x0, test_fail
.L_sltiu_8:

    # --------------------------------------------------------------------------
    # 2. Exhaustive Testing: LUI (Load Upper Immediate)
    # --------------------------------------------------------------------------
    # Case 2.1: lui with 0
    lui   t0, 0
    beq   t0, x0, .L_lui_1
    beq   x0, x0, test_fail
.L_lui_1:

    # Case 2.2: lui loads exact upper bit pattern
    lui   t0, 0x12345
    lui   t1, 0x12345
    beq   t0, t1, .L_lui_2
    beq   x0, x0, test_fail
.L_lui_2:

    # Case 2.3: subtract matching lui results
    sub   t2, t0, t1
    beq   t2, x0, .L_lui_3
    beq   x0, x0, test_fail
.L_lui_3:

    # Case 2.4: lui 0x80000 sets sign bit (0x80000000 <= 0 signed)
    lui   t0, 0x80000
    bge   x0, t0, .L_lui_4
    beq   x0, x0, test_fail
.L_lui_4:

    # --------------------------------------------------------------------------
    # 3. Exhaustive Testing: ADD
    # --------------------------------------------------------------------------
    # Case 3.1: 0 + 0 = 0
    add   t0, x0, x0
    beq   t0, x0, .L_add_1
    beq   x0, x0, test_fail
.L_add_1:

    # Case 3.2: Identity 5 + 0 = 5
    add   t0, s5, x0
    beq   t0, s5, .L_add_2
    beq   x0, x0, test_fail
.L_add_2:

    # Case 3.3: 2 + 3 = 5
    add   t0, s2, s3
    beq   t0, s5, .L_add_3
    beq   x0, x0, test_fail
.L_add_3:

    # Case 3.4: 5 + (-5) = 0
    sub   t1, x0, s5
    add   t0, s5, t1
    beq   t0, x0, .L_add_4
    beq   x0, x0, test_fail
.L_add_4:

    # Case 3.5: Wrap-around 0xFFFFFFFF + 1 = 0
    sub   t1, x0, s1
    add   t0, t1, s1
    beq   t0, x0, .L_add_5
    beq   x0, x0, test_fail
.L_add_5:

    # --------------------------------------------------------------------------
    # 4. Exhaustive Testing: SUB
    # --------------------------------------------------------------------------
    # Case 4.1: Identity 5 - 0 = 5
    sub   t0, s5, x0
    beq   t0, s5, .L_sub_1
    beq   x0, x0, test_fail
.L_sub_1:

    # Case 4.2: Self-subtraction 5 - 5 = 0
    sub   t0, s5, s5
    beq   t0, x0, .L_sub_2
    beq   x0, x0, test_fail
.L_sub_2:

    # Case 4.3: 5 - 2 = 3
    sub   t0, s5, s2
    beq   t0, s3, .L_sub_3
    beq   x0, x0, test_fail
.L_sub_3:

    # Case 4.4: Negative result 2 - 5 = -3
    sub   t0, s2, s5
    sub   t1, x0, s3
    beq   t0, t1, .L_sub_4
    beq   x0, x0, test_fail
.L_sub_4:

    # Case 4.5: (-2) - (-5) = 3
    sub   t1, x0, s2
    sub   t2, x0, s5
    sub   t0, t1, t2
    beq   t0, s3, .L_sub_5
    beq   x0, x0, test_fail
.L_sub_5:

    # --------------------------------------------------------------------------
    # 5. Exhaustive Testing: AND
    # --------------------------------------------------------------------------
    # Case 5.1: 5 AND 0 = 0
    and   t0, s5, x0
    beq   t0, x0, .L_and_1
    beq   x0, x0, test_fail
.L_and_1:

    # Case 5.2: Idempotence 5 AND 5 = 5
    and   t0, s5, s5
    beq   t0, s5, .L_and_2
    beq   x0, x0, test_fail
.L_and_2:

    # Case 5.3: 5 AND -1 (all ones) = 5
    sub   t1, x0, s1
    and   t0, s5, t1
    beq   t0, s5, .L_and_3
    beq   x0, x0, test_fail
.L_and_3:

    # Case 5.4: Disjoint bit patterns 1 AND 2 = 0
    and   t0, s1, s2
    beq   t0, x0, .L_and_4
    beq   x0, x0, test_fail
.L_and_4:

    # Case 5.5: 3 AND 1 = 1
    and   t0, s3, s1
    beq   t0, s1, .L_and_5
    beq   x0, x0, test_fail
.L_and_5:

    # Case 5.6: 3 AND 2 = 2
    and   t0, s3, s2
    beq   t0, s2, .L_and_6
    beq   x0, x0, test_fail
.L_and_6:

    # --------------------------------------------------------------------------
    # 6. Exhaustive Testing: OR
    # --------------------------------------------------------------------------
    # Case 6.1: 5 OR 0 = 5
    or    t0, s5, x0
    beq   t0, s5, .L_or_1
    beq   x0, x0, test_fail
.L_or_1:

    # Case 6.2: Idempotence 5 OR 5 = 5
    or    t0, s5, s5
    beq   t0, s5, .L_or_2
    beq   x0, x0, test_fail
.L_or_2:

    # Case 6.3: Bit combination 1 OR 2 = 3
    or    t0, s1, s2
    beq   t0, s3, .L_or_3
    beq   x0, x0, test_fail
.L_or_3:

    # Case 6.4: 5 OR -1 = -1
    sub   t1, x0, s1
    or    t0, s5, t1
    beq   t0, t1, .L_or_4
    beq   x0, x0, test_fail
.L_or_4:

    # --------------------------------------------------------------------------
    # 7. Exhaustive Testing: MUL
    # --------------------------------------------------------------------------
    # Case 7.1: 5 * 0 = 0
    mul   t0, s5, x0
    beq   t0, x0, .L_mul_1
    beq   x0, x0, test_fail
.L_mul_1:

    # Case 7.2: 5 * 1 = 5
    mul   t0, s5, s1
    beq   t0, s5, .L_mul_2
    beq   x0, x0, test_fail
.L_mul_2:

    # Case 7.3: 2 * 3 = 6
    mul   t0, s2, s3
    beq   t0, s6, .L_mul_3
    beq   x0, x0, test_fail
.L_mul_3:

    # Case 7.4: 2 * (-3) = -6
    sub   t1, x0, s3
    mul   t0, s2, t1
    sub   t2, x0, s6
    beq   t0, t2, .L_mul_4
    beq   x0, x0, test_fail
.L_mul_4:

    # Case 7.5: (-2) * (-3) = 6
    sub   t1, x0, s2
    sub   t2, x0, s3
    mul   t0, t1, t2
    beq   t0, s6, .L_mul_5
    beq   x0, x0, test_fail
.L_mul_5:

    # Case 7.6: Lower 32-bit truncation: (2^28) * 2 = 2^29
    lui   t1, 0x10000
    mul   t0, t1, s2
    lui   t2, 0x20000
    beq   t0, t2, .L_mul_6
    beq   x0, x0, test_fail
.L_mul_6:

    # --------------------------------------------------------------------------
    # 8. Exhaustive Testing: BEQ
    # --------------------------------------------------------------------------
    # Case 8.1: Branch taken when equal
    beq   s3, s3, .L_beq_1
    beq   x0, x0, test_fail
.L_beq_1:

    # Case 8.2: Branch not taken when unequal
    beq   s1, s2, test_fail

    # Case 8.3: Branch taken for x0 == x0
    beq   x0, x0, .L_beq_3
    beq   x0, x0, test_fail
.L_beq_3:

    # Case 8.4: Branch not taken for opposite signs
    sub   t0, x0, s1
    beq   t0, s1, test_fail

    # --------------------------------------------------------------------------
    # 9. Exhaustive Testing: BGE (Signed Comparison)
    # --------------------------------------------------------------------------
    # Case 9.1: 3 >= 2 (taken)
    bge   s3, s2, .L_bge_1
    beq   x0, x0, test_fail
.L_bge_1:

    # Case 9.2: 3 >= 3 (taken)
    bge   s3, s3, .L_bge_2
    beq   x0, x0, test_fail
.L_bge_2:

    # Case 9.3: 2 >= 3 (not taken)
    bge   s2, s3, test_fail

    # Case 9.4: Positive >= Negative: 1 >= -1 (taken)
    sub   t1, x0, s1
    bge   s1, t1, .L_bge_4
    beq   x0, x0, test_fail
.L_bge_4:

    # Case 9.5: Negative >= Positive: -1 >= 1 (not taken)
    bge   t1, s1, test_fail

    # Case 9.6: Negative >= More Negative: -2 >= -3 (taken)
    sub   t1, x0, s2
    sub   t2, x0, s3
    bge   t1, t2, .L_bge_6
    beq   x0, x0, test_fail
.L_bge_6:

    # Case 9.7: More Negative >= Less Negative: -3 >= -2 (not taken)
    bge   t2, t1, test_fail

    # Case 9.8: Equal negative: -2 >= -2 (taken)
    bge   t1, t1, .L_bge_8
    beq   x0, x0, test_fail
.L_bge_8:

    # --------------------------------------------------------------------------
    # 10. Exhaustive Testing: SW and LW
    # --------------------------------------------------------------------------
    # Load 4KB-aligned data address (scratch_mem has %lo == 0)
    lui   s7, %hi(scratch_mem)

    # Case 10.1: Store word and load back at offset 0
    sw    s5, 0(s7)
    lw    t0, 0(s7)
    beq   t0, s5, .L_mem_1
    beq   x0, x0, test_fail
.L_mem_1:

    # Case 10.2: Distinct words across positive offsets 4, 8, 12
    sw    s1, 4(s7)
    sw    s2, 8(s7)
    sw    s3, 12(s7)

    # Verify offset 0 remained intact
    lw    t0, 0(s7)
    beq   t0, s5, .L_mem_2
    beq   x0, x0, test_fail
.L_mem_2:

    # Verify offset 4
    lw    t0, 4(s7)
    beq   t0, s1, .L_mem_3
    beq   x0, x0, test_fail
.L_mem_3:

    # Verify offset 8
    lw    t0, 8(s7)
    beq   t0, s2, .L_mem_4
    beq   x0, x0, test_fail
.L_mem_4:

    # Verify offset 12
    lw    t0, 12(s7)
    beq   t0, s3, .L_mem_5
    beq   x0, x0, test_fail
.L_mem_5:

    # Case 10.3: Negative offset from advanced base register
    add   t1, s4, s4            # t1 = 8
    add   t1, t1, s4            # t1 = 12
    add   s8, s7, t1            # s8 = s7 + 12
    lw    t0, -8(s8)            # load from (s7 + 12) - 8 = s7 + 4
    beq   t0, s1, .L_mem_6
    beq   x0, x0, test_fail
.L_mem_6:

    # Case 10.4: Store and load zero
    sw    x0, 0(s7)
    lw    t0, 0(s7)
    beq   t0, x0, .L_mem_7
    beq   x0, x0, test_fail
.L_mem_7:

    # Case 10.5: Store and load all-ones (0xFFFFFFFF)
    sub   t1, x0, s1
    sw    t1, 0(s7)
    lw    t0, 0(s7)
    beq   t0, t1, .L_mem_8
    beq   x0, x0, test_fail
.L_mem_8:

    # --------------------------------------------------------------------------
    # 11. Exhaustive Testing: JALR
    # --------------------------------------------------------------------------
    # Case 11.1: Call subroutine, save return address into ra, execute, and return
    lui   s9, %hi(subroutine_target)
    add   a0, x0, x0            # reset a0 = 0
    jalr  ra, %lo(subroutine_target)(s9)
    # Check that subroutine modified a0 to 5 and returned here via JALR
    beq   a0, s5, .L_jalr_1
    beq   x0, x0, test_fail
.L_jalr_1:

    # Case 11.2: Call alternate entry point
    lui   s9, %hi(subroutine_entry2)
    add   a1, x0, x0            # reset a1 = 0
    jalr  ra, %lo(subroutine_entry2)(s9)
    beq   a1, s3, .L_jalr_2
    beq   x0, x0, test_fail
.L_jalr_2:

    # Case 11.3: Hardware clearing of target LSB ((addr + 1) & ~1 == addr)
    # Adding 1 sets bit 0; JALR must clear bit 0 and reach subroutine_target safely
    lui   s9, %hi(subroutine_target)
    add   t3, s9, s1            # t3 has bit 0 set
    add   a0, x0, x0            # reset a0 = 0
    jalr  ra, %lo(subroutine_target)(t3)
    beq   a0, s5, .L_jalr_3
    beq   x0, x0, test_fail
.L_jalr_3:

# ------------------------------------------------------------------------------
# Test Status Exit Handlers
# ------------------------------------------------------------------------------
test_pass:
    sltiu a0, x0, 1             # a0 = 1 indicates success
    beq   x0, x0, test_pass     # infinite halt loop

test_fail:
    add   a0, x0, x0            # a0 = 0 indicates failure
    sub   a1, x0, s1            # a1 = -1
    beq   x0, x0, test_fail     # infinite halt loop

# ------------------------------------------------------------------------------
# Data Section (4096-byte aligned so %lo is 0, avoiding ADDI address math)
# ------------------------------------------------------------------------------
.section .data
.balign 4096
scratch_mem:
    .word 0
    .word 0
    .word 0
    .word 0