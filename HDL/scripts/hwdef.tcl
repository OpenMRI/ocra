
set project_name [lindex $argv 0]
set board_name [lindex $argv 1]

open_project tmp/${board_name}_${project_name}.xpr

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
  launch_runs synth_1
  wait_on_run synth_1
}

write_hw_platform -fixed -force tmp/${board_name}_${project_name}.xsa

close_project
