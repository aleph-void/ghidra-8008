#!/usr/bin/env python3
"""Compare the module's decode (DumpSlots output) with MAME unidasm (mame_stream.py output), slot by slot.

  compare.py <ghidra.txt> <mame.txt> [--show N]

MAME uses Intel's original 8008 mnemonics (LAB, ADM, JFC, ...), the module the 8080-style ones (MOV A,B,
ADD M, JNC, ...); the MAME text is translated by the manual's mapping into the module's dialect and compared
operand by operand.  Display-only difference: the module prints RST with the vector address (RST 0x18)
where MAME prints the 3-bit field (rst 03).  Exit status 1 when any bucket that is not explained is not empty.
"""
import re
import sys
from collections import Counter, defaultdict

REG = {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D', 'e': 'E', 'h': 'H', 'l': 'L', 'm': 'M'}
ALU = {'ad': 'ADD', 'ac': 'ADC', 'su': 'SUB', 'sb': 'SBB', 'nd': 'ANA', 'xr': 'XRA', 'or': 'ORA', 'cp': 'CMP'}
ALUI = {'adi': 'ADI', 'aci': 'ACI', 'sui': 'SUI', 'sbi': 'SBI', 'ndi': 'ANI', 'xri': 'XRI', 'ori': 'ORI', 'cpi': 'CPI'}
COND = {'c': ('NC', 'C'), 'z': ('NZ', 'Z'), 's': ('P', 'M'), 'p': ('PO', 'PE')}


def hexv(s):
    return int(s, 16)


def mame_canon(t):
    """MAME text -> (mnemonic, operands tuple) in the module's dialect, or None for illegal"""
    t = t.strip().lower()
    if t == 'illegal':
        return None
    parts = t.split()
    m = parts[0]
    arg = parts[1] if len(parts) > 1 else None
    if m == 'hlt':
        return ('HLT', ())
    if m in ('rlc', 'rrc', 'ral', 'rar', 'ret'):
        return (m.upper(), ())
    if m == 'rst':
        return ('RST', (hexv(arg),))
    if m == 'inp':
        return ('IN', (hexv(arg),))
    if m == 'out':
        return ('OUT', (hexv(arg),))
    if m in ('jmp', 'cal'):
        return ('JMP' if m == 'jmp' else 'CALL', (hexv(arg),))
    if m in ALUI:
        return (ALUI[m], (hexv(arg),))
    if len(m) == 3 and m[0] in 'jc' and m[1] in 'ft' and m[2] in COND:
        return (m[0].upper() + COND[m[2]][m[1] == 't'], (hexv(arg),))
    if len(m) == 3 and m[0] == 'r' and m[1] in 'ft' and m[2] in COND:
        return ('R' + COND[m[2]][m[1] == 't'], ())
    if len(m) == 3 and m[0] == 'l' and m[1] in REG and m[2] in REG:
        return ('MOV', (REG[m[1]], REG[m[2]]))
    if len(m) == 3 and m[0] == 'l' and m[1] in REG and m[2] == 'i':
        return ('MVI', (REG[m[1]], hexv(arg)))
    if len(m) == 3 and m[:2] in ('in', 'dc') and m[2] in REG:
        return ('INR' if m[:2] == 'in' else 'DCR', (REG[m[2]],))
    if len(m) == 3 and m[:2] in ALU and m[2] in REG:
        return (ALU[m[:2]], (REG[m[2]],))
    raise SystemExit(f'unmapped MAME text {t!r}')


def ghidra_canon(t):
    t = t.strip()
    if t == 'BAD':
        return None
    parts = t.split(None, 1)
    ops = []
    if len(parts) > 1:
        for o in parts[1].split(','):
            o = o.strip()
            ops.append(int(o, 16) if o.startswith('0x') else o)
    mn = parts[0]
    if mn == 'RST':
        ops = [ops[0] >> 3] if ops[0] % 8 == 0 else ops
    return (mn, tuple(ops))


def main():
    gh = [l.rstrip('\n').split(' ', 2) for l in open(sys.argv[1]) if not l.startswith('    ')]
    ma = [l.rstrip('\n').split(' ', 2) for l in open(sys.argv[2])]
    show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 5
    assert len(gh) == len(ma), (len(gh), len(ma))
    cnt = Counter()
    ex = defaultdict(list)
    for (i, gl, gt), (j, ml, mt) in zip(gh, ma):
        assert i == j
        g = ghidra_canon(gt)
        m = mame_canon(mt)
        if g is None and m is None:
            k = 'both invalid'
        elif g is None:
            k = 'MAME decodes, module rejects'
        elif m is None:
            k = 'module decodes, MAME rejects'
        elif int(gl) != int(ml):
            k = 'length differs'
        elif g == m:
            k = 'agree'
        else:
            k = 'text differs'
        cnt[k] += 1
        if len(ex[k]) < show:
            ex[k].append(f'slot {i}: module {gt!r}  MAME {mt!r}')
    tot = sum(cnt.values())
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f'   {k:32s} {v:8d}  ({100 * v / tot:.3f}%)')
        if k not in ('agree', 'both invalid'):
            for e in ex[k]:
                print('      ', e)
    bad = tot - cnt['agree'] - cnt['both invalid']
    print(f'   total {tot}, differences {bad}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
