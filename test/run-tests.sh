#!/usr/bin/env bash
# Intel 8008 module test suite: everything that needs no downloaded inputs.
#
#   GHIDRA_INSTALL_DIR=<scratch Ghidra 12.1.x> test/run-tests.sh [workdir] [--real]
#
# 1. the spec compiles (.sla well under 16 MB)
# 2. decode differential against MAME unidasm (-arch i8008) on every opcode with every operand byte and on
#    random words, and AS (cpu 8008new, an independent assembler) re-assembling the module's disassembly to
#    the original bytes
# 3. every SLEIGH constructor is reached by those corpora
# 4. p-code: hand-computed emulator tests (EmuCheck.java), including deliberately wrong expectations that
#    must be reported
#    4b (needs mame): the mod8 driver's Intel 8008 core run as a black box on 7,000+ random single-instruction
#    states (registers, flags, M, branches, calls, returns) must end in the same state as the module's p-code
# --real adds step 5: the Jim Loos serial monitor and the paulscottrobson Tiny BASIC (MIT; fetched by pinned
#    commit and SHA-256), assembled with AS, analysed, decompiled and compared with MAME and AS
#    (test/real-binaries.sh).
#
# Environment: GHIDRA_INSTALL_DIR (a scratch copy of Ghidra 12.1.x; the module is symlinked into its
# Ghidra/Processors/8008), JAVA_HOME (optional), UNIDASM (MAME's unidasm), ASL / P2BIN (macro assembler AS),
# PROJ_DIR (where headless Ghidra projects are created; the path must not contain a component that starts
# with a dot).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
MOD=$(cd "$HERE/.." && pwd)
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR to a scratch Ghidra 12.1.x}"
REAL=0
ARGS=()
for a in "$@"; do if [[ $a == --real ]]; then REAL=1; else ARGS+=("$a"); fi; done
W=$(readlink -m "${ARGS[0]:-${TMPDIR:-/tmp}/i8008-tests}")
mkdir -p "$W"
export TMPDIR=$W
export PROJ_DIR=${PROJ_DIR:-$W}
UNIDASM=${UNIDASM:-$(command -v unidasm || true)}
: "${ASL:=$(command -v asl || echo "$HOME/.cache/ghidra-rare-scratch/tools/asl/bin/asl")}"
: "${P2BIN:=$(command -v p2bin || echo "$HOME/.cache/ghidra-rare-scratch/tools/asl/bin/p2bin")}"
export ASL P2BIN UNIDASM GHIDRA_INSTALL_DIR
fail=0
LANGID=8008:LE:16:default

echo "== 1. SLEIGH compiles"
"$GHIDRA_INSTALL_DIR/support/sleigh" "$MOD/data/languages/8008.slaspec" 2>&1 | grep -E "^ERROR|^Error" && exit 1 || true
sz=$(stat -c %s "$MOD/data/languages/8008.sla")
echo "   8008.sla: $sz bytes"
((sz < 16 * 1024 * 1024))
P="$GHIDRA_INSTALL_DIR/Ghidra/Processors/8008"
if [[ ! -e $P ]]; then ln -s "$MOD" "$P"; elif [[ $(readlink -f "$P") != "$MOD" ]]; then
	echo "warning: $P exists and is not this module" >&2; fi

python3 "$HERE/gen_corpus.py" "$W/all.bin" 100000 7
echo "== 2. decode differential"
"$HERE/decode-corpus.sh" $LANGID "$W/all.bin" "$W/gh.txt" 4
if [[ -n $UNIDASM ]]; then
	echo "   against MAME unidasm"
	python3 "$HERE/mame_stream.py" i8008 "$W/all.bin" "$W/mame.txt" 4 c0
	python3 "$HERE/compare.py" "$W/gh.txt" "$W/mame.txt" --show 8 | tee "$W/compare.txt" || fail=1
else
	echo "   (skipped: no unidasm)"
fi
if [[ -x $ASL || -n $(command -v "$ASL" || true) ]]; then
	echo "   AS re-assembles the disassembly to the original bytes"
	python3 "$HERE/asl_roundtrip.py" "$W/gh.txt" "$W/all.bin" 4 || fail=1
else
	echo "   (skipped: no asl)"
fi

echo "== 3. every constructor is reached"
"$HERE/decode-corpus.sh" $LANGID "$W/all.bin" "$W/reach.txt" 4 Reach.java
python3 "$HERE/reach_check.py" "$MOD/data/languages/8008.slaspec" "$W/reach.txt" || fail=1

echo "== 4. p-code: emulator tests"
mkdir -p "$W/emu"
python3 "$HERE/emu_tests.py" "$W/emu"
"$HERE/ghidra-script.sh" raw $LANGID "$W/emu/emu.bin" EmuCheck.java "$W/emu/tests.txt" "$W/emu/out.txt"
echo "   $(tail -1 "$W/emu/out.txt")"
grep -q " 0 failed" "$W/emu/out.txt" || { grep -v "^PASS" "$W/emu/out.txt" | head -20; fail=1; }
grep -q "[1-9][0-9]* broken expectations detected" "$W/emu/out.txt" || { echo "   the deliberately wrong expectations were not detected"; fail=1; }

if command -v mame >/dev/null; then
	echo "== 4b. random single instructions against MAME's i8008 core (state differential)"
	EMU_BIN="$W/emu/emu.bin" "$HERE/mame/run-mame-sem.sh" "$W/sem" 30 || fail=1
else
	echo "== 4b. skipped (no mame)"
fi

if ((REAL)); then
	echo "== 5. real code"
	"$HERE/real-binaries.sh" "$W/real" || fail=1
fi

if ((fail)); then echo "FAILED"; exit 1; fi
echo "all tests passed"
