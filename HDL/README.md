# The HDL directory

This directory contains all the HDL code of the ocra project. The code is organized in projects, which can be found in subdirectories of the projects folders.

All building of the HDL is done by a Makefile, which, with the help of tcl scripts, uses Vivado without using its GUI to generate bitfiles and so on. This makes it straightforward to build multiple projects etc. from the command line without having to wrestle the Vivado GUI. This entire setup is based on the [red-pitaya-notes](https://github.com/pavel-demin/red-pitaya-notes) by Pavel Demin, and some of his architecture and cores can also be found in this repository.

To get a quick start, assuming you have Vitis/Vivado configured in your path, you should be able to build the base_pl project for the snickerdoodle_black
```
make NAME=base_pl BOARD=snickerdoodle_black
```

Similarily, you can build the ocra_mri project for the stemlab_125_14 by calling
```
make NAME=ocra_mri BOARD=stemlab_125_14
```

This is pretty easy, isn't it?