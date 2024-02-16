global board_name

if { $board_name == "stemlab_125_14_4in"} {
    #io
    create_bd_pin -dir I adc_0_clk_p
    create_bd_pin -dir I adc_0_clk_n
    create_bd_pin -dir I adc_1_clk_p
    create_bd_pin -dir I adc_1_clk_n
    create_bd_intf_pin -mode Slave -vlnv xilinx.com:interface:aximm_rtl:1.0 s0_axi
    create_bd_intf_pin -mode Slave -vlnv xilinx.com:interface:aximm_rtl:1.0 s1_axi
    create_bd_pin -dir I s_axi_aclk
    create_bd_pin -dir I s_axi_aresetn
    create_bd_pin -dir I aresetn
    create_bd_pin -dir O adc_0_clk
    create_bd_pin -dir O adc_1_clk
    create_bd_pin -dir O adc_2_clk
    create_bd_pin -dir O adc_3_clk
    create_bd_pin -dir O adc_0_resetn
    create_bd_pin -dir O adc_1_resetn
    create_bd_pin -dir O adc_2_resetn
    create_bd_pin -dir O adc_3_resetn
    create_bd_pin -dir I -from 7 -to 0 adc_0_data_i
    create_bd_pin -dir I -from 7 -to 0 adc_1_data_i
    create_bd_pin -dir I -from 7 -to 0 adc_2_data_i
    create_bd_pin -dir I -from 7 -to 0 adc_3_data_i
    create_bd_pin -dir I -from 1 -to 0 channel_switch
    create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M0_AXIS
    create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M1_AXIS
    create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M2_AXIS
    create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M3_AXIS
    #adc
    module adc_0 {
        source projects/scope/rp_ddr_adc.tcl
    } {
        clk_p           adc_0_clk_p
        clk_n           adc_0_clk_n
        s_axi           s0_axi
        s_axi_aclk      s_axi_aclk
        s_axi_aresetn   s_axi_aresetn
        aresetn         aresetn
        adc_0_data_i    adc_0_data_i
        adc_1_data_i    adc_1_data_i
        channel_switch  channel_switch
        M0_AXIS         M0_AXIS
        M1_AXIS         M1_AXIS
    }
    connect_bd_net      [get_bd_pins adc_0_clk]         [get_bd_pins adc_0/adc_clk]
    connect_bd_net      [get_bd_pins adc_1_clk]         [get_bd_pins adc_0/adc_clk]
    connect_bd_net      [get_bd_pins adc_0_resetn]      [get_bd_pins adc_0/adc_resetn]
    connect_bd_net      [get_bd_pins adc_1_resetn]      [get_bd_pins adc_0/adc_resetn] 
    module adc_1 {
        source projects/scope/rp_ddr_adc.tcl
    } {
        clk_p           adc_1_clk_p
        clk_n           adc_1_clk_n
        s_axi           s1_axi
        s_axi_aclk      s_axi_aclk
        s_axi_aresetn   s_axi_aresetn
        aresetn         aresetn
        adc_0_data_i    adc_2_data_i
        adc_1_data_i    adc_3_data_i
        channel_switch  channel_switch
        M0_AXIS         M2_AXIS
        M1_AXIS         M3_AXIS
    }
    connect_bd_net      [get_bd_pins adc_2_clk]         [get_bd_pins adc_1/adc_clk]
    connect_bd_net      [get_bd_pins adc_3_clk]         [get_bd_pins adc_1/adc_clk]
    connect_bd_net      [get_bd_pins adc_2_resetn]      [get_bd_pins adc_1/adc_resetn]
    connect_bd_net      [get_bd_pins adc_3_resetn]      [get_bd_pins adc_1/adc_resetn] 
} else {
    #io
    create_bd_pin -dir I adc_clk
    create_bd_pin -dir I adc_clk_locked
    create_bd_pin -dir I aresetn
    create_bd_pin -dir O adc_0_clk
    create_bd_pin -dir O adc_0_resetn
    create_bd_pin -dir O adc_csn_o
    create_bd_pin -dir I -from 13 -to 0 adc_0_data_i
    create_bd_pin -dir I -from 13 -to 0 adc_1_data_i
    create_bd_pin -dir I -from 1 -to 0 channel_switch
    create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:axis_rtl:1.0 M0_AXIS
    connect_bd_net [get_bd_pins adc_0_clk] [get_bd_pins adc_clk]
    cell xilinx.com:ip:proc_sys_reset:5.0 reset_0 {
    } {
        slowest_sync_clk    adc_clk
        ext_reset_in        aresetn
        dcm_locked          adc_clk_locked
        peripheral_aresetn  adc_0_resetn
    }

    # Create axis_red_pitaya_adc
    cell open-mri:user:axis_red_pitaya_adc:3.0 adc_0 {} {
        aclk adc_clk
        adc_dat_a adc_0_data_i
        adc_dat_b adc_1_data_i
        adc_csn adc_csn_o
        adc_channel_switch channel_switch
        M_AXIS M0_AXIS
    }

} 