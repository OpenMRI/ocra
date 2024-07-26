set display_name {AXI4-Stream Red Pitaya DDR ADC}

set core [ipx::current_core]

set_property DISPLAY_NAME $display_name $core
set_property DESCRIPTION $display_name $core

core_parameter DDR_DATA_WIDTH {DDR DATA WIDTH} {Width of the DDR ADC data bus.}

set bus [ipx::get_bus_interfaces aclk]
set parameter [ipx::add_bus_parameter ASSOCIATED_BUSIF $bus]
