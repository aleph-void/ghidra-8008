#!/usr/bin/env python3
"""Random single-instruction tests for the MAME semantic differential.

  sem_gen.py gen <in.txt> [tests-per-opcode] [seed]      -> input for mame/mame_sem.lua
  sem_gen.py tests <in.txt> <mame-out.txt> <tests.txt>   -> EmuCheck input (Ghidra emulator runs the same tests)

Each test: random registers, flags (the four flip-flops are independent), the byte M points at (inside the RAM
the mod8 driver has at 0x800-0xbff), operand bytes, and for RET a return address on the stack.  MAME's final
state (registers, flags, M, program counter, pushed return address) is the expectation for the module.
"""
import random
import sys

NAMES = {}


def length(op):
    if op < 0x40 and (op & 7) in (4, 6):
        return 2
    if 0x40 <= op < 0x80 and (op & 1) == 0:
        return 3
    return 1


def gen(path, per, seed):
    rnd = random.Random(seed)
    out = open(path, 'w')
    tid = 0
    for op in range(256):
        if op in (0x00, 0x01, 0xff):       # HLT: the CPU stays on the instruction
            continue
        if op in (0x22, 0x2a, 0x32, 0x38, 0x39, 0x3a):    # undefined opcodes: MAME's core does something arbitrary
            continue
        for _ in range(per):
            regs = [rnd.randrange(256) for _ in range(5)]
            h = (rnd.randrange(4) << 6) | (8 + rnd.randrange(4))
            l = rnd.randrange(256)
            fl = [rnd.randrange(2) for _ in range(4)]
            mb = rnd.randrange(256)
            b1, b2 = rnd.randrange(256), rnd.randrange(256)
            if length(op) == 3:
                while (b1 | (b2 << 8)) & 0x3fff in range(0x100, 0x104):
                    b1 = rnd.randrange(256)
            pos, a0 = 0, 0
            if op < 0x40 and (op & 7) == 7 or (op < 0x40 and (op & 7) == 3):    # RET, Rcc
                pos, a0 = 1, rnd.randrange(0x4000)
                while a0 in range(0x100, 0x104):
                    a0 = rnd.randrange(0x4000)
            tid += 1
            out.write(' '.join(map(str, [tid] + regs + [h, l] + fl + [pos, a0, 0, mb, op, b1, b2])) + '\n')
    out.close()
    print(tid, 'tests')


def tests(inp, mout, outp):
    ins = {}
    for l in open(inp):
        v = list(map(int, l.split()))
        ins[v[0]] = v
    n = skipped = 0
    with open(outp, 'w') as o:
        for l in open(mout):
            r = list(map(int, l.split()))
            v = ins[r[0]]
            tid, regs_in = v[0], v[1:8]
            cf, zf, sf, pf, pos, a0, a1, mb, op, b1, b2 = v[8:19]
            _, A, B, C, D, E, H, L, ccf, czf, csf, cpf, halt, pc, rpos, ra0, ra1, rmb = r
            if not halt:
                skipped += 1
                continue
            L_ = length(op)
            insn = [op, b1, b2][:L_]
            maddr = ((regs_in[5] & 0x3f) << 8) | regs_in[6]
            init = [f'A={regs_in[0]:x}', f'B={regs_in[1]:x}', f'C={regs_in[2]:x}', f'D={regs_in[3]:x}', f'E={regs_in[4]:x}',
                    f'H={regs_in[5]:x}', f'L={regs_in[6]:x}', f'CY_flag={cf}', f'Z_flag={zf}', f'S_flag={sf}', f'P_flag={pf}',
                    f'm{L_}:100=' + ''.join(f'{b:02x}' for b in insn), f'm1:{maddr:x}={mb:x}']
            exp = [f'B={B:x}', f'C={C:x}', f'D={D:x}', f'E={E:x}', f'H={H:x}', f'L={L:x}', f'CY_flag={ccf}', f'Z_flag={czf}',
                   f'S_flag={csf}', f'P_flag={cpf}', f'm1:{maddr:x}={rmb:x}']
            if not (0x40 <= op < 0x50 and op & 1):     # IN reads a port the mod8 driver does not define: skip A there
                exp.append(f'A={A:x}')
            if op < 0x40 and (op & 7) in (3, 7):       # RET / Rcc
                init += ['SP=fffe', f'n2:fffe={a0:x}']
                exp += [f'SP={0:x}' if rpos == 0 else 'SP=fffe']
            elif 0x40 <= op < 0x80 and (op & 7) in (2, 6) or (op < 0x40 and (op & 7) == 5):  # CALL, Ccc, RST
                init += ['SP=0']
                if rpos == 1:
                    exp += ['SP=fffe', f'n2:fffe={ra0:x}']
                else:
                    exp += ['SP=0']
            name = f'sem_{tid:05d}_op{op:02x}'
            o.write(f'{name} 100 {pc:x} {",".join(init)} {",".join(exp)}\n')
            n += 1
    print(n, 'tests written,', skipped, 'skipped (no halt)')


if __name__ == '__main__':
    if sys.argv[1] == 'gen':
        gen(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30, int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    else:
        tests(sys.argv[2], sys.argv[3], sys.argv[4])
