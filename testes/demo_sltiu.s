.globl _start
_start:
    sltiu t0, x0, -1        # t0 = (0 <u 0xFFFFFFFF) = 1
    sltiu t1, x0, 1         # t1 = (0 <u 1)          = 1
    sub   t2, x0, t1        # t2 = 0xFFFFFFFF
    sltiu t3, t2, 1         # t3 = (0xFFFFFFFF <u 1) = 0
    lui   t4, 0x80000       # t4 = 0x80000000
    sltiu t5, t4, 1         # t5 = (0x80000000 <u 1) = 0
halt:
    beq   x0, x0, halt
