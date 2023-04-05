global board_name
global project_name

# set ps_preset boards/${board_name}/ps_${project_name}.xml

# Create processing_system7
cell xilinx.com:ip:processing_system7:5.5 ps_0 {
  PCW_USE_S_AXI_HP0 1
} {
    M_AXI_GP0_ACLK ps_0/FCLK_CLK0
    S_AXI_HP0_ACLK ps_0/FCLK_CLK0
}

# Create all required interconnections
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 -config {
    make_external {FIXED_IO, DDR}
    apply_board_preset 1
    Master Disable
    Slave Disable
} [get_bd_cells ps_0]

# I don't think we need that for this project
set_property CONFIG.PCW_USE_S_AXI_ACP {0} [get_bd_cells ps_0]

# We always have this though
set_property CONFIG.PCW_USE_S_AXI_HP0 {1} [get_bd_cells ps_0]

