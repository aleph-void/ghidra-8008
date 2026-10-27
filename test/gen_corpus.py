#!/usr/bin/env python3
"""Corpus of 4-byte slots for the Intel 8008 decode differential.

  gen_corpus.py <out.bin> [random-slots] [seed]

* every opcode with every second byte (and several third bytes: the 14-bit address mask cases)
* random bytes after instructions shorter than the slot
* random slots
"""
import random
import sys

out = sys.argv[1]
nrand = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)


def length(op):
    if op < 0x40 and (op & 7) in (4, 6):
        return 2
    if 0x40 <= op < 0x80 and (op & 1) == 0:
        return 3
    return 1


slots = []
for op in range(256):
    n = length(op)
    if n == 3:
        for b1 in range(256):
            for b2 in (0x00, 0x01, 0x2a, 0x3f, 0x40, 0x80, 0xc0, 0xff):
                slots.append(bytes([op, b1, b2, rnd.randrange(256)]))
    elif n == 2:
        for b1 in range(256):
            slots.append(bytes([op, b1, rnd.randrange(256), rnd.randrange(256)]))
    else:
        for _ in range(4):
            slots.append(bytes([op]) + bytes(rnd.randrange(256) for _ in range(3)))
for _ in range(nrand):
    slots.append(bytes(rnd.randrange(256) for _ in range(4)))
open(out, 'wb').write(b''.join(slots))
print(len(slots), 'slots')
