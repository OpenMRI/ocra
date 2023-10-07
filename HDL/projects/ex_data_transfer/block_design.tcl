global board_name
global project_name

set ps_preset boards/${board_name}/ps_${project_name}.xml

#set target -> to ddr or to local bram
#set dma_target "ddr"
set dma_target "bram"

# Create processing_system7
if {$dma_target eq "ddr"} {
  set ps_0_pcw_use_s_axi_hp0 1
} else {
  set ps_0_pcw_use_s_axi_hp0 0
}
cell xilinx.com:ip:processing_system7:5.5 ps_0 {
  PCW_IMPORT_BOARD_PRESET $ps_preset
  PCW_USE_S_AXI_HP0 $ps_0_pcw_use_s_axi_hp0 
  PCW_USE_FABRIC_INTERRUPT 1
  PCW_IRQ_F2P_INTR 1 
} {
  M_AXI_GP0_ACLK ps_0/FCLK_CLK0
}
if {$dma_target eq "ddr"} {
 connect_bd_net [get_bd_pins ps_0/S_AXI_HP0_ACLK] [get_bd_pins ps_0/FCLK_CLK0]
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

# clocks and resets
set ps_clk /ps_0/FCLK_CLK0
set ps_aresetn /rst_0/peripheral_aresetn
set ps_reset   /rst_0/peripheral_reset

# Create axi stream
cell xilinx.com:ip:c_counter_binary:12.0 binary_counter_0 {
  Output_Width 64
} {
  CLK $ps_clk
}
cell pavel-demin:user:axis_constant:1.0 axis_constant_0 {
  AXIS_TDATA_WIDTH 64
} {
  aclk $ps_clk
  cfg_data binary_counter_0/Q
}

# Data Transfer
cell open-mri:user:axis_dma_rx:1.0 axis_dma_rx_0 {
  C_S_AXI_ADDR_WIDTH 16
  C_S_AXI_DATA_WIDTH 32
  C_AXIS_TDATA_WIDTH 64
} {
  aclk      $ps_clk
  aresetn   $ps_aresetn
  S_AXIS    axis_constant_0/M_AXIS
  i_rq      /ps_0/IRQ_F2P
}

cell xilinx.com:ip:axi_datamover:5.1 axi_datamover_0 {
  c_include_mm2s            Omit
  c_include_mm2s_stsfifo    false
  c_m_axi_s2mm_data_width   64
  c_s_axis_s2mm_tdata_width 64
  c_s2mm_support_indet_btt  true
  c_enable_mm2s             0
} {
  m_axi_s2mm_aclk             $ps_clk
  m_axis_s2mm_cmdsts_awclk    $ps_clk
  m_axis_s2mm_cmdsts_aresetn  $ps_aresetn
  m_axi_s2mm_aresetn          $ps_aresetn
  s2mm_err                    axis_dma_rx_0/s2mm_err
  M_AXIS_S2MM_STS             axis_dma_rx_0/S_AXIS_S2MM_STS
  S_AXIS_S2MM                 axis_dma_rx_0/M_AXIS_S2MM
  S_AXIS_S2MM_CMD             axis_dma_rx_0/M_AXIS_S2MM_CMD
}
cell open-mri:user:axi_sniffer:1.0 axi_sniffer_0 {
  C_S_AXI_ADDR_WIDTH 32
  C_S_AXI_DATA_WIDTH 64
} {
  aclk      $ps_clk
  aresetn   $ps_aresetn
  bresp     axis_dma_rx_0/axi_mm_bresp
  bvalid    axis_dma_rx_0/axi_mm_bvalid
  bready    axis_dma_rx_0/axi_mm_bready
}
set_property CONFIG.PROTOCOL AXI4 [get_bd_intf_pins axi_sniffer_0/S_AXI]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master     /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins axis_dma_rx_0/S_AXI]
set_property range 64K [get_bd_addr_segs {ps_0/Data/SEG_axis_dma_rx_0_reg0}]
set_property offset 0x40010000 [get_bd_addr_segs {ps_0/Data/SEG_axis_dma_rx_0_reg0}]
save_bd_design

# gate
cell pavel-demin:user:axi_cfg_register:1.0 cfg_0 {
  CFG_DATA_WIDTH 32
  AXI_ADDR_WIDTH 16
  AXI_DATA_WIDTH 32
} {
  aclk $ps_clk
  aresetn $ps_aresetn
}
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master     /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins cfg_0/S_AXI]
set_property range 64K [get_bd_addr_segs {ps_0/Data/SEG_cfg_0_reg0}]
set_property offset 0x40000000 [get_bd_addr_segs {ps_0/Data/SEG_cfg_0_reg0}]

cell xilinx.com:ip:xlslice:1.0 gate_slice {
  DIN_WIDTH 32 DIN_FROM 0 DIN_TO 0 DOUT_WIDTH 1
} {
  Din cfg_0/cfg_data
}
create_bd_cell -type module -reference pulse_on_transition rx_gate_0
connect_bd_net [get_bd_pins rx_gate_0/aclk]     [get_bd_pins $ps_clk]
connect_bd_net [get_bd_pins rx_gate_0/aresetn]  [get_bd_pins $ps_aresetn]
connect_bd_net [get_bd_pins rx_gate_0/edge_transition_in]  [get_bd_pins gate_slice/Dout]
connect_bd_net [get_bd_pins rx_gate_0/pulse_out]  [get_bd_pins axis_dma_rx_0/gate]
save_bd_design

if {$dma_target eq "ddr"} {
  apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
    Clk        Auto 
    Master     {/axi_datamover_0/M_AXI_S2MM}
    Slave      ps_0/S_AXI_HP0
    intc_ip    {New AXI Interconnect}
  }  [get_bd_intf_pins ps_0/S_AXI_HP0]
  set_property range 1G [get_bd_addr_segs {axi_datamover_0/Data_S2MM/SEG_ps_0_HP0_DDR_LOWOCM}]
  save_bd_design
} else {
  #use bram as the datamover target
  
  #add regular mmap access to the bram
  cell xilinx.com:ip:axi_bram_ctrl:4.1 axi_bram_ctrl_0 {
    DATA_WIDTH 32
    SINGLE_PORT_BRAM 1
    PROTOCOL AXI4LITE
  } {
    s_axi_aclk $ps_clk
    s_axi_aresetn $ps_aresetn
  }
  apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
    Master     /ps_0/M_AXI_GP0
    Clk        Auto
  } [get_bd_intf_pins axi_bram_ctrl_0/S_AXI]
  set_property offset 0x42000000 [get_bd_addr_segs {ps_0/Data/SEG_axi_bram_ctrl_0_Mem0}]
  set_property range 8K [get_bd_addr_segs {ps_0/Data/SEG_axi_bram_ctrl_0_Mem0}]

  #add dma access to the bram
  cell xilinx.com:ip:axi_bram_ctrl:4.1 axi_bram_ctrl_1 {
    DATA_WIDTH 64
    SINGLE_PORT_BRAM 1
  } {
    s_axi_aclk $ps_clk
    s_axi_aresetn $ps_aresetn
  }
  apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
    Clk       Auto 
    Master    {/axi_datamover_0/M_AXI_S2MM}
    Slave     {/axi_bram_ctrl_1/S_AXI}
    intc_ip {New AXI SmartConnect} 
  }  [get_bd_intf_pins axi_bram_ctrl_1/S_AXI]
  set_property offset 0x42000000 [get_bd_addr_segs {axi_datamover_0/Data_S2MM/SEG_axi_bram_ctrl_1_Mem0}]
  set_property range 8K [get_bd_addr_segs {axi_datamover_0/Data_S2MM/SEG_axi_bram_ctrl_1_Mem0}]
  save_bd_design

  cell xilinx.com:ip:blk_mem_gen:8.4 blk_mem_gen_0 {
    Assume_Synchronous_Clk true
    Memory_Type True_Dual_Port_RAM
  } {
    BRAM_PORTA axi_bram_ctrl_0/BRAM_PORTA
    BRAM_PORTB axi_bram_ctrl_1/BRAM_PORTA
  }
  save_bd_design
}
connect_bd_intf_net [get_bd_intf_pins axi_sniffer_0/S_AXI] [get_bd_intf_pins axi_datamover_0/M_AXI_S2MM]
save_bd_design
