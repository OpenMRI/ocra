# ocra


## Build notes (VN)

   Currently the build process is set up for Xilinx Vivado 2019.2.
   However, Vivado 2019.2 no longer includes the Xilinx SDK, which means that some extra tools from Xilinx 2019.1 are required.
   To build the necessary files:

   - install Vivado 2019.2; only include the webpack and the Zynq FPGAs unless you're sure you need more [TODO: more info].
     After installation, assuming you installed to /opt, inside the /opt/Xilinx/Vivado/2019.2 folder you should find settings64.sh .

   - download the Xilinx 2019.1 SDK tools from http://petalinux.xilinx.com/sswreleases/rel-v2019/downloads/xsct/xsct_2019.1.tar.xz

   - extract them to your /opt/Xilinx folder (or /tools/Xilinx folder, depending on where you installed Vivado).
     After extraction, the bin folder's path should be /opt/Xilinx/Scout/2019.1/bin/ (or /tools/Xilinx/Scout/2019.1/bin/)

   For the below I'm assuming you installed in /opt

   - in a terminal, run the following commands:

   ". /opt/Xilinx/Vivado/2019.2/settings64.sh"
   "export PATH=/opt/Xilinx/Scout/2019.1/bin:$PATH"
   "make"

   After completion (15 minutes - 2 hours, depending on your PC), you should have a HDL/tmp folder, containing the files ocra_mri.bit.bin, ocra_mri.dtbo, and ocra_mri.hdf .
   The first two are for loading the Red Pitaya/StemLAB FPGA bitstream, and the third is the hardware description file used for generating the Yocto Linux image.
   For more Yocto build info, see the meta-openmri readme (https://github.com/OpenMRI/meta-openmri) .
   You can use the same SDK tools for Yocto as well.