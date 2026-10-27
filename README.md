# Intel 8008 for Ghidra

A SLEIGH processor module for the Intel 8008 (MCS-8, 1972): seven 8-bit registers (A B C D E H L) and the
memory operand M, 14-bit addresses, 8 input and 24 output ports, the carry/zero/sign/parity flip-flops and the
on-chip return stack. Instructions use the 8080-style mnemonics (`MOV A,B`, `ADI`, `JNZ`, ...) that Intel's later
manuals and the AS assembler (`cpu 8008new`) use.

Language ID: `8008:LE:16:default` (raw binaries only: there is no executable format for the 8008, so import
with the Raw Binary loader, pick this language and set the base address).

The module was contributed to Ghidra as pull request
[#8007](https://github.com/NationalSecurityAgency/ghidra/pull/8007) by Spiro Sekulovski (@spirosekulovski), based
on Ghidra's 8085 module. This repository is that module plus the Ghidra-Rare verification work: see
[GHIDRA-RARE.md](GHIDRA-RARE.md) for what was tested and the results, and [CREDITS.md](CREDITS.md) for the
provenance and the list of changes. Prebuilt zips for Ghidra 12.1.3, 12.1.4 and 12.2 are on the
[Releases](../../releases) page; to build it yourself, `GHIDRA_INSTALL_DIR=<ghidra> gradle buildExtension`, then
install the zip from `dist/` with File > Install Extensions.

## What the upstream README said, and what is true now

The pull request shipped no README and listed no limitations. Its source carried these open points, all
resolved:

| Upstream | Now |
|---|---|
| `# AC_flag = ??` (an auxiliary-carry flag in the carry macros) | the 8008 has no auxiliary carry; removed |
| parity flag used as an overflow flag by INR/DCR, never set by anything else | P is the even-parity flip-flop, set by every instruction that sets Z and S |
| ADC/SBB/ACI/SBI used the carry after overwriting it | fixed |
| 16-bit addresses and M | 14-bit addresses (the two high bits of address bytes are don't-care) and M = (H & 0x3f) << 8 \| L |
| unused 8080/8085 leftovers (BCD adjust, interrupt-mask pcodeops) | removed |

Remaining limitations: see "Known gaps" in GHIDRA-RARE.md (return stack overflow, interrupts, six undefined
opcodes).
