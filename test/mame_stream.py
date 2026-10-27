#!/usr/bin/env python3
"""Disassemble a corpus of fixed-size slots with MAME's unidasm, in one process, at the slot's own address.

  mame_stream.py <arch> <corpus.bin> <out.txt> [slot-size] [fill-byte-hex]

The first byte of an instruction fixes its length for the CPUs this is used on, so each slot's instruction
bytes are laid out at offset slot*N of a stream and the gap up to the next slot is filled with a harmless
one-byte opcode (fill-byte), then unidasm decodes the whole stream once (pc-relative operands are then
computed at the slot address, as in Ghidra).  Lines that start inside a gap are ignored.
Output: one line per slot, "<index> <length> <text>" (length = number of raw bytes MAME printed,
0 for a line MAME refused).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

UNIDASM = os.environ.get('UNIDASM', shutil.which('unidasm') or 'unidasm')
LINE = re.compile(r'^([0-9a-f]+):\s+((?:[0-9a-f]{2}\s)+)\s*(.*)$')


def run(arch, path, count, basepc=0):
    r = subprocess.run([UNIDASM, path, '-arch', arch, '-basepc', format(basepc, 'x'), '-count', str(count)],
                       capture_output=True, text=True)
    return r.stdout.split('\n')


def lengths(arch, slot, tmp):
    """instruction length (bytes MAME prints) by first byte"""
    out = []
    for op in range(256):
        p = os.path.join(tmp, 'p.bin')
        open(p, 'wb').write(bytes([op]) + b'\x00' * (slot + 4))
        ln = run(arch, p, 1)[0]
        m = LINE.match(ln)
        if not m:
            raise SystemExit(f'cannot parse {ln!r}')
        out.append(len(m.group(2).split()))
    return out


def main():
    arch, corpus, outf = sys.argv[1:4]
    slot = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    fill = int(sys.argv[5], 16) if len(sys.argv) > 5 else 0
    data = open(corpus, 'rb').read()
    n = len(data) // slot
    tmp = tempfile.mkdtemp(prefix='mame-stream.', dir=os.environ.get('TMPDIR', '/tmp'))
    ln = lengths(arch, slot, tmp)
    stream = bytearray()
    for i in range(n):
        s = data[i * slot:(i + 1) * slot]
        k = min(ln[s[0]], slot)
        stream += s[:k] + bytes([fill]) * (slot - k)
    p = os.path.join(tmp, 'stream.bin')
    open(p, 'wb').write(stream)
    res = {}
    lines = run(arch, p, len(stream))
    for l in lines:
        m = LINE.match(l)
        if not m:
            continue
        a = int(m.group(1), 16)
        if a % slot == 0 and a // slot < n:
            res[a // slot] = (len(m.group(2).split()), m.group(3).strip())
    with open(outf, 'w') as o:
        for i in range(n):
            k, t = res.get(i, (0, 'MISSING'))
            o.write(f'{i} {k} {t}\n')
    shutil.rmtree(tmp)


if __name__ == '__main__':
    main()
