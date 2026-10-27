#!/usr/bin/env bash
# Real-code run for the Intel 8008 module.  Two freely licensed (MIT) programs, fetched by pinned commit and
# SHA-256 and never committed:
#   * the 8008 SBC serial monitor by Jim Loos (jim11662418/Intel_8008_Single_Board_Computer, monitor.asm),
#     assembled here with AS, and the monitor.bin shipped in that repository
#   * the Tiny BASIC of paulscottrobson/1k-coding-challenge (basic/basic.asm, basic.bin and the AS listing)
# For each program: linear check (every instruction of the assembler listing is disassembled and must agree with the
# listing in address, length and bytes), flow analysis from the entry points with function creation and
# decompilation, MAME and AS comparison of every instruction the module produced.
#   test/real-binaries.sh <workdir>
# Needs: asl + p2bin, unidasm, GHIDRA_INSTALL_DIR with this module (analyzeHeadless).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=$(readlink -m "${1:?workdir}")
mkdir -p "$W/dl" "$W/mon" "$W/tb"
: "${ASL:=$(command -v asl || echo "$HOME/.cache/ghidra-rare-scratch/tools/asl/bin/asl")}"
: "${P2BIN:=$(command -v p2bin || echo "$HOME/.cache/ghidra-rare-scratch/tools/asl/bin/p2bin")}"
: "${UNIDASM:=$(command -v unidasm || true)}"
export ASL P2BIN UNIDASM
LANGID=8008:LE:16:default
JIM=1a36b57d8e1e3fb6480b5da75dc098e4de1c4afb
PSR=996fd54bc665d1499838bf431e1540aa06c2177e
fetch() { # <url> <file> <sha256>
	[[ -f $2 ]] || curl -sSL -o "$2" "$1"
	echo "$3  $2" | sha256sum -c - >/dev/null || { echo "checksum mismatch: $2" >&2; exit 1; }
}
fetch "https://raw.githubusercontent.com/jim11662418/Intel_8008_Single_Board_Computer/$JIM/monitor.asm" "$W/dl/monitor.asm" 48e736830ec8177f8e374b0b3f4f4e4e3a20bd80f5e4e156e793f6c19e1d5dff
fetch "https://raw.githubusercontent.com/jim11662418/Intel_8008_Single_Board_Computer/$JIM/monitor.bin" "$W/dl/monitor.bin" 61e26f1b04e5fb035f54caa66b986d054884991604f38e6f026403e86eb3f080
fetch "https://raw.githubusercontent.com/paulscottrobson/1k-coding-challenge/$PSR/basic/basic.asm" "$W/dl/basic.asm" 20b53d4ad4ea67011939cb6047ae091bddb6e1f5a3c33e5687cbc0da8120f4f2
fetch "https://raw.githubusercontent.com/paulscottrobson/1k-coding-challenge/$PSR/basic/basic.bin" "$W/dl/basic.bin" 7bc8c30b006281a63d868d79da6f7fbf5ea7ac3bdf7a45633a1431a568151bef

fail=0
# <name> <asm file> <asm dir> <base> <p2bin range> <entry address> [shipped image]
run() {
	local name=$1 asm=$2 base=$3 range=$4 entry=$5
	local D=$W/$name
	mkdir -p "$D"
	echo "== $name: assemble with AS"
	(cd "$D" && cp "$asm" prog.asm && cp "$HERE/real/bitfuncs.inc" . && "$ASL" -i . -L -q prog.asm >asl.out 2>&1 || { tail asl.out; exit 1; }
	 "$P2BIN" prog.p prog.bin -r "$range" -l 0 >/dev/null)
	python3 - "$D/prog.lst" >"$D/entries.all" <<'PY'
import sys
sys.path.insert(0, '.')
import importlib.util, os
spec = importlib.util.spec_from_file_location('rc', os.path.join(os.environ['HERE'], 'real_compare.py'))
rc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rc)
for a in sorted(rc.asl_instructions(sys.argv[1])):
    print(f'i{a:04x} {a:x}')
PY
	echo "   $(wc -l <"$D/entries.all") instructions in the listing"
	echo "== $name: linear disassembly of every listed instruction"
	BASE_ADDR=$base "$HERE/ghidra-script.sh" raw $LANGID "$D/prog.bin" RealCheck.java "$D/lin.sum" "$D/lin.lst" 0 "$D/entries.all"
	grep -E "^(instructions|functions|bookmark)" "$D/lin.sum" | sed 's/^/   /'
	python3 "$HERE/real_compare.py" --linear "$D/prog.bin" "$base" "$D/entries.all" "$D/lin.lst" "$D/lin" "$D/prog.lst" || fail=1
	echo "== $name: flow analysis from the entry point, functions, decompiler"
	echo "start $entry" >"$D/entries.flow"
	BASE_ADDR=$base "$HERE/ghidra-script.sh" raw $LANGID "$D/prog.bin" RealCheck.java "$D/flow.sum" "$D/flow.lst" 400 "$D/entries.flow" analyze
	grep -vE "^(language|executable|blocks)" "$D/flow.sum" | sed 's/^/   /'
	python3 "$HERE/real_compare.py" "$D/prog.bin" "$base" "$D/entries.flow" "$D/flow.lst" "$D/flow" "$D/prog.lst" || fail=1
	grep -q "failed 0 " "$D/flow.sum" || { echo "   decompile failures"; fail=1; }
	if [[ -n $UNIDASM ]]; then
		echo "== $name: MAME and AS comparison of the module's instructions"
		for p in lin flow; do
			python3 "$HERE/mame_stream.py" i8008 "$D/$p.bin" "$D/$p.mame.txt" 4 c0
			python3 "$HERE/compare.py" "$D/$p.gh.txt" "$D/$p.mame.txt" | sed "s/^/   [$p] /" || fail=1
			python3 "$HERE/asl_roundtrip.py" "$D/$p.gh.txt" "$D/$p.bin" 4 | sed "s/^/   [$p] /" || fail=1
		done
	fi
}
export HERE
run monitor "$W/dl/monitor.asm" 0x2000 0x2000-0x3fff 2008
run basic "$W/dl/basic.asm" 0 0-2048 0

echo "== shipped monitor.bin (its source differs from monitor.asm): flow analysis and MAME / AS comparison"
D=$W/monbin; mkdir -p "$D"
echo "start 2008" >"$D/entries.flow"
BASE_ADDR=0x2000 "$HERE/ghidra-script.sh" raw $LANGID "$W/dl/monitor.bin" RealCheck.java "$D/flow.sum" "$D/flow.lst" 400 "$D/entries.flow" analyze
grep -vE "^(language|executable|blocks)" "$D/flow.sum" | sed 's/^/   /'
python3 "$HERE/real_compare.py" "$W/dl/monitor.bin" 0x2000 "$D/entries.flow" "$D/flow.lst" "$D/flow" || fail=1
if [[ -n $UNIDASM ]]; then
	python3 "$HERE/mame_stream.py" i8008 "$D/flow.bin" "$D/flow.mame.txt" 4 c0
	python3 "$HERE/compare.py" "$D/flow.gh.txt" "$D/flow.mame.txt" | sed 's/^/   /' || fail=1
	python3 "$HERE/asl_roundtrip.py" "$D/flow.gh.txt" "$D/flow.bin" 4 | sed 's/^/   /' || fail=1
fi
if ((fail)); then echo "REAL-CODE CHECKS FAILED"; exit 1; fi
echo "real-code checks passed"
