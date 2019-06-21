# Create processing_system7
cell xilinx.com:ip:processing_system7:5.5 ps_0 {
  PCW_IMPORT_BOARD_PRESET cfg/red_pitaya.xml
} {
  M_AXI_GP0_ACLK ps_0/FCLK_CLK0
}

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 -config {
  make_external {FIXED_IO, DDR}
  Master Disable
  Slave Disable
} [get_bd_cells ps_0]

# Create proc_sys_reset
cell xilinx.com:ip:proc_sys_reset:5.0 rst_0

# Create clk_wiz
# (using v5.4 is also an option)
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

# ADC

# Create axis_red_pitaya_adc
cell pavel-demin:user:axis_red_pitaya_adc:2.0 adc_0 {} {
  aclk pll_0/clk_out1
  adc_dat_a adc_dat_a_i
  adc_dat_b adc_dat_b_i
  adc_csn adc_csn_o
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

# Create axi_cfg_register
cell pavel-demin:user:axi_cfg_register:1.0 cfg_0 {
  CFG_DATA_WIDTH 128
  AXI_ADDR_WIDTH 32
  AXI_DATA_WIDTH 32
}

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 txinterpolator_slice_0 {
  DIN_WIDTH 128 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
} {
  Din cfg_0/cfg_data
}

# Create xlslice
#cell xilinx.com:ip:xlslice:1.0 rst_slice_1 {
#  DIN_WIDTH 128 DIN_FROM 15 DIN_TO 8 DOUT_WIDTH 8
#} {
#  Din cfg_0/cfg_data
#}

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 cfg_slice_0 {
  DIN_WIDTH 128 DIN_FROM 95 DIN_TO 32 DOUT_WIDTH 64
} {
  Din cfg_0/cfg_data
}

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 cfg_slice_1 {
  DIN_WIDTH 128 DIN_FROM 127 DIN_TO 96 DOUT_WIDTH 32
} {
  Din cfg_0/cfg_data
}

# Create xlconstant
cell xilinx.com:ip:xlconstant:1.1 const_0

# Removed this connection from rx:
# slice_0/Din rst_slice_0/Dout
module rx_0 {
  source projects/ocra_mri/rx2.tcl
} {
  rate_slice/Din cfg_slice_0/Dout
  fifo_0/S_AXIS adc_0/M_AXIS
  fifo_0/s_axis_aclk pll_0/clk_out1
  fifo_0/s_axis_aresetn const_0/dout
}

#  axis_interpolator_0/cfg_data txinterpolator_slice_0/Dout  
module tx_0 {
  source projects/ocra_mri/tx6.tcl
} {
  slice_1/Din cfg_slice_1/Dout
  axis_interpolator_0/cfg_data txinterpolator_slice_0/Dout
  fifo_1/M_AXIS dac_0/S_AXIS
  fifo_1/m_axis_aclk pll_0/clk_out1
  fifo_1/m_axis_aresetn const_0/dout
}

module nco_0 {
    source projects/ocra_mri/nco.tcl
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
  sts_data rx_0/fifo_generator_0/rd_data_count
}

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins cfg_0/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_cfg_0_reg0]
set_property OFFSET 0x40000000 [get_bd_addr_segs ps_0/Data/SEG_cfg_0_reg0]

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins sts_0/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_sts_0_reg0]
set_property OFFSET 0x40001000 [get_bd_addr_segs ps_0/Data/SEG_sts_0_reg0]

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins rx_0/reader_0/S_AXI]

set_property RANGE 256K [get_bd_addr_segs ps_0/Data/SEG_reader_0_reg0]
set_property OFFSET 0x40100000 [get_bd_addr_segs ps_0/Data/SEG_reader_0_reg0]

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins tx_0/writer_0/S_AXI]

set_property RANGE 128K [get_bd_addr_segs ps_0/Data/SEG_writer_0_reg0]
set_property OFFSET 0x40020000 [get_bd_addr_segs ps_0/Data/SEG_writer_0_reg0]

# Create Memory for pulse sequence
# (Could also use V8.3)
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
  Clk Auto
} [get_bd_intf_pins sequence_writer/S_AXI]

set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_sequence_writer_reg0]
set_property OFFSET 0x40070000 [get_bd_addr_segs ps_0/Data/SEG_sequence_writer_reg0]

# Create microsequencer
cell pavel-demin:user:micro_sequencer:1.0 micro_sequencer {
  C_S_AXI_DATA_WIDTH 32
  C_S_AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 64
  BRAM_ADDR_WIDTH 13
} {
  BRAM_PORTA sequence_memory/BRAM_PORTB
}

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins micro_sequencer/S_AXI]

set_property RANGE 4K [get_bd_addr_segs ps_0/Data/SEG_micro_sequencer_reg0]
set_property OFFSET 0x40080000 [get_bd_addr_segs ps_0/Data/SEG_micro_sequencer_reg0]

# Create Memory for gradient waveform
cell xilinx.com:ip:blk_mem_gen:8.4 gradient_memoryx {
  MEMORY_TYPE Simple_Dual_Port_RAM
  USE_BRAM_BLOCK Stand_Alone
  WRITE_WIDTH_A 32
  WRITE_DEPTH_A 4000
  WRITE_WIDTH_B 32
  ENABLE_A Always_Enabled
  ENABLE_B Always_Enabled
  REGISTER_PORTB_OUTPUT_OF_MEMORY_PRIMITIVES false
}

cell xilinx.com:ip:blk_mem_gen:8.4 gradient_memoryy {
  MEMORY_TYPE Simple_Dual_Port_RAM
  USE_BRAM_BLOCK Stand_Alone
  WRITE_WIDTH_A 32
  WRITE_DEPTH_A 4000
  WRITE_WIDTH_B 32
  ENABLE_A Always_Enabled
  ENABLE_B Always_Enabled
  REGISTER_PORTB_OUTPUT_OF_MEMORY_PRIMITIVES false
}
cell xilinx.com:ip:blk_mem_gen:8.4 gradient_memoryz {
  MEMORY_TYPE Simple_Dual_Port_RAM
  USE_BRAM_BLOCK Stand_Alone
  WRITE_WIDTH_A 32
  WRITE_DEPTH_A 4000
  WRITE_WIDTH_B 32
  ENABLE_A Always_Enabled
  ENABLE_B Always_Enabled
  REGISTER_PORTB_OUTPUT_OF_MEMORY_PRIMITIVES false
}

# Create axi_bram_writer for gradient waveform
cell pavel-demin:user:axi_bram_writer:1.0 gradient_writerx {
  AXI_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 32
  BRAM_ADDR_WIDTH 14
} {
  BRAM_PORTA gradient_memoryx/BRAM_PORTA
}
cell pavel-demin:user:axi_bram_writer:1.0 gradient_writery {
  AXI_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 32
  BRAM_ADDR_WIDTH 14
} {
  BRAM_PORTA gradient_memoryy/BRAM_PORTA
}
cell pavel-demin:user:axi_bram_writer:1.0 gradient_writerz {
  AXI_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 32
  BRAM_ADDR_WIDTH 14
} {
  BRAM_PORTA gradient_memoryz/BRAM_PORTA
}


# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins gradient_writerx/S_AXI]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins gradient_writery/S_AXI]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins gradient_writerz/S_AXI]

set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_gradient_writerx_reg0]
set_property OFFSET 0x400A0000 [get_bd_addr_segs ps_0/Data/SEG_gradient_writerx_reg0]
set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_gradient_writery_reg0]
set_property OFFSET 0x400B0000 [get_bd_addr_segs ps_0/Data/SEG_gradient_writery_reg0]
set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_gradient_writerz_reg0]
set_property OFFSET 0x400C0000 [get_bd_addr_segs ps_0/Data/SEG_gradient_writerz_reg0]

module gradient_dac_0 {
    source projects/ocra_mri/gradient_dacs.tcl
} {
    spi_sequencer_0/BRAM_PORTX gradient_memoryx/BRAM_PORTB
    spi_sequencer_0/BRAM_PORTY gradient_memoryy/BRAM_PORTB
    spi_sequencer_0/BRAM_PORTZ gradient_memoryz/BRAM_PORTB
}

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins gradient_dac_0/spi_sequencer_0/S_AXI]

set_property RANGE  4K [get_bd_addr_segs ps_0/Data/SEG_spi_sequencer_0_reg0]
set_property OFFSET 0x40090000 [get_bd_addr_segs ps_0/Data/SEG_spi_sequencer_0_reg0]

#
# hook up the event pulses to something
#

# the LEDs
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 xlslice_0
set_property -dict [list CONFIG.DIN_WIDTH {64} CONFIG.DIN_TO {8} CONFIG.DIN_FROM {15} CONFIG.DIN_TO {8} CONFIG.DIN_FROM {15} CONFIG.DOUT_WIDTH {8}] [get_bd_cells xlslice_0]
connect_bd_net [get_bd_pins micro_sequencer/pulse] [get_bd_pins xlslice_0/Din]
connect_bd_net [get_bd_ports led_o] [get_bd_pins xlslice_0/Dout]

# the transmit trigger pulse
create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 trigger_slice_0
set_property -dict [list CONFIG.DIN_WIDTH {64} CONFIG.DIN_FROM {7} CONFIG.DIN_TO {0} CONFIG.DOUT_WIDTH {8}] [get_bd_cells trigger_slice_0]
connect_bd_net [get_bd_pins micro_sequencer/pulse] [get_bd_pins trigger_slice_0/Din]
connect_bd_net [get_bd_pins trigger_slice_0/Dout] [get_bd_pins tx_0/slice_0/Din]
connect_bd_net [get_bd_pins trigger_slice_0/Dout] [get_bd_pins rx_0/slice_0/Din]

# the gradient DAC pulse
connect_bd_net [get_bd_pins trigger_slice_0/Dout] [get_bd_pins gradient_dac_0/slice_0/Din]

# connect the tx_offset
connect_bd_net [get_bd_pins micro_sequencer/tx_offset] [get_bd_pins tx_0/reader_0/current_offset]
# connect the grad_offset
connect_bd_net [get_bd_pins micro_sequencer/grad_offset] [get_bd_pins gradient_dac_0/spi_sequencer_0/current_offset]

# TW add one output register stage
set_property -dict [list CONFIG.Register_PortB_Output_of_Memory_Primitives {true} CONFIG.Register_PortB_Output_of_Memory_Core {false}] [get_bd_cells sequence_memory]

# The RAM for the gradients should not have wait states?
set_property -dict [list CONFIG.Register_PortB_Output_of_Memory_Primitives {true} CONFIG.Register_PortB_Output_of_Memory_Core {false}] [get_bd_cells gradient_memoryx]
set_property -dict [list CONFIG.Register_PortB_Output_of_Memory_Primitives {true} CONFIG.Register_PortB_Output_of_Memory_Core {false}] [get_bd_cells gradient_memoryy]
set_property -dict [list CONFIG.Register_PortB_Output_of_Memory_Primitives {true} CONFIG.Register_PortB_Output_of_Memory_Core {false}] [get_bd_cells gradient_memoryz]
#
# try to connect the bottom 8 bits of the pulse output of the sequencer to the positive gpoi
#
# Delete input/output port
delete_bd_objs [get_bd_ports exp_p_tri_io]
delete_bd_objs [get_bd_ports exp_n_tri_io]

# Create newoutput port
create_bd_port -dir O -from 7 -to 0 exp_p_tri_io
connect_bd_net [get_bd_pins exp_p_tri_io] [get_bd_pins trigger_slice_0/Dout]

# Create output port for the SPI stuff
create_bd_port -dir O -from 7 -to 0 exp_n_tri_io
connect_bd_net [get_bd_pins exp_n_tri_io] [get_bd_pins gradient_dac_0/spiconcat_0/Dout]

