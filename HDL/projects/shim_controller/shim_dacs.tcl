# Create a pin for the 2MHz clock
# create_bd_pin -dir I clk_2MHz

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 slice_0 {
  DIN_WIDTH 8 DIN_FROM 2 DIN_TO 2 DOUT_WIDTH 1
}

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 slice_1 {
  DIN_WIDTH 32 DIN_FROM 15 DIN_TO 0 DOUT_WIDTH 16
}

# Create dac_spi_sequencer
cell open-mri:user:axi_four_ltc2656_spi:1.0 spi_sequencer_0 {
  BRAM_DATA_WIDTH 32
  BRAM_ADDR_WIDTH 11
  CONTINUOUS FALSE
  C_S_AXI_DATA_WIDTH 32
  C_S_AXI_ADDR_WIDTH 32
} {
  aclk /ps_0/FCLK_CLK0
  aresetn slice_0/Dout
}

# 09/2019: Make sure this has SEVEN ports
cell xilinx.com:ip:xlconcat:2.1 spiconcat_0 {
    NUM_PORTS 7
}

# Make a constant setting the gradient DAC to 100 samples
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 xlconstant_0
set_property -dict [list CONFIG.CONST_WIDTH {14} CONFIG.CONST_VAL {100}] [get_bd_cells xlconstant_0]
connect_bd_net [get_bd_pins xlconstant_0/dout] [get_bd_pins spi_sequencer_0/cfg_data]

# Make a constant setting the gradient DAC offset to 0
#create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 xlconstant_1
#set_property -dict [list CONFIG.CONST_WIDTH {14} CONFIG.CONST_VAL {0}] [get_bd_cells xlconstant_1]
#connect_bd_net [get_bd_pins xlconstant_1/dout] [get_bd_pins spi_sequencer_0/current_offset]

# Hookup the SPI stuff
# For the shim controller we are using this pinout
#
# DIO0_N CS
# DIO1_N CLK
# DIO2_N LDAC
# DIO3_N SDI_BANK0
# DIO4_N SDI_BANK1
# DIO5_N SDI_BANK2
# DIO5_N SDI_BANK3
connect_bd_net [get_bd_pins spiconcat_0/In0] [get_bd_pins spi_sequencer_0/spi_cs]
connect_bd_net [get_bd_pins spiconcat_0/In1] [get_bd_pins spi_sequencer_0/spi_clk]
connect_bd_net [get_bd_pins spiconcat_0/In2] [get_bd_pins spi_sequencer_0/spi_ldacn]
connect_bd_net [get_bd_pins spiconcat_0/In3] [get_bd_pins spi_sequencer_0/spi_bank0]
connect_bd_net [get_bd_pins spiconcat_0/In4] [get_bd_pins spi_sequencer_0/spi_bank1]
connect_bd_net [get_bd_pins spiconcat_0/In5] [get_bd_pins spi_sequencer_0/spi_bank2]
connect_bd_net [get_bd_pins spiconcat_0/In6] [get_bd_pins spi_sequencer_0/spi_bank3]
# Since the sequencer has no z2 yet, lets connect with a constant 0
