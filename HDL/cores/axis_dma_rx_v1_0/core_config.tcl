set display_name {AXI Stream DMA Receiver}

set core [ipx::current_core]

set_property DISPLAY_NAME $display_name $core
set_property DESCRIPTION $display_name $core

core_parameter C_S_AXI_DATA_WIDTH {AXI DATA WIDTH} {Width of the AXI data bus.}
core_parameter C_S_AXI_ADDR_WIDTH {AXI ADDR WIDTH} {Width of the AXI address bus.}
core_parameter C_AXIS_TDATA_WIDTH {AXIS DATA WIDTH} {Width of the AXIS data bus.}

# AXI4-Lite Slave Interface to control the core
set bus [ipx::get_bus_interfaces -of_objects $core S_AXI]
set_property BUS_TYPE_VLNV xilinx.com:interface:aximm_rtl:1.0 $bus
set_property NAME S_AXI $bus
set_property INTERFACE_MODE slave $bus

# S-AXIS Interface from receiver chain 
set bus [ipx::get_bus_interfaces -of_objects $core s_axis]
set_property BUS_TYPE_VLNV xilinx.com:interface:axis_rtl:1.0 $bus
set_property NAME S_AXIS $bus
set_property INTERFACE_MODE slave $bus

# M-AXIS Interface - Data Mover Commands 
set bus [ipx::get_bus_interfaces -of_objects $core m_axis_s2mm_cmd]
set_property BUS_TYPE_VLNV xilinx.com:interface:axis_rtl:1.0 $bus
set_property NAME M_AXIS_S2MM_CMD $bus
set_property INTERFACE_MODE master $bus

# S-AXIS Interface - Data Mover Status 
set bus [ipx::get_bus_interfaces -of_objects $core s_axis_s2mm_sts]
set_property BUS_TYPE_VLNV xilinx.com:interface:axis_rtl:1.0 $bus
set_property NAME S_AXIS_S2MM_STS $bus
set_property INTERFACE_MODE slave $bus

# M-AXIS Interface - Data Mover - Data Stream 
set bus [ipx::get_bus_interfaces -of_objects $core m_axis_s2mm]
set_property BUS_TYPE_VLNV xilinx.com:interface:axis_rtl:1.0 $bus
set_property NAME M_AXIS_S2MM $bus
set_property INTERFACE_MODE master $bus

set bus [ipx::get_bus_interfaces aclk]
set parameter [ipx::get_bus_parameters -of_objects $bus ASSOCIATED_BUSIF]
set_property VALUE S_AXI:S_AXIS:M_AXIS_S2MM_CMD:S_AXIS_S2MM_STS:M_AXIS_S2MM $parameter
