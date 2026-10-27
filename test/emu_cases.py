"""Hand-computed p-code test cases for the Intel 8008 module (assembled by emu_tests.py, run by EmuCheck.java).

T(name, asm, init, expect): asm is a short sequence (asl syntax, cpu 8008new), init and expect are comma
separated items: registers (a b c d e h l, SP), flags (CY_flag Z_flag S_flag P_flag), 'm1:<addr>=<hex>'
(memory; 'n2:<addr>' is a little-endian 16-bit word, used for the return stack at 0xFFF0-0xFFFF) and
'io@1:<port>=<hex>' (I/O port).  '@END@' is the address after the sequence, '@label@' a label of the sequence.

Every expectation is worked out by hand from the Intel 8008 User's Manual: carry is the carry out of bit 7
for additions and the borrow for subtractions and comparisons; INR/DCR and the rotates leave the other flags
alone (the rotates change only the carry); AND/XOR/OR clear the carry; Z, S and P (P = even number of one
bits) come from the result.  Tests whose name starts with XFAIL_ carry a deliberately wrong expectation and
must be reported as failures.
"""

CASES = []


def T(name, asm, init='', expect=''):
    CASES.append((name, asm, init, expect))


def F(cy=None, z=None, s=None, p=None):
    items = []
    for n, v in (('CY_flag', cy), ('Z_flag', z), ('S_flag', s), ('P_flag', p)):
        if v is not None:
            items.append(f'{n}={v}')
    return ','.join(items)


def J(*parts):
    return ','.join(p for p in parts if p)


# ------------------------------------------------------------------------------------------------------
# moves
# ------------------------------------------------------------------------------------------------------
T('mvi_keeps_flags', 'mvi b,05ah', J('B=0', F(1, 1, 1, 1)), J('B=5a', F(1, 1, 1, 1)))
T('mov_reg', 'mov c,b', 'B=12,C=0', 'C=12,B=12')
T('mov_a_m_masks_h_to_6_bits', 'mov a,m', 'H=c0,L=40,A=0,m1:40=99', 'A=99')
T('mov_a_m_14bit_address', 'mov a,m', 'H=21,L=43,A=0,m1:2143=5c,m1:0143=11', 'A=5c')
T('mov_m_reg', 'mov m,e', 'H=0,L=50,E=7e,m1:50=0', 'm1:50=7e')
T('mvi_m', 'mvi m,0a5h', 'H=1,L=2,m1:102=0', 'm1:102=a5')
T('mov_r_r_swap', 'mov a,b\n\tmov b,c\n\tmov c,a', 'A=0,B=11,C=22', 'A=11,B=22,C=11')

# ------------------------------------------------------------------------------------------------------
# INR / DCR: Z, S, P set, carry untouched
# ------------------------------------------------------------------------------------------------------
T('inr_wraps_to_zero', 'inr b', J('B=ff', F(cy=1, z=0, s=1, p=0)), J('B=00', F(cy=1, z=1, s=0, p=1)))
T('dcr_wraps_to_ff', 'dcr c', J('C=0', F(cy=0, z=1, s=0, p=1)), J('C=ff', F(cy=0, z=0, s=1, p=1)))
T('inr_parity_even', 'inr d', 'D=02', J('D=03', F(z=0, s=0, p=1)))
T('inr_parity_odd', 'inr e', 'E=00', J('E=01', F(z=0, s=0, p=0)))
T('dcr_to_7f', 'dcr h', 'H=80', J('H=7f', F(z=0, s=0, p=0)))
T('inr_l_7f', 'inr l', 'L=7f', J('L=80', F(z=0, s=1, p=0)))

# ------------------------------------------------------------------------------------------------------
# arithmetic
# ------------------------------------------------------------------------------------------------------
T('add_carry_out', 'add b', 'A=f0,B=20', J('A=10', F(cy=1, z=0, s=0, p=0)))
T('add_m_sign', 'add m', 'A=01,H=0,L=60,m1:60=7f', J('A=80', F(cy=0, z=0, s=1, p=0)))
T('adi_to_zero', 'adi 1', 'A=ff', J('A=00', F(cy=1, z=1, s=0, p=1)))
T('add_a_doubles', 'add a', 'A=81', J('A=02', F(cy=1, z=0, s=0, p=0)))
T('adc_with_carry', 'adc b', J('A=0f,B=01', F(cy=1)), J('A=11', F(cy=0, z=0, s=0, p=1)))
T('adc_carry_chain', 'adc b', J('A=ff,B=0', F(cy=1)), J('A=00', F(cy=1, z=1, s=0, p=1)))
T('aci', 'aci 0fh', J('A=f0', F(cy=1)), J('A=00', F(cy=1, z=1, s=0, p=1)))
T('adc_without_carry', 'adc c', J('A=40,C=40', F(cy=0)), J('A=80', F(cy=0, z=0, s=1, p=0)))
T('sub_borrow', 'sub b', 'A=10,B=20', J('A=f0', F(cy=1, z=0, s=1, p=1)))
T('sub_equal', 'sub c', 'A=55,C=55', J('A=00', F(cy=0, z=1, s=0, p=1)))
T('sub_a_clears', 'sub a', J('A=9c', F(cy=1)), J('A=0', F(cy=0, z=1, s=0, p=1)))
T('sui', 'sui 1', 'A=00', J('A=ff', F(cy=1, z=0, s=1, p=1)))
T('sbb_with_borrow_to_zero', 'sbb d', J('A=10,D=0f', F(cy=1)), J('A=00', F(cy=0, z=1, s=0, p=1)))
T('sbb_borrow_out', 'sbb b', J('A=0,B=0', F(cy=1)), J('A=ff', F(cy=1, z=0, s=1, p=1)))
T('sbb_operand_ff_with_borrow', 'sbb b', J('A=ff,B=ff', F(cy=1)), J('A=ff', F(cy=1, z=0, s=1, p=1)))
T('sbi', 'sbi 5', J('A=5', F(cy=0)), J('A=0', F(cy=0, z=1, s=0, p=1)))
T('sub_m', 'sub m', 'A=3,H=0,L=70,m1:70=4', J('A=ff', F(cy=1, z=0, s=1, p=1)))

# ------------------------------------------------------------------------------------------------------
# logic and compare
# ------------------------------------------------------------------------------------------------------
T('ana_clears_carry', 'ana e', J('A=f3,E=3f', F(cy=1)), J('A=33', F(cy=0, z=0, s=0, p=1)))
T('xra_a_zero', 'xra a', J('A=77', F(cy=1)), J('A=0', F(cy=0, z=1, s=0, p=1)))
T('ora_sign', 'ora b', J('A=80,B=01', F(cy=1)), J('A=81', F(cy=0, z=0, s=1, p=1)))
T('ani', 'ani 0fh', J('A=a7', F(cy=1)), J('A=07', F(cy=0, z=0, s=0, p=0)))
T('xri', 'xri 0ffh', J('A=0f', F(cy=1)), J('A=f0', F(cy=0, z=0, s=1, p=1)))
T('ori', 'ori 1', J('A=0', F(cy=1)), J('A=01', F(cy=0, z=0, s=0, p=0)))
T('ora_m', 'ora m', J('A=1,H=0,L=71,m1:71=2', F(cy=1)), J('A=03', F(cy=0, z=0, s=0, p=1)))
T('cmp_less', 'cmp b', 'A=20,B=30', J('A=20', F(cy=1, z=0, s=1, p=1)))
T('cmp_equal', 'cmp b', J('A=44,B=44', F(cy=1)), J('A=44', F(cy=0, z=1, s=0, p=1)))
T('cmp_greater', 'cmp b', 'A=30,B=20', J('A=30', F(cy=0, z=0, s=0, p=0)))
T('cpi', 'cpi 80h', 'A=7f', J('A=7f', F(cy=1, z=0, s=1, p=1)))

# ------------------------------------------------------------------------------------------------------
# rotates: only the carry changes
# ------------------------------------------------------------------------------------------------------
T('rlc', 'rlc', J('A=81', F(cy=0, z=1, s=1, p=0)), J('A=03', F(cy=1, z=1, s=1, p=0)))
T('rrc', 'rrc', J('A=01', F(cy=0)), J('A=80', F(cy=1)))
T('ral_through_carry', 'ral', J('A=80', F(cy=1)), J('A=01', F(cy=1)))
T('ral_in_zero', 'ral', J('A=40', F(cy=0)), J('A=80', F(cy=0)))
T('rar_through_carry', 'rar', J('A=01', F(cy=0)), J('A=00', F(cy=1)))
T('rar_carry_in', 'rar', J('A=02', F(cy=1)), J('A=81', F(cy=0)))

# ------------------------------------------------------------------------------------------------------
# jumps
# ------------------------------------------------------------------------------------------------------
T('jmp_skips', 'jmp over\n\tmvi a,1\nover:\tmvi b,2', 'A=0,B=0', 'A=0,B=2')
T('jmp_ignores_top_address_bits', '\tdb 44h, over & 0ffh, (over >> 8) | 0c0h\n\tmvi a,1\nover:\tmvi b,2', 'A=0,B=0', 'A=0,B=2')
T('jz_taken_jnz_not', 'xra a\n\tjz l1\n\tmvi b,1\nl1:\tjnz l2\n\tmvi c,2\nl2:', 'B=0,C=0', 'B=0,C=2')
T('jnc_taken_jc_not', 'jnc l1\n\tmvi b,1\nl1:\tjc l2\n\tmvi c,2\nl2:', 'B=0,C=0,CY_flag=0', 'B=0,C=2')
T('jc_taken_jnc_not', 'jnc l1\n\tmvi b,1\nl1:\tjc l2\n\tmvi c,2\nl2:', 'B=0,C=0,CY_flag=1', 'B=1,C=0')
T('jp_jm', 'mvi a,0\n\tora a\n\tjm l1\n\tmvi b,1\nl1:\tjp l2\n\tmvi c,2\nl2:', 'B=0,C=0', 'B=1,C=0')
T('jpe_jpo', 'xri 3\n\tjpo l1\n\tmvi b,1\nl1:\tjpe l2\n\tmvi c,2\nl2:', 'A=0,B=0,C=0', 'B=1,C=0')
T('jpo_taken', 'ori 1\n\tjpe l1\n\tmvi b,1\nl1:\tjpo l2\n\tmvi c,2\nl2:', 'A=0,B=0,C=0', 'B=1,C=0')
T('jm_taken', 'ori 80h\n\tjp l1\n\tmvi b,1\nl1:\tjm l2\n\tmvi c,2\nl2:', 'A=0,B=0,C=0', 'B=1,C=0')
T('countdown_loop', 'mvi b,5\n\tmvi a,0\nlp:\tadd b\n\tdcr b\n\tjnz lp', 'A=0,B=0', 'A=0f,B=0')

# ------------------------------------------------------------------------------------------------------
# calls and returns on the on-chip stack
# ------------------------------------------------------------------------------------------------------
T('call_ret', 'call sub1\n\tmvi c,3\n\tjmp done\nsub1:\tmvi b,7\n\tret\ndone:', 'B=0,C=0,SP=0', 'B=7,C=3,SP=0')
T('call_pushes_return_address', 'call nxt\nnxt:', 'SP=0', 'SP=fffe,n2:fffe=@END@')
T('call_second_level', 'call l1\nl1:\tcall l2\nl2:', 'SP=0', 'SP=fffc,n2:fffe=@l1@,n2:fffc=@l2@')
T('ret_pops', 'ret\n\tmvi a,1\ntgt:\tmvi b,2', 'SP=fffe,n2:fffe=@tgt@,A=0,B=0', 'SP=0,A=0,B=2')
T('ret_any_x_bits', '@raw 3f\n\tmvi a,1\ntgt:\tmvi b,2', 'SP=fffe,n2:fffe=@tgt@,A=0,B=0', 'SP=0,A=0,B=2')
T('seven_nested_calls',
  'call n1\nn1:\tcall n2\nn2:\tcall n3\nn3:\tcall n4\nn4:\tcall n5\nn5:\tcall n6\nn6:\tcall n7\nn7:',
  'SP=0', 'SP=fff2,n2:fffe=@n1@,n2:fff2=@n7@,n2:fff8=@n4@')
T('ret_pops_from_sp', 'ret\n\tmvi a,1\ntgt:\tmvi b,2', 'SP=fff0,n2:fff0=@tgt@,A=0,B=0', 'SP=fff2,A=0,B=2')
T('cnz_not_taken', 'xra a\n\tcnz sub1\n\tmvi c,3\n\tjmp done\nsub1:\tmvi b,7\n\tret\ndone:', 'B=0,C=0,SP=0', 'B=0,C=3,SP=0')
T('cz_taken', 'xra a\n\tcz sub1\n\tmvi c,3\n\tjmp done\nsub1:\tmvi b,7\n\tret\ndone:', 'B=0,C=0,SP=0', 'B=7,C=3,SP=0')
T('cc_taken_cnc_not', 'cc sub1\n\tcnc sub1\n\tjmp done\nsub1:\tinr b\n\tret\ndone:', J('B=0,SP=0', F(cy=1)), 'B=1,SP=0')
T('cp_cm', 'ora a\n\tcm sub1\n\tcp sub1\n\tjmp done\nsub1:\tinr b\n\tret\ndone:', 'A=1,B=0,SP=0', 'B=1,SP=0')
T('cpe_cpo', 'ora a\n\tcpo sub1\n\tcpe sub1\n\tjmp done\nsub1:\tinr b\n\tret\ndone:', 'A=3,B=0,SP=0', 'B=1,SP=0')
T('rz_returns', 'call sub1\n\tmvi c,3\n\tjmp done\nsub1:\txra a\n\trz\n\tmvi b,9\n\tret\ndone:', 'B=0,C=0,SP=0', 'B=0,C=3,SP=0')
T('rnz_falls_through', 'call sub1\n\tmvi c,3\n\tjmp done\nsub1:\txra a\n\trnz\n\tmvi b,9\n\tret\ndone:', 'B=0,C=0,SP=0', 'B=9,C=3,SP=0')
T('rc_rnc', 'call sub1\n\tjmp done\nsub1:\trnc\n\tmvi b,5\n\trc\n\tmvi c,6\n\tret\ndone:', J('B=0,C=0,SP=0', F(cy=1)), 'B=5,C=0,SP=0')
T('rp_taken', 'call sub1\n\tjmp done\nsub1:\trp\n\tmvi b,5\n\tret\ndone:', J('B=0,SP=0', F(s=0)), 'B=0,SP=0')
T('rp_not_taken', 'call sub1\n\tjmp done\nsub1:\trp\n\tmvi b,5\n\tret\ndone:', J('B=0,SP=0', F(s=1)), 'B=5,SP=0')
T('rm_taken', 'call sub1\n\tjmp done\nsub1:\trm\n\tmvi b,5\n\tret\ndone:', J('B=0,SP=0', F(s=1)), 'B=0,SP=0')
T('rm_not_taken', 'call sub1\n\tjmp done\nsub1:\trm\n\tmvi b,5\n\tret\ndone:', J('B=0,SP=0', F(s=0)), 'B=5,SP=0')
T('rpe_rpo', 'call sub1\n\tjmp done\nsub1:\trpo\n\tmvi b,5\n\trpe\n\tmvi c,6\n\tret\ndone:', J('B=0,C=0,SP=0', F(p=1)), 'B=5,C=0,SP=0')
for v in range(8):
    T(f'rst_{v}', f'rst {v}', 'L=ee,SP=0', f'L={v:02x},SP=0')

# ------------------------------------------------------------------------------------------------------
# I/O
# ------------------------------------------------------------------------------------------------------
T('in_port3', 'in 3', 'A=0,io@1:3=5c', 'A=5c')
T('in_port0', 'in 0', 'A=0,io@1:0=81', 'A=81')
T('in_port7', 'in 7', 'A=0,io@1:7=02,io@1:6=03', 'A=02')
T('out_port9', 'out 9', 'A=77,io@1:9=0', 'io@1:9=77')
T('out_port8', 'out 8', 'A=11,io@1:8=0,io@1:9=0', 'io@1:8=11,io@1:9=0')
T('out_port31', 'out 31', 'A=a5,io@1:1f=0', 'io@1:1f=a5')
T('out_port17', 'out 17', 'A=3c,io@1:11=0', 'io@1:11=3c')

# ------------------------------------------------------------------------------------------------------
# programs
# ------------------------------------------------------------------------------------------------------
T('copy_block',
  'mvi h,1\n\tmvi l,0\n\tmvi e,4\nlp:\tmov a,m\n\tinr l\n\tinr l\n\tinr l\n\tinr l\n\tmov m,a\n\tdcr l\n\tdcr l\n\tdcr l\n\tdcr e\n\tjnz lp',
  'm1:100=11,m1:101=22,m1:102=33,m1:103=44', 'm1:104=11,m1:105=22,m1:106=33,m1:107=44')
T('sum_bytes',
  'mvi h,0\n\tmvi l,80h\n\tmvi b,4\n\txra a\nlp:\tadd m\n\tinr l\n\tdcr b\n\tjnz lp',
  'm1:80=01,m1:81=02,m1:82=03,m1:83=04', J('A=0a,B=0', F(cy=0, z=1, s=0, p=1)))
T('multiply_8x8_by_shifts',
  'mvi b,13\n\tmvi c,11\n\tmvi d,0\nlp:\tmov a,c\n\tora a\n\tjz done_\n\tdcr c\n\tmov a,d\n\tadd b\n\tmov d,a\n\tjmp lp\ndone_:',
  'B=0,C=0,D=0', 'D=8f,C=0')

# a deliberately wrong expectation must be reported
T('XFAIL_add_wrong_result', 'add b', 'A=01,B=01', 'A=03')
T('XFAIL_flag_wrong', 'sub b', 'A=01,B=01', 'Z_flag=0')
