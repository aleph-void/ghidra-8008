# Ghidra-Rare notes: Intel 8008

Verification of the community module from Ghidra pull request #8007 (see CREDITS.md). Language ID
`8008:LE:16:default`, 52 SLEIGH constructors, `8008.sla` about 4 KB. Builds and passes the suite on Ghidra
12.1.3, 12.1.4 and 12.2.

## How to test

```
GHIDRA_INSTALL_DIR=<scratch copy of a Ghidra 12.1.x/12.2 install> test/run-tests.sh [workdir] [--real]
```

The scratch install gets a symlink `Ghidra/Processors/8008` to this directory. Needs `unidasm` and `mame` (MAME
0.285), `asl`/`p2bin` (AS 1.42), Java 21+ (25 for Ghidra 12.2) and Python 3; the headless project path must not
contain a component starting with a dot. `--real` downloads two MIT-licensed programs (pinned commit + SHA-256 in
`test/real-binaries.sh`, never committed).

## Results

| Area | Result |
|---|---|
| Build | compiles on 12.1.3, 12.1.4, 12.2; release zips built with `tools/build-module.sh --standard --name I8008` |
| Decode vs MAME `unidasm -arch i8008` | 170,464 four-byte slots (every opcode with every second byte and eight third-byte values incl. the 14-bit address-mask cases, plus 100,000 random slots): 168,039 agree (mnemonic, operands, length), 2,425 both invalid (the six undefined opcodes), **0 differences** |
| Decode vs AS (`cpu 8008new`) | the module's disassembly of those 168,039 slots re-assembles with AS to the original bytes: 168,039/168,039 (don't-care bits in RET `00xxx111`, JMP `01xxx100`, CALL `01xxx110`, the two high bits of address bytes and the three HLT encodings are normalised) |
| Every constructor reached | 52/52 |
| P-code, hand-computed | 95 emulator cases from the datasheet (ALU flags incl. parity, carry/borrow chains, INR/DCR leaving carry, rotates, every jump/call/return condition, 14-bit M and address masking, RST vectors, IN/OUT, small programs); 2 deliberately wrong expectations are detected |
| P-code vs MAME's i8008 CPU core | 7,410 random single-instruction states (30 per defined opcode: random registers, flags, M, operands, return address): registers, flags, M, final PC and pushed return address identical, **7,410/7,410** (the original pull request: 5,066) |
| Real code | see below |

Real code, `test/real-binaries.sh` (all instruction counts compared three ways: against the AS listing, against an
independent flow walk over the opcode map, against MAME and AS):

| Program | Result |
|---|---|
| Jim Loos's SBC monitor (`monitor.asm`, MIT, assembled with AS at 0x2000) | 934 instructions in the listing; linear disassembly identical on all 934 (one extra `HLT` at the zero fill after `rst 1`); flow analysis from the entry point reaches 788 instructions (the other 146 are routines the source never calls; an opcode-map flow walk reaches exactly the same 788), 26 functions, 21/21 decompile |
| Tiny BASIC by Paul Robson (`basic.asm`, MIT; our AS build is byte-identical to the author's `basic.bin`) | 482 instructions identical to the listing; flow analysis finds all 482 (+1 zero-fill `HLT`), 16 functions, 16/16 decompile |
| `monitor.bin` shipped in the monitor repository (its source is a different revision from `monitor.asm`) | flow analysis: 788 instructions, 26 functions, 21/21 decompile; all instructions agree with MAME and re-assemble with AS |
| Error bookmarks | 4 (monitor), 1 (BASIC), 3 (shipped monitor.bin): all are jumps into RAM (the monitor writes a `jmp` into RAM at 0x1FFC and runs it; BASIC calls a RAM routine at 0x1200): "flow into non-existing memory" is correct for a raw image |
| Bad-instruction bookmarks | 0 |

Before and after (same tests against the pull request as imported): decode differences from MAME 42,032 of 170,464
(the `HALT` spelling and 16-bit addresses); emulator cases failing 30 of 95; MAME state differential failing 2,344
of 7,410. The module's opcode map itself was right; the flags, ADC/SBB, M and address width were not.

## What works

Every defined opcode: moves, INR/DCR, the eight ALU operations in register, M and immediate forms (all four
flip-flops, borrow carry, parity as even parity), rotates, JMP/Jcc/CALL/Ccc/RET/Rcc/RST with 14-bit targets,
IN 0-7 and OUT 8-31 (I/O space), HLT. P-code for all of it. A 7-entry-deep return stack that the decompiler hides.
Decompiles real programs (no failures in 58 decompiled functions).

## Doesn't work (and why)

- **Return stack overflow.** The chip keeps eight 14-bit stack registers; an eighth nested CALL overwrites the
  oldest return address. The module models an ordinary downward stack in 0xFFF0-0xFFFF (outside the 14-bit address
  space) instead. P-code can express the ring, but the masked address arithmetic defeats the decompiler's stack
  analysis and leaves a store `uMemfffe = ...;` before every call, so it was not done (tried). Correct programs never nest more than seven deep.
- **Interrupts and READY/wait states.** An interrupt is an externally injected `RST` (it works as `RST n`); HLT
  stays in a self-jump instead of waiting for it. Hardware.
- **Six undefined opcodes** (0x22, 0x2A, 0x32, 0x38, 0x39, 0x3A) are not decoded. The datasheet leaves them
  undefined; MAME's disassembler prints `illegal` while its CPU core executes arbitrary behaviour, so they are
  excluded from the state differential.
- **Address wrap at 0x4000.** Fall-through past 0x3FFF would wrap to 0 on the chip; Ghidra continues at 0x4000.
- Raw binaries only: the 8008 has no executable format (no ELF machine number), so there is no loader or ELF
  opinion.

## Unverified

Behaviour on physical hardware (the oracles are the datasheet, MAME and AS); carry reset by AND/XOR/OR is from the
MCS-8 manual and MAME's core, the datasheet page only says "all flip-flops" for ALU operations; I/O port values
(MAME's `mod8` driver does not provide IN data, so `IN` results are checked only by hand-computed cases).

## Confirmed bugs in reference tools

None found. (AS `hlt` always assembles to `00` although `01` and `FF` are the same instruction; that is not a
bug. The `maly/8008` JavaScript simulator was examined and rejected as an oracle, see CREDITS.md.)
