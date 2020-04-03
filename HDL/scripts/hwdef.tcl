
set project_name [lindex $argv 0]

open_project tmp/$project_name.xpr

# VN: these aren't needed
# set_property platform.board_id StemLAB122 [current_project]
# set_property platform.name StemLAB122 [current_project]
# generate_target all [get_files tmp/ocra_mri.srcs/sources_1/bd/system/system.bd]

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
  launch_runs synth_1
  wait_on_run synth_1
}

write_hw_platform -fixed -force -file tmp/$project_name.xsa

close_project
