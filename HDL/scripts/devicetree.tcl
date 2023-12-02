set project_name [lindex $argv 0]

set proc_name [lindex $argv 1]

set repo_path [lindex $argv 2]

set version [lindex $argv 3]

set board_name [lindex $argv 4]

set boot_args {console=ttyPS0,115200 root=/dev/mmcblk0p2 ro rootfstype=ext4 earlyprintk rootwait}

set hard_path tmp/${board_name}_${project_name}.hard
set tree_path tmp/${board_name}_${project_name}.tree

file mkdir $hard_path
file copy -force tmp/${board_name}_${project_name}.xsa $hard_path/${board_name}_${project_name}.xsa

hsi::set_repo_path $repo_path

hsi::open_hw_design $hard_path/${board_name}_${project_name}.xsa
hsi::create_sw_design -proc $proc_name -os device_tree devicetree

common::set_property CONFIG.kernel_version $version [hsi::get_os]
common::set_property CONFIG.bootargs $boot_args [hsi::get_os]
common::set_property CONFIG.dt_overlay true [hsi::get_os]
common::set_property CONFIG.firmware_name ${board_name}_${project_name}.bit [hsi::get_os]

hsi::generate_bsp -dir $tree_path

hsi::close_sw_design [hsi::current_sw_design]
hsi::close_hw_design [hsi::current_hw_design]
