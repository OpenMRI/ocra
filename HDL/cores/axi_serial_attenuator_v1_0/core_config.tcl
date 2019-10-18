set display_name {AXI-4 Lite 7-bit RF attenuator}

set core [ipx::current_core]

set_property DISPLAY_NAME $display_name $core
set_property DESCRIPTION $display_name $core

core_parameter C_S_AXI_DATA_WIDTH {AXI DATA WIDTH} {Width of the AXI data bus.}
core_parameter C_S_AXI_ADDR_WIDTH {AXI ADDR WIDTH} {Width of the AXI address bus.}

set bus [ipx::get_bus_interfaces -of_objects $core S_AXI]
set_property NAME S_AXI $bus
set_property INTERFACE_MODE slave $bus

set bus [ipx::get_bus_interfaces S_AXI_ACLK]
set parameter [ipx::get_bus_parameters -of_objects $bus ASSOCIATED_BUSIF]
set_property VALUE S_AXI $parameter

