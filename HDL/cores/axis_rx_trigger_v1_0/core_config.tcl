set display_name {AXI Stream Receiver Trigger}

set core [ipx::current_core]

set_property DISPLAY_NAME $display_name $core
set_property DESCRIPTION $display_name $core

core_parameter C_S_AXI_DATA_WIDTH {AXI DATA WIDTH} {Width of the AXI data bus.}
core_parameter C_S_AXI_ADDR_WIDTH {AXI ADDR WIDTH} {Width of the AXI address bus.}
core_parameter C_AXIS_TDATA_WIDTH {AXIS DATA WIDTH} {Width of the AXIS data bus.}

# AXI4-Lite Slave Interface to control the core
set bus [ipx::get_bus_interfaces -of_objects $core S_AXI]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:aximm_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:aximm:1.0 $bus
set_property NAME S_AXI $bus
set_property INTERFACE_MODE slave $bus

# S-AXIS Interface
set bus [ipx::get_bus_interfaces -of_objects $core s_axis]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:axis_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:axis:1.0 $bus
set_property NAME S_AXIS $bus
set_property INTERFACE_MODE slave $bus

# M-AXIS Interface
set bus [ipx::get_bus_interfaces -of_objects $core m_axis]
set_property ABSTRACTION_TYPE_VLNV xilinx.com:interface:axis_rtl:1.0 $bus
set_property BUS_TYPE_VLNV xilinx.com:interface:axis:1.0 $bus
set_property NAME M_AXIS $bus
set_property INTERFACE_MODE master $bus

set bus [ipx::get_bus_interfaces aclk]
set parameter [ipx::get_bus_parameters -of_objects $bus ASSOCIATED_BUSIF]
set_property VALUE S_AXI:S_AXIS:M_AXIS_S2MM_CMD:S_AXIS_S2MM_STS:M_AXIS_S2MM $parameter
ipx::associate_bus_interfaces -busif M_AXIS_S2MM -clock aclk [ipx::current_core]
ipx::associate_bus_interfaces -busif M_AXIS_S2MM_CMD -clock aclk [ipx::current_core]
ipx::associate_bus_interfaces -busif S_AXIS -clock aclk [ipx::current_core]
ipx::associate_bus_interfaces -busif S_AXIS_S2MM_STS -clock aclk [ipx::current_core]
ipx::associate_bus_interfaces -busif S_AXI -clock aclk [ipx::current_core]
ipx::merge_project_changes ports [ipx::current_core]
