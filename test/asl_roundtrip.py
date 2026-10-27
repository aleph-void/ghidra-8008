#!/usr/bin/env python3
"""Assemble the module's disassembly with the AS macro assembler (cpu 8008new, an independent
implementation of the manual's mnemonics) and require the original bytes back.

  asl_roundtrip.py <ghidra.txt> <corpus.bin> [slot-size]

Every slot the module decodes is turned into an assembler line (numbers as 0NNh; RST prints the vector
address, asl wants the 0-7 field), assembled in pieces and compared with the instruction bytes of the
slot (a 14-bit address operand compares only its low 14 bits, the top two bits are don't-care).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

ASL = os.environ.get('ASL') or shutil.which('asl') or os.path.expanduser('~/.cache/ghidra-rare-scratch/tools/asl/bin/asl')


DONTCARE = ('RET', 'JMP', 'CALL')


def to_asm(t):
    m = re.match(r'(\w+)\s*(.*)$', t)
    mn, ops = m.group(1), m.group(2)
    if mn == 'RST':
        ops = str(int(ops, 16) >> 3)
    else:
        ops = re.sub(r'0x([0-9a-fA-F]+)', lambda x: '0' + x.group(1) + 'h', ops)
    return f'\t{mn.lower()}\t{ops}'


def main():
    gh = [l.rstrip('\n').split(' ', 2) for l in open(sys.argv[1]) if not l.startswith('    ')]
    data = open(sys.argv[2], 'rb').read()
    slot = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    todo = [(int(i), int(n), t) for i, n, t in gh if t != 'BAD']
    tmp = tempfile.mkdtemp(prefix='aslrt.', dir=os.environ.get('TMPDIR', '/tmp'))
    cnt = Counter()
    shown = 0
    CH = 3000
    for c in range(0, len(todo), CH):
        part = todo[c:c + CH]
        src = os.path.join(tmp, 'p.asm')
        with open(src, 'w') as f:
            f.write('\tcpu 8008new\n')
            for _, _, t in part:
                f.write(to_asm(t) + '\n')
        r = subprocess.run([ASL, '-L', '-q', src], capture_output=True, text=True, cwd=tmp)
        lst = open(os.path.join(tmp, 'p.lst')).read().split('\n')
        got = {}
        for l in lst:
            m = re.match(r'\s*(\d+)/\s*[0-9A-F]+ : ((?:[0-9A-F]{2} )+)', l)
            if m:
                got.setdefault(int(m.group(1)), bytearray()).extend(bytes.fromhex(m.group(2).replace(' ', '')))
        for k, (i, n, t) in enumerate(part):
            want = bytearray(data[i * slot:i * slot + n])
            g = got.get(k + 2)       # line 1 is the cpu directive
            if g is None:
                cnt['asl rejects'] += 1
                if shown < 10:
                    print('   asl rejects', t); shown += 1
                continue
            g = bytearray(g)
            if len(want) == 3:
                want[2] &= 0x3f
                g[2] &= 0x3f
            if t == 'HLT' and bytes(want) in (b'\x00', b'\x01', b'\xff') and bytes(g) == b'\x00':
                cnt['identical'] += 1     # HLT has three encodings (00, 01, FF); asl emits 00
            elif t.split()[0] in DONTCARE and want[0] & 0xc7 == g[0] and want[1:] == bytearray(g[1:]):
                cnt['identical'] += 1     # RET 00xxx111, JMP 01xxx100, CALL 01xxx110: the x bits are don't-care
            elif bytes(g) == bytes(want):
                cnt['identical'] += 1
            else:
                cnt['different'] += 1
                if shown < 10:
                    print('   different', t, g.hex(), want.hex()); shown += 1
    shutil.rmtree(tmp)
    for k, v in cnt.items():
        print(f'   {k:12s} {v}')
    sys.exit(1 if cnt['asl rejects'] or cnt['different'] else 0)


if __name__ == '__main__':
    main()
