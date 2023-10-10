global board_name
global project_name

set ps_preset boards/${board_name}/ps_${project_name}.xml

# Create processing_system7
cell xilinx.com:ip:processing_system7:5.5 ps_0 {
  PCW_IMPORT_BOARD_PRESET $ps_preset
  PCW_USE_S_AXI_HP0 1
  PCW_USE_FABRIC_INTERRUPT 1
  PCW_IRQ_F2P_INTR 1 
} {
  M_AXI_GP0_ACLK ps_0/FCLK_CLK0
  S_AXI_HP0_ACLK ps_0/FCLK_CLK0
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

# Create clk_wiz
cell xilinx.com:ip:clk_wiz:6.0 pll_0 {
  PRIMITIVE PLL
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

# clocks and resets
set ps_clk /ps_0/FCLK_CLK0
set ps_aresetn /rst_0/peripheral_aresetn
set ps_reset   /rst_0/peripheral_reset

cell xilinx.com:ip:proc_sys_reset:5.0 rst_125_0
connect_bd_net [get_bd_pins ps_0/FCLK_RESET0_N] [get_bd_pins rst_125_0/ext_reset_in]
connect_bd_net [get_bd_pins pll_0/clk_out1]     [get_bd_pins rst_125_0/slowest_sync_clk]
set fclk /pll_0/clk_out1
set f_aresetn /rst_125_0/peripheral_aresetn
set f_reset   /rst_125_0/peripheral_reset

# Create axi_cfg_register
cell pavel-demin:user:axi_cfg_register:1.0 cfg_0 {
  CFG_DATA_WIDTH 128
  AXI_ADDR_WIDTH 32
  AXI_DATA_WIDTH 32
} {
  aclk $fclk
  aresetn $f_aresetn
}

# Create slice with the TX configuration, which uses the bottom 32 bits
cell xilinx.com:ip:xlslice:1.0 txinterpolator_slice_0 {
  DIN_WIDTH 128 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
} {
  Din cfg_0/cfg_data
}

# Create slice with the RX configuration and NCO configuration
# RX seems to use the bottom 16 bit of the upper 32 bit
# NCO uses the bottom 32 bit
# Bits 63 to 48 seem free, USING bits 49,48 FOR ADC switch then
cell xilinx.com:ip:xlslice:1.0 cfg_slice_0 {
  DIN_WIDTH 128 DIN_FROM 95 DIN_TO 32 DOUT_WIDTH 64
} {
  Din cfg_0/cfg_data
}

# ADC switch slice
cell xilinx.com:ip:xlslice:1.0 cfg_adc_switch {
  DIN_WIDTH 128 DIN_FROM 49 DIN_TO 48 DOUT_WIDTH 2
} {
  Din cfg_0/cfg_data
}

# Create another slice with data for the TX, which is another 32 bit
cell xilinx.com:ip:xlslice:1.0 cfg_slice_1 {
  DIN_WIDTH 128 DIN_FROM 127 DIN_TO 96 DOUT_WIDTH 32
} {
  Din cfg_0/cfg_data
}
# ADC

# Create axis_red_pitaya_adc
cell open-mri:user:axis_red_pitaya_adc:3.0 adc_0 {} {
  aclk pll_0/clk_out1
  adc_dat_a adc_dat_a_i
  adc_dat_b adc_dat_b_i
  adc_csn adc_csn_o
    adc_channel_switch cfg_adc_switch/Dout
}

# Create axis_red_pitaya_dac
cell pavel-demin:user:axis_red_pitaya_dac:1.0 dac_0 {} {
  aclk pll_0/clk_out1
  ddr_clk pll_0/clk_out2
  locked pll_0/locked
  dac_clk dac_clk_o
  dac_rst dac_rst_o
  dac_sel dac_sel_o
  dac_wrt dac_wrt_o
  dac_dat dac_dat_o
}


# Create xlconstant
cell xilinx.com:ip:xlconstant:1.1 const_0
cell xilinx.com:ip:xlconstant:1.1 const_sts_0
set_property -dict [list CONFIG.CONST_WIDTH {32} CONFIG.CONST_VAL {0}] [get_bd_cells const_sts_0]

# Removed this connection from rx:
# slice_0/Din rst_slice_0/Dout
module rx_0 {
  source projects/scope/rx2.tcl
} {
  rate_slice/Din cfg_slice_0/Dout
  fifo_0/S_AXIS adc_0/M_AXIS
  fifo_0/s_axis_aclk pll_0/clk_out1
  fifo_0/s_axis_aresetn const_0/dout
}
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Clk_xbar $ps_clk
  Master  {/rx_0/axi_datamover_0/M_AXI_S2MM}
  Slave   {/ps_0/S_AXI_HP0}
  intc_ip {New AXI Interconnect}
} [get_bd_intf_pins ps_0/S_AXI_HP0]
connect_bd_intf_net [get_bd_intf_pins rx_0/axi_sniffer_0/S_AXI] -boundary_type upper [get_bd_intf_pins rx_0/axi_datamover_0/M_AXI_S2MM]
set_property range 1G [get_bd_addr_segs {rx_0/axi_datamover_0/Data_S2MM/SEG_ps_0_HP0_DDR_LOWOCM}]

#  axis_interpolator_0/cfg_data txinterpolator_slice_0/Dout  
module tx_0 {
  source projects/scope/tx6.tcl
} {
  slice_1/Din cfg_slice_1/Dout
  axis_interpolator_0/cfg_data txinterpolator_slice_0/Dout
  fifo_1/M_AXIS dac_0/S_AXIS
  fifo_1/m_axis_aclk pll_0/clk_out1
  fifo_1/m_axis_aresetn const_0/dout
}

module nco_0 {
    source projects/scope/nco.tcl
} {
  slice_1/Din cfg_slice_0/Dout
  bcast_nco/M00_AXIS rx_0/mult_0/S_AXIS_B
  bcast_nco/M01_AXIS tx_0/mult_0/S_AXIS_B
}

# Create axi_sts_register
cell pavel-demin:user:axi_sts_register:1.0 sts_0 {
  STS_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  AXI_DATA_WIDTH 32
} {
  aclk $fclk
  aresetn $f_aresetn
  sts_data const_sts_0/dout
}
save_bd_design
# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master     /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins cfg_0/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_cfg_0_reg0]
set_property OFFSET 0x40000000 [get_bd_addr_segs ps_0/Data/SEG_cfg_0_reg0]

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins sts_0/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_sts_0_reg0]
set_property OFFSET 0x40001000 [get_bd_addr_segs ps_0/Data/SEG_sts_0_reg0]
save_bd_design

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins rx_0/axis_dma_rx_0/S_AXI]

set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_axis_dma_rx_0_reg0]
set_property OFFSET 0x40010000 [get_bd_addr_segs ps_0/Data/SEG_axis_dma_rx_0_reg0]

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins tx_0/writer_0/S_AXI]

set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_writer_0_reg0]
set_property OFFSET 0x40020000 [get_bd_addr_segs ps_0/Data/SEG_writer_0_reg0]

# Create Memory for pulse sequence
cell xilinx.com:ip:blk_mem_gen:8.4 sequence_memory {
  MEMORY_TYPE Simple_Dual_Port_RAM
  USE_BRAM_BLOCK Stand_Alone
  WRITE_WIDTH_A 32
  WRITE_DEPTH_A 16384
  WRITE_WIDTH_B 64
  ENABLE_A Always_Enabled
  ENABLE_B Always_Enabled
  REGISTER_PORTB_OUTPUT_OF_MEMORY_PRIMITIVES false
}

# Load some initial data to the memory
#set_property -dict [list CONFIG.Load_Init_File {true} CONFIG.Coe_File {/home/red-pitaya/red-pitaya-notes.old/test.coe}] [get_bd_cells sequence_memory]

# Create axi_bram_writer for pulse sequence
cell pavel-demin:user:axi_bram_writer:1.0 sequence_writer {
  AXI_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 32
  BRAM_ADDR_WIDTH 14
} {
  BRAM_PORTA sequence_memory/BRAM_PORTA
}

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk_slave $fclk
} [get_bd_intf_pins sequence_writer/S_AXI]

set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_sequence_writer_reg0]
set_property OFFSET 0x40030000 [get_bd_addr_segs ps_0/Data/SEG_sequence_writer_reg0]

create_bd_cell -type module -reference sync_external_pulse detect_unpause_pulse_0
connect_bd_net [get_bd_pins detect_unpause_pulse_0/aclk]    [get_bd_pins $fclk]
connect_bd_net [get_bd_pins detect_unpause_pulse_0/aresetn] [get_bd_pins $f_aresetn]

# Create microsequencer
cell open-mri:user:micro_sequencer:1.0 micro_sequencer {
  C_S_AXI_DATA_WIDTH 32
  C_S_AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 64
  BRAM_ADDR_WIDTH 13
} {
  BRAM_PORTA sequence_memory/BRAM_PORTB
  S_AXI_ACLK $fclk
  S_AXI_ARESETN $f_aresetn
  unpause detect_unpause_pulse_0/pulse_detected
}
# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins micro_sequencer/S_AXI]

set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_micro_sequencer_reg0]
set_property OFFSET 0x40040000 [get_bd_addr_segs ps_0/Data/SEG_micro_sequencer_reg0]

cell xilinx.com:ip:xlconcat:2.1 irq_concat_0 {
    NUM_PORTS 3
}
connect_bd_net [get_bd_pins irq_concat_0/In0] [get_bd_pins micro_sequencer/irq_halt]
connect_bd_net [get_bd_pins irq_concat_0/In1] [get_bd_pins micro_sequencer/irq_litr]
connect_bd_net [get_bd_pins irq_concat_0/In2] [get_bd_pins rx_0/axis_dma_rx_0/i_rq]
connect_bd_net [get_bd_pins irq_concat_0/Dout] [get_bd_pins /ps_0/IRQ_F2P]

# Create RF attenuator
cell open-mri:user:axi_serial_attenuator:1.0 serial_attenuator {
  C_S_AXI_DATA_WIDTH 32
  C_S_AXI_ADDR_WIDTH 16
} {
  S_AXI_ACLK $fclk
  S_AXI_ARESETN $f_aresetn
}
# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk        Auto
} [get_bd_intf_pins serial_attenuator/S_AXI]
set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_serial_attenuator_reg0]
set_property OFFSET 0x40050000 [get_bd_addr_segs ps_0/Data/SEG_serial_attenuator_reg0]

#
# hook up the event pulses to something
#

# the LEDs
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 xled_slice_0
set_property -dict [list CONFIG.DIN_WIDTH {64} CONFIG.DIN_TO {8} CONFIG.DIN_FROM {15} CONFIG.DOUT_WIDTH {8}] [get_bd_cells xled_slice_0]
connect_bd_net [get_bd_pins micro_sequencer/pulse] [get_bd_pins xled_slice_0/Din]
connect_bd_net [get_bd_ports led_o] [get_bd_pins xled_slice_0/Dout]

# the transmit trigger pulse
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 trigger_slice_0
set_property -dict [list CONFIG.DIN_WIDTH {64} CONFIG.DIN_FROM {7} CONFIG.DIN_TO {0} CONFIG.DOUT_WIDTH {8}] [get_bd_cells trigger_slice_0]
connect_bd_net [get_bd_pins micro_sequencer/pulse] [get_bd_pins trigger_slice_0/Din]
connect_bd_net [get_bd_pins trigger_slice_0/Dout] [get_bd_pins tx_0/slice_0/Din]
connect_bd_net [get_bd_pins trigger_slice_0/Dout] [get_bd_pins rx_0/slice_0/Din]

# connect the tx_offset
connect_bd_net [get_bd_pins micro_sequencer/tx_offset] [get_bd_pins tx_0/reader_0/current_offset]

# TW add one output register stage
set_property -dict [list CONFIG.Register_PortB_Output_of_Memory_Primitives {true} CONFIG.Register_PortB_Output_of_Memory_Core {false}] [get_bd_cells sequence_memory]

# try to connect the bottom 8 bits of the pulse output of the sequencer to the positive gpoi
#
# Delete input/output port
delete_bd_objs [get_bd_ports exp_p_tri_io_*]
delete_bd_objs [get_bd_ports exp_n_tri_io_*]

# Create newoutput port
for {set i 0} {$i < 4} {incr i} {
    create_bd_port -dir O exp_p_tri_io_$i
}
for {set i 4} {$i < 8} {incr i} {
    create_bd_port -dir I exp_p_tri_io_$i
}

# Create output port for the SPI stuff
for {set i 0} {$i < 8} {incr i} {
    create_bd_port -dir O exp_n_tri_io_$i
}

# 09/2019: For the new board we are doing this differently. The SPI bus will use seven pins on the n side of the header
#          and the txgate will use the eight' pin on the n side

# Slice the txgate off the microsequencer pulse word. I'm torn on style here, but the trigger slice is almost obsolete,
# so its easier to not use it
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 txgate_slice_0
set_property -dict [list CONFIG.DIN_WIDTH {64} CONFIG.DIN_FROM {4} CONFIG.DIN_TO {4} CONFIG.DOUT_WIDTH {1}] [get_bd_cells txgate_slice_0]
connect_bd_net [get_bd_pins micro_sequencer/pulse] [get_bd_pins txgate_slice_0/Din]

# Input / Output
cell xilinx.com:ip:xlconstant:1.1 const_low
cell xilinx.com:ip:xlconstant:1.1 const_high
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}] [get_bd_cells const_low]
set_property -dict [list CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}] [get_bd_cells const_high]
# exp_p_tri_io [3:0] - output
connect_bd_net [get_bd_ports exp_p_tri_io_0] [get_bd_pins serial_attenuator/attn_clk]
connect_bd_net [get_bd_ports exp_p_tri_io_1] [get_bd_pins serial_attenuator/attn_serial]
connect_bd_net [get_bd_ports exp_p_tri_io_2] [get_bd_pins serial_attenuator/attn_le]
connect_bd_net [get_bd_ports exp_p_tri_io_3] [get_bd_pins const_low/Dout]
# exp_p_tri_io [7:4] - input
connect_bd_net [get_bd_ports exp_p_tri_io_4] [get_bd_pins detect_unpause_pulse_0/external_input]
# exp_n_tri_io [7:0] - output
connect_bd_net [get_bd_ports exp_n_tri_io_0] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_1] [get_bd_pins const_high/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_2] [get_bd_pins const_high/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_3] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_4] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_5] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_6] [get_bd_pins const_low/Dout]
connect_bd_net [get_bd_ports exp_n_tri_io_7] [get_bd_pins txgate_slice_0/Dout]