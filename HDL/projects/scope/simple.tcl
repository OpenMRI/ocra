global board_name
global project_name
global ps_preset
global pl_param_dict
cell xilinx.com:ip:xlconstant:1.1 const_low
cell xilinx.com:ip:xlconstant:1.1 const_high
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] [get_bd_cells const_low]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] [get_bd_cells const_high]

# A simplified scope does not have a microsequencer

# Create processing_system7
cell xilinx.com:ip:processing_system7:5.5 ps_0 {
  PCW_IMPORT_BOARD_PRESET $ps_preset
  PCW_USE_S_AXI_HP0 1
  PCW_USE_S_AXI_HP1 1
  PCW_USE_S_AXI_HP2 1
  PCW_USE_S_AXI_HP3 1
  PCW_USE_FABRIC_INTERRUPT 1
  PCW_IRQ_F2P_INTR 1 
} {
  M_AXI_GP0_ACLK ps_0/FCLK_CLK0
  S_AXI_HP0_ACLK ps_0/FCLK_CLK0
  S_AXI_HP1_ACLK ps_0/FCLK_CLK0
  S_AXI_HP2_ACLK ps_0/FCLK_CLK0
  S_AXI_HP3_ACLK ps_0/FCLK_CLK0
}


# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 -config {
  make_external {FIXED_IO, DDR}
  Master Disable
  Slave Disable
} [get_bd_cells ps_0]

# Create proc_sys_reset
cell xilinx.com:ip:proc_sys_reset:5.0 rst_0
connect_bd_net [get_bd_pins ps_0/FCLK_RESET0_N] [get_bd_pins rst_0/ext_reset_in]
connect_bd_net [get_bd_pins ps_0/FCLK_CLK0]     [get_bd_pins rst_0/slowest_sync_clk]
cell xilinx.com:ip:xlconstant:1.1 const_0

if {[dict get $pl_param_dict fclk_source] == "SATA"} {
  cell xilinx.com:ip:clk_wiz:6.0 pll_fclk_0 {
    PRIMITIVE PLL
    PRIM_IN_FREQ.VALUE_SRC USER
    PRIM_IN_FREQ 125.0
    PRIM_SOURCE Differential_clock_capable_pin
    CLKOUT1_USED true
    CLKOUT1_REQUESTED_OUT_FREQ 125.0
    USE_RESET false
  } {
    clk_in1_p sata_s2_b_p
    clk_in1_n sata_s2_b_n
  }
  set fclk /pll_fclk_0/clk_out1
  set fclk_locked /pll_fclk_0/locked
} else {
  set fclk /ps_0/FCLK_CLK0
  set fclk_locked const_0/dout
}

# clocks and resets
set ps_clk     /ps_0/FCLK_CLK0
set ps_aresetn /rst_0/peripheral_aresetn
set ps_reset   /rst_0/peripheral_reset

cell xilinx.com:ip:proc_sys_reset:5.0 rst_125_0
connect_bd_net [get_bd_pins ps_0/FCLK_RESET0_N] [get_bd_pins rst_125_0/ext_reset_in]
connect_bd_net [get_bd_pins $fclk] [get_bd_pins rst_125_0/slowest_sync_clk]
connect_bd_net [get_bd_pins $fclk_locked] [get_bd_pins rst_125_0/dcm_locked]

set f_aresetn /rst_125_0/peripheral_aresetn
set f_reset   /rst_125_0/peripheral_reset

# Create axi_cfg_register
cell open-mri:user:axi_config_registers:1.0 cfg8 {
    AXI_ADDR_WIDTH 5
    AXI_DATA_WIDTH 32
} {
  S_AXI_ACLK $fclk
  S_AXI_ARESETN $f_aresetn
}

# Create slice with the TX configuration, which uses the bottom 32 bits
cell xilinx.com:ip:xlslice:1.0 txinterpolator_slice_0 {
  DIN_WIDTH 32 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
} {
  Din cfg8/config_0
}

# Create slice with the RX configuration and NCO configuration
# RX seems to use the bottom 16 bit of the upper 32 bit
# NCO uses the bottom 32 bit
cell xilinx.com:ip:xlslice:1.0 nco_slice_0 {
  DIN_WIDTH 32 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
} {
  Din cfg8/config_1
}

cell xilinx.com:ip:xlslice:1.0 rx_slice_0 {
  DIN_WIDTH 32 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
} {
  Din cfg8/config_2
}

# ADC switch slice
cell xilinx.com:ip:xlslice:1.0 cfg_adc_switch {
  DIN_WIDTH 32 DIN_FROM 1 DIN_TO 0 DOUT_WIDTH 2
} {
  Din cfg8/config_4
}


# Create another slice with data for the TX, which is another 32 bit
cell xilinx.com:ip:xlslice:1.0 cfg_slice_1 {
  DIN_WIDTH 32 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
} {
  Din cfg8/config_3
}

# ADC
module rp_adc_0 {
    source projects/scope/rp_adc.tcl
} {
    aresetn         ps_0/FCLK_RESET0_N
    channel_switch  cfg_adc_switch/Dout
}

if { $board_name == "stemlab_125_14_4in"} {
    connect_bd_net [get_bd_pins rp_adc_0/adc_0_clk_p]       [get_bd_ports adc_clk_0_p_i]
    connect_bd_net [get_bd_pins rp_adc_0/adc_0_clk_n]       [get_bd_ports adc_clk_0_n_i]
    connect_bd_net [get_bd_pins rp_adc_0/adc_1_clk_p]       [get_bd_ports adc_clk_1_p_i]
    connect_bd_net [get_bd_pins rp_adc_0/adc_1_clk_n]       [get_bd_ports adc_clk_1_n_i]
    connect_bd_net [get_bd_pins rp_adc_0/s_axi_aclk]        [get_bd_pins $fclk]
    connect_bd_net [get_bd_pins rp_adc_0/s_axi_aresetn]     [get_bd_pins $f_aresetn]
    connect_bd_net [get_bd_pins rp_adc_0/adc_0_data_i]      [get_bd_ports adc_dat_i_0]        
    connect_bd_net [get_bd_pins rp_adc_0/adc_1_data_i]      [get_bd_ports adc_dat_i_1]        
    connect_bd_net [get_bd_pins rp_adc_0/adc_2_data_i]      [get_bd_ports adc_dat_i_2]        
    connect_bd_net [get_bd_pins rp_adc_0/adc_3_data_i]      [get_bd_ports adc_dat_i_3]
    save_bd_design
    
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
        Master  /ps_0/M_AXI_GP0
        Clk     Auto
    } [get_bd_intf_pins /rp_adc_0/adc_0/pll_adc_0/s_axi_lite]
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
        Master  /ps_0/M_AXI_GP0
        Clk     Auto
    } [get_bd_intf_pins /rp_adc_0/adc_1/pll_adc_0/s_axi_lite]
    set_property RANGE 64K          [get_bd_addr_segs {ps_0/Data/SEG_pll_adc_0_Reg}]
    set_property offset 0x40100000  [get_bd_addr_segs {ps_0/Data/SEG_pll_adc_0_Reg}]
    set_property RANGE 64K          [get_bd_addr_segs {ps_0/Data/SEG_pll_adc_0_Reg_1}]
    set_property offset 0x40110000  [get_bd_addr_segs {ps_0/Data/SEG_pll_adc_0_Reg_1}]

    # Manual SPI Write to ADC
    cell open-mri:user:axi_config_registers:1.0 axi_config_adc_spi_0 {
        AXI_ADDR_WIDTH 5
        AXI_DATA_WIDTH 32
    } {
        S_AXI_ACLK $fclk
        S_AXI_ARESETN $f_aresetn
    }
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
        Master  /ps_0/M_AXI_GP0
        Clk     Auto
    } [get_bd_intf_pins axi_config_adc_spi_0/s_axi]
    set_property offset 0x40002000 [get_bd_addr_segs {ps_0/Data/SEG_axi_config_adc_spi_0_reg0}]
    set_property range  4K         [get_bd_addr_segs {ps_0/Data/SEG_axi_config_adc_spi_0_reg0}]
    cell xilinx.com:ip:xlslice:1.0 adc_spi_wrdata_0 {
        DIN_WIDTH 32 DIN_FROM 15 DIN_TO 0 DOUT_WIDTH 16
    } {
        Din axi_config_adc_spi_0/config_0
    }
    cell xilinx.com:ip:xlslice:1.0 adc_spi_wr_0 {
        DIN_WIDTH 32 DIN_FROM 0 DIN_TO 0 DOUT_WIDTH 1
    } {
        Din axi_config_adc_spi_0/config_1
    }
    # SPI Write to ADC
    cell open-mri:user:red_pitaya_adc_spi:1.0 adc_spi_0 {
    } {
        sclk    spi_clk_o
        sdio    spi_mosi_o
        aclk    $fclk
        aresetn $f_aresetn
        spi_data adc_spi_wrdata_0/Dout
        spi_wr   adc_spi_wr_0/Dout
    }
    connect_bd_net [get_bd_pins adc_spi_0/n_cs] [get_bd_ports spi_csa_o]
    connect_bd_net [get_bd_pins adc_spi_0/n_cs] [get_bd_ports spi_csb_o]
    # Pattern Validation
    cell xilinx.com:ip:xlconstant:1.1 const_28_0 {
        CONST_WIDTH 28
        CONST_VAL 0
    } {}
    cell xilinx.com:ip:xlconcat:2.1 pattern_valid_concat_0 {
        NUM_PORTS 5
    } {
        In0 rp_adc_0/valid_pattern_0
        In1 rp_adc_0/valid_pattern_1
        In2 rp_adc_0/valid_pattern_2
        In3 rp_adc_0/valid_pattern_3
        In4 const_28_0/Dout
    }
    cell pavel-demin:user:axi_sts_register:1.0 adc_sts_0 {
        STS_DATA_WIDTH 32
        AXI_ADDR_WIDTH 32
        AXI_DATA_WIDTH 32
    } {
        aclk $fclk
        aresetn $f_aresetn
        sts_data pattern_valid_concat_0/Dout
    }
    # Create all required interconnections
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
      Master /ps_0/M_AXI_GP0
      Clk        Auto
    } [get_bd_intf_pins adc_sts_0/S_AXI]
    set_property range 4K [get_bd_addr_segs {ps_0/Data/SEG_adc_sts_0_reg0}]
    set_property offset 0x40003000 [get_bd_addr_segs {ps_0/Data/SEG_adc_sts_0_reg0}]
} else {
    cell xilinx.com:ip:clk_wiz:6.0 pll_0 {
      PRIMITIVE MMCM
      PRIM_IN_FREQ.VALUE_SRC USER
      PRIM_IN_FREQ 125.0
      PRIM_SOURCE Differential_clock_capable_pin
      CLKOUT1_USED true
      CLKOUT1_REQUESTED_OUT_FREQ 125.0
      CLKOUT2_USED true
      CLKOUT2_REQUESTED_OUT_FREQ 250.0
      CLKOUT2_REQUESTED_PHASE -90.0
      USE_RESET false
    } {
      clk_in1_p adc_clk_p_i
      clk_in1_n adc_clk_n_i
    }
    set adc_clk    /pll_0/clk_out1
    set dac_clk    /pll_0/clk_out1
    set dac_clk_locked /pll_0/locked
    set dac_ddr_clk /pll_0/clk_out2
    connect_bd_net [get_bd_pins rp_adc_0/f_clk]             [get_bd_pins  $fclk]           
    connect_bd_net [get_bd_pins rp_adc_0/adc_clk]           [get_bd_pins  $adc_clk]           
    connect_bd_net [get_bd_pins rp_adc_0/adc_clk_locked]    [get_bd_pins  $dac_clk_locked]    
    connect_bd_net [get_bd_pins rp_adc_0/adc_csn_o]         [get_bd_ports adc_csn_o]          
    connect_bd_net [get_bd_pins rp_adc_0/adc_0_data_i]      [get_bd_ports adc_dat_a_i]        
    connect_bd_net [get_bd_pins rp_adc_0/adc_1_data_i]      [get_bd_ports adc_dat_b_i]        
}

#gate
create_bd_cell -type module -reference sync_external_pulse detect_gate_0
connect_bd_net [get_bd_pins detect_gate_0/aclk]    [get_bd_pins $fclk]
connect_bd_net [get_bd_pins detect_gate_0/aresetn] [get_bd_pins $f_aresetn]

cell xilinx.com:ip:util_ds_buf ibufds_trigger_0 {
    C_BUF_TYPE IBUFDS
} {
    IBUF_DS_P sata_s1_b_p
    IBUF_DS_N sata_s1_b_n
}
connect_bd_net [get_bd_pins ibufds_trigger_0/IBUF_OUT] [get_bd_pins detect_gate_0/external_input]
cell xilinx.com:ip:xlslice:1.0 gate_enable_0 {
    DIN_WIDTH 32
    DIN_FROM 0
    DIN_TO 0
} {
    Din cfg8/config_5
}

cell xilinx.com:ip:util_vector_logic:2.0 gate_0 {
    C_SIZE 1
    C_OPERATION AND
} {
    Op1 gate_enable_0/Dout
    Op2 detect_gate_0/pulse_detected
}


if { [dict get $pl_param_dict modulated] == "TRUE"} {
    module nco_0 {
        source projects/scope/nco.tcl
    } {
      slice_1/Din nco_slice_0/Dout
    }
    save_bd_design
}

set rx_status_width [expr 1 + [dict get $pl_param_dict rx_channel_count]]
cell xilinx.com:ip:xlconcat:2.1 rx_status_concat_0 {
    NUM_PORTS $rx_status_width
}
set rx_channel_count [dict get $pl_param_dict rx_channel_count]
for {set i 0} {$i < $rx_channel_count} {incr i} {
    module rx_${i} {
      source projects/scope/rx2.tcl
    } {
      axis_acq_trigger_0/gate gate_0/Res
      rate_slice/Din        rx_slice_0/Dout
      fifo_0/S_AXIS         rp_adc_0/M${i}_AXIS
      fifo_0/s_axis_aclk    rp_adc_0/adc_${i}_clk
      fifo_0/s_axis_aresetn rp_adc_0/adc_${i}_resetn
      axis_dma_rx_0/busy    rx_status_concat_0/In${i}
    }
    # Connect NCO if necessary      
    if { [dict get $pl_param_dict modulated] == "TRUE"} {
        connect_bd_intf_net [get_bd_intf_pins rx_${i}/mult_0/S_AXIS_B] [get_bd_intf_pins nco_0/bcast_nco/M0${i}_AXIS]
    }

    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [subst {
      Clk_xbar $ps_clk
      Master  /rx_${i}/axi_datamover_0/M_AXI_S2MM
      Slave   /ps_0/S_AXI_HP${i}
      intc_ip {New AXI Interconnect}
    }] [get_bd_intf_pins ps_0/S_AXI_HP${i}]
    connect_bd_intf_net [get_bd_intf_pins rx_${i}/axi_sniffer_0/S_AXI] -boundary_type upper [get_bd_intf_pins rx_${i}/axi_datamover_0/M_AXI_S2MM]
    set_property range 1G [get_bd_addr_segs rx_${i}/axi_datamover_0/Data_S2MM/SEG_ps_0_HP${i}_DDR_LOWOCM]

    if {$i==0} {
        set suffix ""
    } else {
        set suffix _$i
    }
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
      Master    /ps_0/M_AXI_GP0
      Clk       Auto
    } [get_bd_intf_pins rx_${i}/axis_dma_rx_0/S_AXI]
    set_property RANGE  4K             [get_bd_addr_segs ps_0/Data/SEG_axis_dma_rx_0_reg0${suffix}]
    set_property OFFSET 0x6000${i}000  [get_bd_addr_segs ps_0/Data/SEG_axis_dma_rx_0_reg0${suffix}]
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
      Master    /ps_0/M_AXI_GP0
      Clk       Auto
    } [get_bd_intf_pins rx_${i}/axis_acq_trigger_0/S_AXI]
    set_property RANGE  4K             [get_bd_addr_segs ps_0/Data/SEG_axis_acq_trigger_0_reg0${suffix}]
    set_property OFFSET 0x4006${i}000  [get_bd_addr_segs ps_0/Data/SEG_axis_acq_trigger_0_reg0${suffix}]
}

# Create xlconstant

cell xilinx.com:ip:xlconstant:1.1 const_sts_0 {
  CONST_WIDTH [expr 32 - $rx_channel_count]
  CONST_VAL 0
} {
}
connect_bd_net [get_bd_pins const_sts_0/Dout] [get_bd_pins rx_status_concat_0/In$rx_channel_count]

# Create axi_sts_register
cell pavel-demin:user:axi_sts_register:1.0 sts_0 {
  STS_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  AXI_DATA_WIDTH 32
} {
  aclk $fclk
  aresetn $f_aresetn
  sts_data rx_status_concat_0/dout
}
save_bd_design
# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master     /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins cfg8/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_cfg8_reg0]
set_property OFFSET 0x40000000 [get_bd_addr_segs ps_0/Data/SEG_cfg8_reg0]

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins sts_0/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_sts_0_reg0]
set_property OFFSET 0x40001000 [get_bd_addr_segs ps_0/Data/SEG_sts_0_reg0]

# Create IRQ concatenator
set irq_width [expr 3 + [dict get $pl_param_dict rx_channel_count]]
cell xilinx.com:ip:xlconcat:2.1 irq_concat_0 {
    NUM_PORTS $irq_width
}
connect_bd_net [get_bd_pins irq_concat_0/In0] [get_bd_pins gate_0/Res]
connect_bd_net [get_bd_pins irq_concat_0/In1] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins irq_concat_0/In2] [get_bd_pins const_low/Dout]
save_bd_design
for {set i 0} {$i < [dict get $pl_param_dict rx_channel_count]} {incr i} {
    connect_bd_net [get_bd_pins irq_concat_0/In[expr 3+$i]] [get_bd_pins /rx_${i}/axis_dma_rx_0/i_rq]
}
connect_bd_net [get_bd_pins irq_concat_0/Dout] [get_bd_pins /ps_0/IRQ_F2P]

#
# hook up the event pulses to something
#

# the LEDs
cell xilinx.com:ip:xlconstant:1.1 const_led_high
set_property -dict [list CONFIG.CONST_WIDTH {7} CONFIG.CONST_VAL {0x7F}] [get_bd_cells const_led_high]
cell xilinx.com:ip:xlconcat:2.1 led_concat_0 {
    NUM_PORTS 2
}
connect_bd_net [get_bd_pins led_concat_0/In0] [get_bd_pins ibufds_trigger_0/IBUF_OUT]
connect_bd_net [get_bd_pins led_concat_0/In1] [get_bd_pins const_led_high/Dout]
connect_bd_net [get_bd_ports led_o] [get_bd_pins led_concat_0/Dout]

# try to connect the bottom 8 bits of the pulse output of the sequencer to the positive gpoi
#
# Delete input/output port
delete_bd_objs [get_bd_ports exp_p_tri_io*]
delete_bd_objs [get_bd_ports exp_n_tri_io*]

# Create newoutput port
create_bd_port -dir O -from 7 -to 0 exp_p_tri_io

# Create output port for the SPI stuff
create_bd_port -dir O -from 7 -to 0 exp_n_tri_io


save_bd_design
# Input / Output
# exp_p_tri_io [7:0] - output
cell xilinx.com:ip:xlconcat:2.1 pio_concat_0 {
    NUM_PORTS 8
}
connect_bd_net [get_bd_pins pio_concat_0/In0] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In1] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In2] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In3] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In4] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In5] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In6] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins pio_concat_0/In7] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins exp_p_tri_io] [get_bd_pins pio_concat_0/Dout]
# exp_n_tri_io [7:0] - output
cell xilinx.com:ip:xlconcat:2.1 nio_concat_0 {
    NUM_PORTS 8
}
connect_bd_net [get_bd_pins nio_concat_0/In0] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In1] [get_bd_pins const_high/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In2] [get_bd_pins const_high/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In3] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In4] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In5] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In6] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins nio_concat_0/In7] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_pins exp_n_tri_io] [get_bd_pins nio_concat_0/Dout]