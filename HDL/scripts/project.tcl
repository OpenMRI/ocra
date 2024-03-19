package require json

set project_name [lindex $argv 0]
set board_name [lindex $argv 1]

# read the ocra_config for the board
set ocra_config_fd [open boards/${board_name}/ocra_config.json "r"]
set ocra_config_str [read $ocra_config_fd]
close $ocra_config_fd
set ocra_config_dict [json::json2dict $ocra_config_str] 

set part_name [dict get $ocra_config_dict HDL part]
set board_part [dict get $ocra_config_dict HDL board_part]

file delete -force tmp/${board_name}_${project_name}.cache tmp/${board_name}_${project_name}.hw tmp/${board_name}_${project_name}.srcs tmp/${board_name}_${project_name}.runs tmp/${board_name}_${project_name}.xpr

create_project -part $part_name ${board_name}_${project_name} tmp

set_property board_part $board_part [current_project]
set_property platform.extensible true [current_project]

set_property IP_REPO_PATHS {tmp/cores tmp/cores_pavel} [current_project]

set bd_path tmp/${board_name}_${project_name}.srcs/sources_1/bd/system

create_bd_design system

source boards/${board_name}/ports.tcl

proc cell {cell_vlnv cell_name {cell_props {}} {cell_ports {}}} {
  set cell [create_bd_cell -type ip -vlnv $cell_vlnv $cell_name]
  set prop_list {}
  foreach {prop_name prop_value} [uplevel 1 [list subst $cell_props]] {
    lappend prop_list CONFIG.$prop_name $prop_value
  }
  if {[llength $prop_list] > 1} {
    set_property -dict $prop_list $cell
  }
  foreach {local_name remote_name} [uplevel 1 [list subst $cell_ports]] {
    set local_port [get_bd_pins $cell_name/$local_name]
    set remote_port [get_bd_pins $remote_name]
    if {[llength $local_port] == 1 && [llength $remote_port] == 1} {
      connect_bd_net $local_port $remote_port
      continue
    }
    set local_port [get_bd_intf_pins $cell_name/$local_name]
    set remote_port [get_bd_intf_pins $remote_name]
    if {[llength $local_port] == 1 && [llength $remote_port] == 1} {
      connect_bd_intf_net $local_port $remote_port
      continue
    }
    error "** ERROR: can't connect $cell_name/$local_name and $remote_name"
  }
}

proc module {module_name module_body {module_ports {}}} {
  set bd [current_bd_instance .]
  current_bd_instance [create_bd_cell -type hier $module_name]
  eval $module_body
  current_bd_instance $bd
  foreach {local_name remote_name} [uplevel 1 [list subst $module_ports]] {
    set local_port [get_bd_pins $module_name/$local_name]
    set remote_port [get_bd_pins $remote_name]
    if {[llength $local_port] == 1 && [llength $remote_port] == 1} {
      connect_bd_net $local_port $remote_port
      continue
    }
    set local_port [get_bd_intf_pins $module_name/$local_name]
    set remote_port [get_bd_intf_pins $remote_name]
    if {[llength $local_port] == 1 && [llength $remote_port] == 1} {
      connect_bd_intf_net $local_port $remote_port
      continue
    }
    error "** ERROR: can't connect $module_name/$local_name and $remote_name"
  }
}

# TW added these from the Koheron project
proc underscore {pin_name} {
    return [join [split $pin_name /] _]
}

proc get_pin_width {pin_name} {
    set left [get_property LEFT [get_bd_pins $pin_name]]
    set right [get_property RIGHT [get_bd_pins $pin_name]]
    set width [expr $left - $right + 1]
    if {$width < 1} {return 1} else {return $width}
}

proc get_slice_pin {pin_name from to {cell_name ""}} {
    if {$cell_name eq ""} {
	set cell_name slice_${from}_${to}_[underscore $pin_name]
    }
    if {[get_bd_cells $cell_name] eq ""} {
	cell xilinx.com:ip:xlslice:1.0 $cell_name {
	    DIN_WIDTH [get_pin_width $pin_name]
	    DIN_FROM $from
	    DIN_TO $to
	} {
	    Din $pin_name
	}
    }
    return $cell_name/Dout
}

set non_ip_rtl_files [glob -nocomplain projects/$project_name/*.v projects/$project_name/*.sv projects/$project_name/rtl/*.sv projects/$project_name/rtl/*.v]
if {[llength $non_ip_rtl_files] > 0} {
  add_files -norecurse $non_ip_rtl_files
}

source projects/$project_name/block_design.tcl

rename cell {}
rename module {}

if {[version -short] >= 2016.3} {
  set_property synth_checkpoint_mode None [get_files $bd_path/system.bd]
}

generate_target all [get_files $bd_path/system.bd]
make_wrapper -files [get_files $bd_path/system.bd] -top

add_files -norecurse $bd_path/hdl/system_wrapper.v

set files [glob -nocomplain projects/$project_name/*.v projects/$project_name/*.sv]
if {[llength $files] > 0} {
  add_files -norecurse $files
}

set files [glob -nocomplain boards/$board_name/*.xdc]
if {[llength $files] > 0} {
  add_files -norecurse -fileset constrs_1 $files
}

set_property VERILOG_DEFINE {TOOL_VIVADO} [current_fileset]

set_property STRATEGY Flow_PerfOptimized_high [get_runs synth_1]
# TW added this for pulsed_nmr_planB
set_property STEPS.SYNTH_DESIGN.ARGS.RETIMING true [get_runs synth_1]

set_property STRATEGY Performance_NetDelay_high [get_runs impl_1]

close_project
