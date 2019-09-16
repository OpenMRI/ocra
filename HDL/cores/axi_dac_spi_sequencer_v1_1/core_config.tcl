set display_name {AXI-4 Lite 4CH DAC SPI Sequencer}

set core [ipx::current_core]

set_property DISPLAY_NAME $display_name $core
set_property DESCRIPTION $display_name $core

core_parameter C_S_AXI_DATA_WIDTH {AXI DATA WIDTH} {Width of the AXI data bus.}
core_parameter C_S_AXI_ADDR_WIDTH {AXI ADDR WIDTH} {Width of the AXI address bus.}
core_parameter BRAM_DATA_WIDTH {BRAM DATA WIDTH} {Width of the BRAM data port.}
core_parameter BRAM_ADDR_WIDTH {BRAM ADDR WIDTH} {Width of the BRAM address port.}

set bus [ipx::get_bus_interfaces -of_objects $core S_AXI]
set_property NAME S_AXI $bus
set_property INTERFACE_MODE slave $bus

set bus [ipx::get_bus_interfaces S_AXI_ACLK]
set parameter [ipx::get_bus_parameters -of_objects $bus ASSOCIATED_BUSIF]
set_property VALUE S_AXI $parameter

set bus [ipx::add_bus_interface BRAM_PORTX $core]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:bram_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:bram:1.0 $bus
set_property INTERFACE_MODE master $bus
foreach {logical physical} {
  RST  bram_portx_rst
  CLK  bram_portx_clk
  ADDR bram_portx_addr
  DOUT bram_portx_rddata
} {
  set_property PHYSICAL_NAME $physical [ipx::add_port_map $logical $bus]
}

set bus [ipx::add_bus_interface BRAM_PORTY $core]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:bram_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:bram:1.0 $bus
set_property INTERFACE_MODE master $bus
foreach {logical physical} {
  RST  bram_porty_rst
  CLK  bram_porty_clk
  ADDR bram_porty_addr
  DOUT bram_porty_rddata
} {
  set_property PHYSICAL_NAME $physical [ipx::add_port_map $logical $bus]
}

set bus [ipx::add_bus_interface BRAM_PORTZ $core]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:bram_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:bram:1.0 $bus
set_property INTERFACE_MODE master $bus
foreach {logical physical} {
  RST  bram_portz_rst
  CLK  bram_portz_clk
  ADDR bram_portz_addr
  DOUT bram_portz_rddata
} {
  set_property PHYSICAL_NAME $physical [ipx::add_port_map $logical $bus]
}

set bus [ipx::add_bus_interface BRAM_PORTZ2 $core]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:bram_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:bram:1.0 $bus
set_property INTERFACE_MODE master $bus
foreach {logical physical} {
  RST  bram_portz2_rst
  CLK  bram_portz2_clk
  ADDR bram_portz2_addr
  DOUT bram_portz2_rddata
} {
  set_property PHYSICAL_NAME $physical [ipx::add_port_map $logical $bus]
}

set bus [ipx::get_bus_interfaces bram_portx_clk]
set parameter [ipx::add_bus_parameter ASSOCIATED_BUSIF $bus]
set_property VALUE BRAM_PORTX $parameter

set bus [ipx::get_bus_interfaces bram_porty_clk]
set parameter [ipx::add_bus_parameter ASSOCIATED_BUSIF $bus]
set_property VALUE BRAM_PORTY $parameter

set bus [ipx::get_bus_interfaces bram_portz_clk]
set parameter [ipx::add_bus_parameter ASSOCIATED_BUSIF $bus]
set_property VALUE BRAM_PORTZ $parameter

set bus [ipx::get_bus_interfaces bram_portz2_clk]
set parameter [ipx::add_bus_parameter ASSOCIATED_BUSIF $bus]
set_property VALUE BRAM_PORTZ2 $parameter

