# The HDL directory

This directory contains all the HDL code of the ocra project. The code is organized in projects, which can be found in subdirectories of the projects folders.

In order to build the HDL code you need to have Xilinx Vitis 2022.2 full edition. We highly recommend that you use Linux, because the build system and other tooling relies on Linux. We are working on and recommend [Ubuntu 22.04 LTS](https://ubuntu.com/download/desktop).

**Basic working knowledge of Linux and bash is more or less required to follow these instructions.**

In order to install Vitis you will need about 110 GB of free disk space, and you will need to register an account with Xilinx website (remember the password, because the installer will also require the same login credentials that you created on the Xilinx website. It is best to download the [Vitis web installer](https://www.xilinx.com/member/forms/download/xef.html?filename=Xilinx_Unified_2022.2_1014_8888_Lin64.bin).

Vivado (the main tool in the Vitis package) is a bit of a beast and requires a reasonably powerful workstation.

All building of the HDL is done by a [GNU Makefile](https://www.gnu.org/software/make/), which, with the help of [TCL scripts](https://www.tcl.tk/about/language.html), uses Vivado without using its GUI to generate bitfiles and so on. Tcl is the scripting language used by Vivado, so one has to script it in tcl. Sorry this isn't python, but its easy to get a hang of. **You do not need to be able to code Makefiles or Tcl to use this repository to develop ocra HDL code.**

This makes it straightforward to build multiple projects etc. from the command line without having to wrestle the Vivado GUI. This entire setup is based on the [red-pitaya-notes](https://github.com/pavel-demin/red-pitaya-notes) by Pavel Demin, and some of his architecture and cores can also be found in this repository.

This repository makes use of Vivado board files, which requires additional configuration of your Vivado/Vitis setup. In order to make everything work the following configuration steps need to be taken:
1. Add `source /tools/Xilinx/Vitis/2022.2/settings64.sh` to your `.bash_profile`
1. Define the environment variable OCRA_DIR in your `.bash_profile` to point to the ocra directory
2. Include the following in your local Vivado config (i.e. $HOME/.Xilinx/Vivado/2022.2/Vivado_init.tcl):
```
# set up the OCRA project
set ocra_dir $::env(OCRA_DIR)
source $ocra_dir/HDL/scripts/Vivado_ocra_init.tcl
```

To get a quick start, assuming you have Vitis/Vivado configured in your path, you should be able to build the base_pl project for the snickerdoodle_black
```
cd $OCRA_DIR/HDL
make NAME=base_pl BOARD=snickerdoodle_black
```

Similarily, you can build the ocra_mri project for the stemlab_125_14 by calling
```
make NAME=ocra_mri BOARD=stemlab_125_14
```

This is pretty easy, isn't it?