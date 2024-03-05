global board_name
global project_name

set ps_preset boards/${board_name}/ps_${project_name}.xml
set pl_param_fd [open boards/${board_name}/pl_${project_name}.json "r"]
set pl_param_str [read $pl_param_fd]
close $pl_param_fd
set pl_param_dict [json::json2dict $pl_param_str]

if { [dict get $pl_param_dict mode] == "ADVANCED"} {
  source projects/scope/advanced.tcl
} else {
  source projects/scope/simple.tcl
}