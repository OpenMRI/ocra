# Create and open your project
create_project -f async_fifo async_fifo_proj -part xc7z010clg400-1
add_files ../async_fifo.sv async_fifo_tb.v
read_xdc async_fifo.xdc
set_property top async_fifo [current_fileset]

# Run synthesis
launch_runs synth_1 -jobs 4
wait_on_run synth_1

# Open synthesized design
open_run synth_1

# Generate reports
report_utilization -file utilization_report.txt
report_timing_summary -file timing_summary.txt
report_timing -sort_by group -max_paths 10 -file detailed_timing.txt

file delete -force failing_timing_paths.txt
report_timing -max_paths 100 -slack_lesser_than 0 -file failing_timing_paths.txt

# some more interesting outputs
# Report all registers with ASYNC_REG attribute
set outfile [open "async_reg_report.txt" "w"]
set all_cells [get_cells -hierarchical -filter {PRIMITIVE_TYPE =~ "FLOP_LATCH.*"}]

foreach cell $all_cells {
    if {[get_property ASYNC_REG $cell] == 1} {
        puts $outfile "$cell"
    }
}
close $outfile
puts "✅ async_reg_report.txt has been generated."
