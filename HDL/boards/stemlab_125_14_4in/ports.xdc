
# set_property CFGBVS VCCO [current_design]
# set_property CONFIG_VOLTAGE 3.3 [current_design]

### ADC

# ADC data
set_property IOSTANDARD LVCMOS18 [get_ports {adc_dat_i_*[*]}]
set_property IOB        TRUE     [get_ports {adc_dat_i_*[*]}]

# ADC 0 data
set_property PACKAGE_PIN Y17     [get_ports {adc_dat_i_0[0]}]
set_property PACKAGE_PIN Y16     [get_ports {adc_dat_i_0[1]}]
set_property PACKAGE_PIN W14     [get_ports {adc_dat_i_0[2]}]
set_property PACKAGE_PIN Y14     [get_ports {adc_dat_i_0[3]}]
set_property PACKAGE_PIN V12     [get_ports {adc_dat_i_0[4]}]
set_property PACKAGE_PIN W13     [get_ports {adc_dat_i_0[5]}]
set_property PACKAGE_PIN V13     [get_ports {adc_dat_i_0[6]}]

# ADC 1 data
set_property PACKAGE_PIN W15     [get_ports {adc_dat_i_1[0]}]
set_property PACKAGE_PIN W16     [get_ports {adc_dat_i_1[1]}]
set_property PACKAGE_PIN V15     [get_ports {adc_dat_i_1[2]}]
set_property PACKAGE_PIN V16     [get_ports {adc_dat_i_1[3]}]
set_property PACKAGE_PIN Y19     [get_ports {adc_dat_i_1[4]}]
set_property PACKAGE_PIN W18     [get_ports {adc_dat_i_1[5]}]
set_property PACKAGE_PIN Y18     [get_ports {adc_dat_i_1[6]}]

# ADC 2 data
set_property PACKAGE_PIN W20     [get_ports {adc_dat_i_2[0]}]
set_property PACKAGE_PIN W19     [get_ports {adc_dat_i_2[1]}]
set_property PACKAGE_PIN V17     [get_ports {adc_dat_i_2[2]}]
set_property PACKAGE_PIN V18     [get_ports {adc_dat_i_2[3]}]
set_property PACKAGE_PIN U17     [get_ports {adc_dat_i_2[4]}]
set_property PACKAGE_PIN T16     [get_ports {adc_dat_i_2[5]}]
set_property PACKAGE_PIN T17     [get_ports {adc_dat_i_2[6]}]

# ADC 3 data
set_property PACKAGE_PIN R19     [get_ports {adc_dat_i_3[0]}]
set_property PACKAGE_PIN R17     [get_ports {adc_dat_i_3[1]}]
set_property PACKAGE_PIN T15     [get_ports {adc_dat_i_3[2]}]
set_property PACKAGE_PIN R16     [get_ports {adc_dat_i_3[3]}]
set_property PACKAGE_PIN T20     [get_ports {adc_dat_i_3[4]}]
set_property PACKAGE_PIN U20     [get_ports {adc_dat_i_3[5]}]
set_property PACKAGE_PIN V20     [get_ports {adc_dat_i_3[6]}]

# clock input
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports {adc_clk_*_i}]

set_property PACKAGE_PIN U18           [get_ports {adc_clk_0_p_i}] #P
set_property PACKAGE_PIN U19           [get_ports {adc_clk_0_n_i}] #N
set_property PACKAGE_PIN N20           [get_ports {adc_clk_1_p_i}] #P
set_property PACKAGE_PIN P20           [get_ports {adc_clk_1_n_i}] #N

### PWM
set_property IOSTANDARD LVCMOS18 [get_ports {dac_pwm_o[*]}]
set_property SLEW FAST [get_ports {dac_pwm_o[*]}]
set_property DRIVE 12 [get_ports {dac_pwm_o[*]}]
# set_property IOB TRUE [get_ports {dac_pwm_o[*]}]

set_property PACKAGE_PIN T10 [get_ports {dac_pwm_o[0]}]
set_property PACKAGE_PIN T11 [get_ports {dac_pwm_o[1]}]
set_property PACKAGE_PIN T19 [get_ports {dac_pwm_o[2]}]
set_property PACKAGE_PIN T14 [get_ports {dac_pwm_o[3]}]

### XADC - This mapping looks incorrect
#set_property IOSTANDARD LVCMOS33 [get_ports Vp_Vn_v_p]
#set_property IOSTANDARD LVCMOS33 [get_ports Vp_Vn_v_n]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux0_v_p]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux0_v_n]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux1_v_p]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux1_v_n]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux8_v_p]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux8_v_n]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux9_v_p]
#set_property IOSTANDARD LVCMOS33 [get_ports Vaux9_v_n]
#
#set_property PACKAGE_PIN K9  [get_ports Vp_Vn_v_p]
#set_property PACKAGE_PIN L10 [get_ports Vp_Vn_v_n]
#set_property PACKAGE_PIN C20 [get_ports Vaux0_v_p]
#set_property PACKAGE_PIN B20 [get_ports Vaux0_v_n]
#set_property PACKAGE_PIN E17 [get_ports Vaux1_v_p]
#set_property PACKAGE_PIN D18 [get_ports Vaux1_v_n]
#set_property PACKAGE_PIN B19 [get_ports Vaux8_v_p]
#set_property PACKAGE_PIN A20 [get_ports Vaux8_v_n]
#set_property PACKAGE_PIN E18 [get_ports Vaux9_v_p]
#set_property PACKAGE_PIN E19 [get_ports Vaux9_v_n]

### Expansion connector

set_property IOSTANDARD LVCMOS33 [get_ports {exp_p_tri_io[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {exp_n_tri_io[*]}]
set_property SLEW FAST [get_ports {exp_p_tri_io[*]}]
set_property SLEW FAST [get_ports {exp_n_tri_io[*]}]
set_property DRIVE 8 [get_ports {exp_p_tri_io[*]}]
set_property DRIVE 8 [get_ports {exp_n_tri_io[*]}]
set_property PULLTYPE PULLUP [get_ports {exp_p_tri_io[*]}]
set_property PULLTYPE PULLUP [get_ports {exp_n_tri_io[*]}]

set_property PACKAGE_PIN G17 [get_ports {exp_p_tri_io[0]}]
set_property PACKAGE_PIN G18 [get_ports {exp_n_tri_io[0]}]
set_property PACKAGE_PIN H16 [get_ports {exp_p_tri_io[1]}]
set_property PACKAGE_PIN H17 [get_ports {exp_n_tri_io[1]}]
set_property PACKAGE_PIN J18 [get_ports {exp_p_tri_io[2]}]
set_property PACKAGE_PIN H18 [get_ports {exp_n_tri_io[2]}]
set_property PACKAGE_PIN K17 [get_ports {exp_p_tri_io[3]}]
set_property PACKAGE_PIN K18 [get_ports {exp_n_tri_io[3]}]
set_property PACKAGE_PIN L14 [get_ports {exp_p_tri_io[4]}]
set_property PACKAGE_PIN L15 [get_ports {exp_n_tri_io[4]}]
set_property PACKAGE_PIN L16 [get_ports {exp_p_tri_io[5]}]
set_property PACKAGE_PIN L17 [get_ports {exp_n_tri_io[5]}]
set_property PACKAGE_PIN K16 [get_ports {exp_p_tri_io[6]}]
set_property PACKAGE_PIN J16 [get_ports {exp_n_tri_io[6]}]
set_property PACKAGE_PIN M14 [get_ports {exp_p_tri_io[7]}]
set_property PACKAGE_PIN M15 [get_ports {exp_n_tri_io[7]}]
set_property PACKAGE_PIN Y9  [get_ports {exp_p_tri_io[8]}]
set_property PACKAGE_PIN Y8  [get_ports {exp_n_tri_io[8]}]
set_property PACKAGE_PIN Y12 [get_ports {exp_p_tri_io[9]}]
set_property PACKAGE_PIN Y13 [get_ports {exp_n_tri_io[9]}]
set_property PACKAGE_PIN Y7  [get_ports {exp_p_tri_io[10]}]
set_property PACKAGE_PIN Y6  [get_ports {exp_n_tri_io[10]}]

#set_property IOSTANDARD LVCMOS33 [get_ports exp_p_trg]
#set_property SLEW FAST [get_ports exp_p_trg]
#set_property DRIVE 8 [get_ports exp_p_trg]
#set_property PACKAGE_PIN M14 [get_ports exp_p_trg] #collision with exp_p_tri_io[7]

#set_property IOSTANDARD LVCMOS33 [get_ports {exp_n_alex[*]}]
#set_property SLEW FAST [get_ports {exp_n_alex[*]}]
#set_property DRIVE 8 [get_ports {exp_n_alex[*]}]

#set_property PACKAGE_PIN L15 [get_ports {exp_n_alex[0]}] #collision with exp_n_tri_io[4]
#set_property PACKAGE_PIN L17 [get_ports {exp_n_alex[1]}] #collision with exp_n_tri_io[5]
#set_property PACKAGE_PIN J16 [get_ports {exp_n_alex[2]}] #collision with exp_n_tri_io[6]
#set_property PACKAGE_PIN M15 [get_ports {exp_n_alex[3]}] #collision with exp_n_tri_io[7]

### SATA connector
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s1_a_p];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s1_a_n];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s1_b_p];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s1_b_n];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s2_a_p];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s2_a_n];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s2_b_p];
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports sata_s2_b_n];
set_property PACKAGE_PIN T12 [get_ports sata_s1_a_p];
set_property PACKAGE_PIN U12 [get_ports sata_s1_a_n];
set_property PACKAGE_PIN U14 [get_ports sata_s1_b_p]; #Clock Capable Input (SRCC)
set_property PACKAGE_PIN U15 [get_ports sata_s1_b_n]; #Clock Capable Input (SRCC)
set_property PACKAGE_PIN P14 [get_ports sata_s2_a_p];
set_property PACKAGE_PIN R14 [get_ports sata_s2_a_n];
set_property PACKAGE_PIN N18 [get_ports sata_s2_b_p]; #Clock Capable Input (MRCC)
set_property PACKAGE_PIN P19 [get_ports sata_s2_b_n]; #Clock Capable Input (MRCC)

### LED

set_property IOSTANDARD LVCMOS33 [get_ports {led_o[*]}]
set_property SLEW SLOW [get_ports {led_o[*]}]
set_property DRIVE 4 [get_ports {led_o[*]}]

set_property PACKAGE_PIN F16 [get_ports {led_o[0]}]
set_property PACKAGE_PIN F17 [get_ports {led_o[1]}]
set_property PACKAGE_PIN G19 [get_ports {led_o[2]}]
set_property PACKAGE_PIN G15 [get_ports {led_o[3]}]
set_property PACKAGE_PIN G14 [get_ports {led_o[4]}]
set_property PACKAGE_PIN F20 [get_ports {led_o[5]}]
set_property PACKAGE_PIN G20 [get_ports {led_o[6]}]
set_property PACKAGE_PIN H20 [get_ports {led_o[7]}]
