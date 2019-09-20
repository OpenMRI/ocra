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

# Create Memory for 8 channels of gradient waveform
# 2000 samples per channel
cell xilinx.com:ip:blk_mem_gen:8.4 gradient_memory_0 {
  MEMORY_TYPE Simple_Dual_Port_RAM
  USE_BRAM_BLOCK Stand_Alone
  WRITE_WIDTH_A 32
  WRITE_DEPTH_A 16000
  WRITE_WIDTH_B 32
  ENABLE_A Always_Enabled
  ENABLE_B Always_Enabled
  REGISTER_PORTB_OUTPUT_OF_MEMORY_PRIMITIVES false
}

# Create axi_bram_writer for gradient waveform
cell pavel-demin:user:axi_bram_writer:1.0 gradient_writer_0 {
  AXI_DATA_WIDTH 32
  AXI_ADDR_WIDTH 32
  BRAM_DATA_WIDTH 32
  BRAM_ADDR_WIDTH 11
} {
  BRAM_PORTA gradient_memory_0/BRAM_PORTA
}

# Create all required interconnections on AXI bus for waveform writer
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins gradient_writer_0/S_AXI]


set_property RANGE 64K [get_bd_addr_segs ps_0/Data/SEG_gradient_writer_0_reg0]
set_property OFFSET 0x40020000 [get_bd_addr_segs ps_0/Data/SEG_gradient_writer_0_reg0]

module shim_dac_0 {
    source projects/shim_controller/shim_dacs.tcl
} {
    spi_sequencer_0/BRAM_PORT0 gradient_memory_0/BRAM_PORTB
}

# Create all required interconnections on AXI bus for shim_dac controller
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
  Master /ps_0/M_AXI_GP0
  Clk Auto
} [get_bd_intf_pins shim_dac_0/spi_sequencer_0/S_AXI]

set_property RANGE  64K [get_bd_addr_segs ps_0/Data/SEG_spi_sequencer_0_reg0]
set_property OFFSET 0x40060000 [get_bd_addr_segs ps_0/Data/SEG_spi_sequencer_0_reg0]


# the gradient DAC trigger pulse
# connect_bd_net [get_bd_pins trigger_slice_0/Dout] [get_bd_pins shim_dac_0/slice_0/Din]

# The RAM for the gradients should not have wait states?
set_property -dict [list CONFIG.Register_PortB_Output_of_Memory_Primitives {true} CONFIG.Register_PortB_Output_of_Memory_Core {false}] [get_bd_cells gradient_memory_0]

#
# try to connect the bottom 8 bits of the pulse output of the sequencer to the positive gpoi
#
# Delete input/output port
delete_bd_objs [get_bd_ports exp_p_tri_io]
delete_bd_objs [get_bd_ports exp_n_tri_io]

# Create newoutput port
create_bd_port -dir O -from 7 -to 0 exp_p_tri_io
#connect_bd_net [get_bd_pins exp_p_tri_io] [get_bd_pins trigger_slice_0/Dout]

# Create output port for the SPI stuff
create_bd_port -dir O -from 7 -to 0 exp_n_tri_io

# For the shim controller we are using this pinout
#
# DIO0_N CS
# DIO1_N CLK
# DIO2_N LDAC
# DIO3_N SDI_BANK0
# DIO4_N SDI_BANK1
# DIO5_N SDI_BANK2
# DIO5_N SDI_BANK3

# connect to pins
connect_bd_net [get_bd_pins exp_n_tri_io] [get_bd_pins shim_dac_0/spiconcat_0/Dout]

