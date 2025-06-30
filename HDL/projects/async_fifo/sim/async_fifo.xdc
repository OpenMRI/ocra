## Clock constraints
# Set the fastest clock speed you may use in your project
create_clock -name wr_clk -period 5.000 [get_ports wr_clk]   ;# 200 MHz
create_clock -name rd_clk -period 10.000 [get_ports rd_clk]   ;# 100 MHz

## Clock groups: prevent Vivado from timing between async domains
set_clock_groups -asynchronous -group {wr_clk} -group {rd_clk}

## Optional: false paths between clock domains
set_false_path -from [get_clocks wr_clk] -to [get_clocks rd_clk]
set_false_path -from [get_clocks rd_clk] -to [get_clocks wr_clk]

## Optional: false paths between synchronizer stages (safe if using proper double flops)
set_false_path -from [get_cells -hierarchical -filter {NAME =~ "*wr_ptr_gray_rd_clk_sync1_reg[*]"}]
set_false_path -from [get_cells -hierarchical -filter {NAME =~ "*wr_ptr_gray_rd_clk_sync2_reg[*]"}]
set_false_path -from [get_cells -hierarchical -filter {NAME =~ "*rd_ptr_gray_wr_clk_sync1_reg[*]"}]
set_false_path -from [get_cells -hierarchical -filter {NAME =~ "*rd_ptr_gray_wr_clk_sync2_reg[*]"}]

