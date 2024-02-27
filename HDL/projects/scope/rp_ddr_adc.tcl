#io
create_bd_pin -dir I clk_p
create_bd_pin -dir I clk_n
create_bd_intf_pin -mode Slave -vlnv xilinx.com:interface:aximm_rtl:1.0 s_axi
create_bd_pin -dir I s_axi_aclk
create_bd_pin -dir I s_axi_aresetn
create_bd_pin -dir I aresetn
create_bd_pin -dir O adc_clk
create_bd_pin -dir O adc_resetn
create_bd_pin -dir O valid_pattern_0
create_bd_pin -dir O valid_pattern_1
create_bd_pin -dir I -from 7 -to 0 adc_0_data_i
create_bd_pin -dir I -from 7 -to 0 adc_1_data_i
create_bd_pin -dir I -from 1 -to 0 channel_switch
create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M0_AXIS
create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M1_AXIS

#clocking
create_bd_cell -type module -reference ibufds_bufg ibufds_bufg_0
set_property CONFIG.FREQ_HZ 125000000 [get_bd_pins ibufds_bufg_0/clk]
set_property CONFIG.FREQ_HZ 125000000 [get_bd_pins ibufds_bufg_0/clk_p]
set_property CONFIG.FREQ_HZ 125000000 [get_bd_pins ibufds_bufg_0/clk_n]
connect_bd_net [get_bd_pins clk_p] [get_bd_pins ibufds_bufg_0/clk_p]
connect_bd_net [get_bd_pins clk_n] [get_bd_pins ibufds_bufg_0/clk_n]
cell xilinx.com:ip:clk_wiz:6.0 pll_adc_0 {
    PRIMITIVE PLL
    PRIM_IN_FREQ.VALUE_SRC USER
    PRIM_IN_FREQ 125.0
    PRIM_SOURCE Global_buffer
    JITTER_SEL Max_I_Jitter
    PHASE_DUTY_CONFIG true
    USE_DYN_RECONFIG true
    CLKOUT1_USED true
    CLKOUT1_REQUESTED_OUT_FREQ 125.0
    CLKOUT1_REQUESTED_PHASE 135.0
} {
    clk_in1 ibufds_bufg_0/clk
    s_axi_lite s_axi
    s_axi_aclk s_axi_aclk
    s_axi_aresetn s_axi_aresetn
    clk_out1 adc_clk
}
cell xilinx.com:ip:proc_sys_reset:5.0 reset_0 {
} {
    slowest_sync_clk pll_adc_0/clk_out1
    ext_reset_in aresetn
    dcm_locked pll_adc_0/locked
    peripheral_aresetn adc_resetn
}
set aclk    pll_adc_0/clk_out1
set aresetn reset_0/peripheral_aresetn

#adc
cell open-mri:user:axis_red_pitaya_adc_ddr:1.0 adc_ddr_0 {
} {
    aclk $aclk
    aresetn $aresetn
    adc_dat_in_0 adc_0_data_i
    adc_dat_in_1 adc_1_data_i
}
cell xilinx.com:ip:xpm_cdc_gen:1.0 valid_pattern_cdc_0 {
    CDC_TYPE xpm_cdc_single
} {
    src_clk $aclk
    src_in adc_ddr_0/test_pattern_valid_0
    dest_clk s_axi_aclk
    dest_out valid_pattern_0
}
cell xilinx.com:ip:xpm_cdc_gen:1.0 valid_pattern_cdc_1 {
    CDC_TYPE xpm_cdc_single
} {
    src_clk $aclk
    src_in adc_ddr_0/test_pattern_valid_1
    dest_clk s_axi_aclk
    dest_out valid_pattern_1
}

cell xilinx.com:ip:xlconstant:1.1 xlconstant_0 {
  CONST_VAL 0x2000
  CONST_WIDTH 14
} {
}
cell xilinx.com:ip:xpm_cdc_gen:1.0 xpm_cdc_gen_0 {
    CDC_TYPE xpm_cdc_array_single
    WIDTH 2
} {
    src_in channel_switch
    dest_clk $aclk
    src_clk s_axi_aclk
}
# Create axis_red_pitaya_adc
cell open-mri:user:axis_red_pitaya_adc:3.0 adc_0 {} {
    aclk $aclk
    adc_dat_a adc_ddr_0/adc_dat_out_0
    adc_dat_b xlconstant_0/Dout
    adc_channel_switch xpm_cdc_gen_0/dest_out
    m_axis M0_AXIS
}
cell open-mri:user:axis_red_pitaya_adc:3.0 adc_1 {} {
    aclk $aclk
    adc_dat_a adc_ddr_0/adc_dat_out_1
    adc_dat_b xlconstant_0/Dout
    adc_channel_switch xpm_cdc_gen_0/dest_out
    m_axis M1_AXIS
}