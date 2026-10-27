#!/usr/bin/env bash
# Random single-instruction differential against MAME's Intel 8008 core, run as a black box in the mod8 driver
# (its ROM files may be dummies: the program under test is placed in the ROM region by a Lua script).
#   test/mame/run-mame-sem.sh <workdir> [tests-per-opcode]
# Runs sem_gen.py (inputs), mame_sem.lua (MAME), sem_gen.py (Ghidra tests) and EmuCheck.java.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
T=$(cd "$HERE/.." && pwd)
W=$(readlink -m "${1:?workdir}")
PER=${2:-30}
mkdir -p "$W/mamerom/mod8"
for i in 1 2 3 4 5 6 7; do head -c 256 /dev/zero > "$W/mamerom/mod8/mon8.00$i"; done
python3 "$T/sem_gen.py" gen "$W/sem_in.txt" "$PER" 1
MAME_SEM_IN=$W/sem_in.txt MAME_SEM_OUT=$W/sem_out.txt timeout 600 mame mod8 -rompath "$W/mamerom" -video none -sound none \
	-seconds_to_run 600 -nothrottle -autoboot_script "$HERE/mame_sem.lua" >"$W/mame.log" 2>&1
[[ $(wc -l <"$W/sem_out.txt") == $(wc -l <"$W/sem_in.txt") ]] || { echo "MAME run incomplete"; tail "$W/mame.log"; exit 1; }
python3 "$T/sem_gen.py" tests "$W/sem_in.txt" "$W/sem_out.txt" "$W/sem_tests.txt"
LANGID=${LANGID:-8008:LE:16:default}
"$T/ghidra-script.sh" raw "$LANGID" "${EMU_BIN:?path of the assembled emu.bin (emu_tests.py)}" EmuCheck.java "$W/sem_tests.txt" "$W/sem_res.txt"
tail -1 "$W/sem_res.txt"
grep -q " 0 failed" "$W/sem_res.txt" || { grep ^FAIL "$W/sem_res.txt" | head -10; exit 1; }
