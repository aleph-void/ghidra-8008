#!/usr/bin/env python3
"""Compare a Ghidra listing of a real program with the AS assembler listing of its source.

  real_compare.py [--linear] <image.bin> <base-hex> <entries-file> <ghidra-listing.txt> <corpus-prefix> [asl.lst]

* image.bin, base: the program image and its load address
* entries-file: lines "<name> <hex address>", the addresses disassembly started from
* ghidra-listing.txt: RealCheck output, "<hex addr> <len> <text>" per instruction
* asl.lst: optional, the listing AS wrote for the source (instructions with addresses and bytes)
* Writes <corpus-prefix>.bin / .gh.txt, a slot corpus of the instructions Ghidra produced and the matching
  module decode, for mame_stream.py + compare.py / asl_roundtrip.py.

Two checks: (1) the module's instructions are exactly the ones an independent flow walk over the opcode map
reaches from the same entries; (2) each of them has the address, length and bytes of the assembler listing
(--linear: every listed instruction must also have been produced).
"""
import re
import sys

INSN = set('''mov mvi inr dcr add adc sub sbb ana xra ora cmp adi aci sui sbi ani xri ori cpi rlc rrc ral rar jmp jnc jc jnz jz jp jm
jpo jpe call cnc cc cnz cz cp cm cpo cpe ret rnc rc rnz rz rp rm rpo rpe rst in out hlt nop
lai lbi lci ldi lei lhi lli lmi'''.split())
ROW = re.compile(r'^\s*\d+/\s*([0-9A-Fa-f]+) : ((?:[0-9A-F]{2} )+)\s*(.*)$')


def asl_instructions(path):
    out = {}
    for l in open(path, errors='replace'):
        m = ROW.match(l.rstrip('\n'))
        if not m:
            continue
        addr = int(m.group(1), 16)
        b = bytes.fromhex(m.group(2).replace(' ', ''))
        src = re.sub(r';.*', '', m.group(3)).strip()
        src = re.sub(r'^\w+:\s*', '', src)
        mn = src.split()[0].lower() if src.split() else ''
        if mn in INSN:
            out[addr] = b
    return out


def length(op):
    if op < 0x40 and (op & 7) in (4, 6):
        return 2
    if 0x40 <= op < 0x80 and (op & 1) == 0:
        return 3
    return 1


def ref_flow(data, base, entries):
    """Independent reference flow: the instruction addresses reachable from the entry points when following
    fall-through, jumps, calls and RSTs, using only the opcode map (no SLEIGH)."""
    seen, todo = {}, list(entries)
    while todo:
        a = todo.pop()
        if a in seen or not (base <= a < base + len(data)):
            continue
        op = data[a - base]
        n = length(op)
        if a - base + n > len(data):
            continue
        seen[a] = n
        nxt = a + n
        tgt = (data[a - base + 1] | (data[a - base + 2] << 8)) & 0x3fff if n == 3 else None
        if op in (0x00, 0x01, 0xff):
            continue
        if op < 0x40 and (op & 7) == 7:        # RET
            continue
        if 0x40 <= op < 0x80 and (op & 7) == 4:  # JMP
            todo.append(tgt)
            continue
        if 0x40 <= op < 0x80 and (op & 7) in (0, 2, 6):   # Jcc, Ccc, CALL
            todo.append(tgt)
        if op < 0x40 and (op & 7) == 5:        # RST
            todo.append(op & 0x38)
        todo.append(nxt)
    return seen


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    image, base, entries, gl, prefix = args[:5]
    lst = args[5] if len(args) > 5 else None
    base = int(base, 16)
    data = open(image, 'rb').read()
    ents = [int(x.split()[1], 16) for x in open(entries) if x.strip()]
    gh = []
    for l in open(gl):
        a, n, t = l.rstrip('\n').split(' ', 2)
        gh.append((int(a, 16), int(n), t))
    bad = 0
    # 1. the instructions the module produced are exactly those an opcode-map flow walk reaches
    ref = ref_flow(data, base, ents)
    mod = {a: n for a, n, _ in gh}
    only_m = sorted(a for a in mod if a not in ref or ref[a] != mod[a])
    only_r = sorted(a for a in ref if a not in mod)
    print(f'   reference flow walk from {len(ents)} entries: {len(ref)} instructions, module {len(mod)}; '
          f'module-only {len(only_m)}, reference-only {len(only_r)}')
    for a in (only_m + only_r)[:10]:
        print(f'   difference at {a:04x}')
    bad += len(only_m) + len(only_r)
    # 2. against the assembler listing of the source
    if lst:
        asl = asl_instructions(lst)
        same = 0
        extra = []
        for a, n, t in gh:
            want = asl.get(a)
            if want is not None and want == data[a - base:a - base + n]:
                same += 1
            else:
                extra.append((a, n, t))
        unlisted = [a for a in asl if a not in mod]
        print(f'   assembler listing: {len(asl)} instructions, identical in the module {same}, '
              f'module instructions not in the listing {len(extra)}, listing instructions not reached {len(unlisted)}')
        for a, n, t in extra[:10]:
            ok = t == 'HLT' and data[a - base] == 0
            print(f'   not in the listing: {a:04x} {t!r}' + ('  (zero fill after a call / RST falls through)' if ok else ''))
            if not ok:
                bad += 1
        if '--linear' in sys.argv:
            bad += len(unlisted)
    with open(prefix + '.bin', 'wb') as cb, open(prefix + '.gh.txt', 'w') as gt:
        for i, (a, n, t) in enumerate(gh):
            cb.write((data[a - base:a - base + 4] + b'\xc0\xc0\xc0\xc0')[:4])
            gt.write(f'{i} {n} {t}\n')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
