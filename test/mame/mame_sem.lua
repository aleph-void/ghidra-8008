-- Run single-instruction tests on MAME's Intel 8008 core (driver mod8, ROM files may be dummies) and
-- write the resulting state.  The CPU state is set through its save-state items (the program counter is
-- the stack entry the pointer selects); the instruction is placed
-- at 0x100 of the ROM region followed by HLT (all other memory is zero / open bus = HLT); the CPU runs until it
-- halts.  Input (env MAME_SEM_IN) and output (MAME_SEM_OUT): one test per line, decimal numbers.
--   in:  id A B C D E H L CF ZF SF PF PCPOS ADDR0 ADDR1 mbyte op b1 b2
--   out: id A B C D E H L CF ZF SF PF HALT PC PCPOS ADDR0 ADDR1 mbyte
-- M is the byte at ((H & 0x3f) << 8 | L), which the tests keep inside the RAM at 0x800-0xbff.
local m = manager.machine
local cpu = m.devices[":maincpu"]
local rgn = m.memory.regions[":maincpu"]
local function item(name) return emu.item(cpu.items["0/" .. name]) end
local A, B, C, D, E, H, L = item("m_A"), item("m_B"), item("m_C"), item("m_D"), item("m_E"), item("m_H"), item("m_L")
local CF, ZF, SF, PF = item("m_CF"), item("m_ZF"), item("m_SF"), item("m_PF")
local PC, HALT, POS = item("m_PC"), item("m_HALT"), item("m_pc_pos")
local SUSP, NSUSP = item("m_suspend"), item("m_nextsuspend")
local ADDR = {}
for i = 0, 7 do ADDR[i] = item("m_ADDR[" .. i .. "]") end
local RAM = emu.item(cpu.items["0/800-bff"])
emu.wait(0.001)   -- the CPU starts out held in reset; let it halt at 0 first
local fin, fout = io.open(os.getenv("MAME_SEM_IN"), "r"), io.open(os.getenv("MAME_SEM_OUT"), "w")
for a = 0, rgn.size - 1 do rgn:write_u8(a, 0) end
for line in fin:lines() do
  local v = {}
  for w in line:gmatch("%-?%d+") do v[#v + 1] = tonumber(w) end
  if #v >= 19 then
    local id = v[1]
    A:write(0, v[2]); B:write(0, v[3]); C:write(0, v[4]); D:write(0, v[5]); E:write(0, v[6]); H:write(0, v[7]); L:write(0, v[8])
    CF:write(0, v[9]); ZF:write(0, v[10]); SF:write(0, v[11]); PF:write(0, v[12])
    POS:write(0, v[13]); ADDR[0]:write(0, v[14]); ADDR[1]:write(0, v[15])
    local maddr = ((v[7] & 0x3f) << 8 | v[8]) - 0x800
    RAM:write(maddr, v[16])
    local op = v[17]
    local len = 1
    if op < 0x40 and ((op & 7) == 4 or (op & 7) == 6) then len = 2
    elseif op >= 0x40 and op < 0x80 and (op & 1) == 0 then len = 3 end
    rgn:write_u8(0x100, op)
    rgn:write_u8(0x101, len >= 2 and v[18] or 0)
    rgn:write_u8(0x102, len >= 3 and v[19] or 0)
    rgn:write_u8(0x103, 0)
    ADDR[v[13] & 7]:write(0, 0x100)
    HALT:write(0, 0)
    SUSP:write(0, 0); NSUSP:write(0, 0)
    local n = 0
    repeat
      emu.wait(0.0002)
      n = n + 1
    until HALT:read(0) ~= 0 or n > 20
    fout:write(string.format("%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d\n", id, A:read(0), B:read(0), C:read(0), D:read(0),
      E:read(0), H:read(0), L:read(0), CF:read(0), ZF:read(0), SF:read(0), PF:read(0), HALT:read(0), cpu.state["PC"].value, POS:read(0),
      ADDR[0]:read(0), ADDR[1]:read(0), RAM:read(maddr)))
    -- leave the test's cell clean
    RAM:write(maddr, 0)
    HALT:write(0, 0)
  end
end
fout:close()
m:exit()
