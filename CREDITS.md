# Credits and provenance: Intel 8008 module

## Upstream

| | |
|---|---|
| Source | Ghidra pull request [#8007](https://github.com/NationalSecurityAgency/ghidra/pull/8007), "Add support for Intel 8008 processor" (still open when imported), head `6e3d6e64b6bab9d6ec0ab44ce5fe378f16a47c45`, files under `Ghidra/Processors/8008` |
| Ghidra-Rare fork | branch `ghidra-rare` of the aleph-void fork; the first commit is the pull request head, unchanged |
| License | Apache-2.0 (a Ghidra contribution; `LICENSE` holds the Apache-2.0 text, `LICENSE.txt` is the upstream stub, unchanged) |
| Original author | Spiro Sekulovski (GitHub @spirosekulovski; the pull request's only commit is by "Spiro Sekulovski") |
| Based on | Ghidra's 8085 processor module (NSA, Apache-2.0), which the pull request names as its template |

The pull request says: "I used the 8085 processor config files as a template."

## Other implementations

A search on GitHub (`ghidra 8008`, `8008 sleigh`, `ghidra intel 8008`) found no other Ghidra module for the 8008.
No code was borrowed from elsewhere.

## Ghidra-Rare changes

1. **Semantics rewritten** (`aec7b25`): parity, carry/borrow, ADC/SBB ordering, INR/DCR, rotates and logical
   operations follow the datasheet; M and branch targets are 14 bits; `HLT` spelling; return stack declared so the
   decompiler hides it; invented default memory symbols removed; OUT port block size fixed; calling-convention
   arguments A-E. The decode (opcode map) of the pull request was kept: it already agreed with MAME.
2. **Notes, tests and build files**: `GHIDRA-RARE.md`, `README.md`, `LICENSE`, `build.gradle`,
   `extension.properties`, `.gitignore` and `test/` (decode differentials against MAME and AS, constructor
   coverage, emulator suite, random-state differential against MAME's i8008 core, real-code run).

## Sources and reference tools

Used as facts, black boxes or test inputs; nothing copied into the module:

- Intel 8008 / 8008-1 datasheet, instruction set pages (MCS-8/MCS-85 data book pp. 9-7, 9-8), as included in the
  documentation folder of paulscottrobson/1k-coding-challenge: instruction codes, flag rules, 14-bit addresses.
  Not redistributed.
- MAME (GPL/BSD) `unidasm -arch i8008` and the `i8008` CPU core, run as black boxes through the `mod8` driver.
- The AS macro assembler (GPL-2.0), `cpu 8008new`, as an independent assembler.
- Real code (MIT, fetched by pinned commit and SHA-256, never committed): Jim Loos's 8008 SBC serial monitor
  (jim11662418/Intel_8008_Single_Board_Computer, commit `1a36b57d8e1e3fb6480b5da75dc098e4de1c4afb`) and the Tiny
  BASIC of Paul Robson (paulscottrobson/1k-coding-challenge, commit `996fd54bc665d1499838bf431e1540aa06c2177e`).
- maly/8008 (MIT, a JavaScript simulator) was looked at as a possible behavioural oracle and rejected: its
  condition-code test never checks the sign flip-flop, among other errors. Nothing was taken from it.
