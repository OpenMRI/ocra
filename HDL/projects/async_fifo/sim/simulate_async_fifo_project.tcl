# Create a new Vivadc prcject for async FIFO
create_project -force async_fifo_proj ./async_fifo_proj -part xc7z010clg400-1

# Set the top module for simulation
set_property top async_fifo_tb [current_fileset -simset]

# Add Verilog source files (adjust paths as needed)
add_files -norecurse ../async_fifo.sv
add_files -fileset sim_1 -norecurse ./async_fifo_tb.v

# Add constraints
add_files -fileset constrs_1 async_fifo.xdc

# Set simulation top module
set_property top async_fifo_tb [get_filesets sim_1]

# Optional: set simulation language
set_property target_language Verilog [current_project]

# Launch simulation
launch_simulation

