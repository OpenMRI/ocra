set display_name {AXI Sniffer}

set core [ipx::current_core]

set_property DISPLAY_NAME $display_name $core
set_property DESCRIPTION $display_name $core

core_parameter C_S_AXI_DATA_WIDTH {AXI DATA WIDTH} {Width of the AXI data bus.}
core_parameter C_S_AXI_ADDR_WIDTH {AXI ADDR WIDTH} {Width of the AXI address bus.}

# AXI4-Lite Slave Interface to control the core
set bus [ipx::get_bus_interfaces -of_objects $core s_axi]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:aximm_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:aximm:1.0 $bus
set_property NAME S_AXI $bus
set_property INTERFACE_MODE monitor $bus

set bus [ipx::get_bus_interfaces aclk]
set parameter [ipx::get_bus_parameters -of_objects $bus ASSOCIATED_BUSIF]
set_property VALUE S_AXI $parameter
ipx::associate_bus_interfaces -busif S_AXI -clock aclk [ipx::current_core]
ipx::merge_project_changes ports [ipx::current_core]