# 'make' builds everything
# 'make clean' deletes everything except source files and Makefile
#
# You need to set NAME, PART and PROC for your project.
# NAME is the base name for most of the generated files.

# solves problem with awk while building linux kernel
# solution taken from http://www.googoolia.com/wp/2015/04/21/awk-symbol-lookup-error-awk-undefined-symbol-mpfr_z_sub/
LD_LIBRARY_PATH =

NAME = ocra_mri
PART = xc7z010clg400-1
PROC = ps7_cortexa9_0

CORES_PAVEL = axi_axis_reader_v1_0 axi_axis_writer_v1_0 axi_bram_reader_v1_0 \
	axi_bram_writer_v1_0 axi_cfg_register_v1_0 axis_bram_reader_v1_0 axis_bram_writer_v1_0 axis_constant_v1_0 \
        axis_fifo_v1_0 axis_lfsr_v1_0 axis_ram_writer_v1_0 axis_red_pitaya_adc_v2_0 axis_red_pitaya_dac_v1_0 \
        axis_zeroer_v1_0 axis_variable_v1_0 axis_interpolator_v1_0 \
        axi_sts_register_v1_0

CORES = micro_sequencer_v1_0 axi_dac_spi_sequencer_v1_1 axi_dac_daisy_spi_sequencer_v1_0 axis_segmented_bram_reader_v1_0 axi_serial_attenuator_v1_0

VIVADO = vivado -nolog -nojournal -mode batch
HSI = hsi -nolog -nojournal -mode batch
RM = rm -rf

UBOOT_TAG = xilinx-v2019.1
LINUX_TAG = xilinx-v2019.1
DTREE_TAG = xilinx-v2019.1

UBOOT_DIR = tmp/u-boot-xlnx-$(UBOOT_TAG)
LINUX_DIR = tmp/linux-xlnx-$(LINUX_TAG)
DTREE_DIR = tmp/device-tree-xlnx-$(DTREE_TAG)

UBOOT_TAR = tmp/u-boot-xlnx-$(UBOOT_TAG).tar.gz
LINUX_TAR = tmp/linux-xlnx-$(LINUX_TAG).tar.gz
DTREE_TAR = tmp/device-tree-xlnx-$(DTREE_TAG).tar.gz

UBOOT_URL = https://github.com/Xilinx/u-boot-xlnx/archive/$(UBOOT_TAG).tar.gz
LINUX_URL = https://github.com/Xilinx/linux-xlnx/archive/$(LINUX_TAG).tar.gz
DTREE_URL = https://github.com/Xilinx/device-tree-xlnx/archive/$(DTREE_TAG).tar.gz

LINUX_CFLAGS = "-O2 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard"
UBOOT_CFLAGS = "-O2 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard"
ARMHF_CFLAGS = "-O2 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard"

RTL_TAR = tmp/rtl8192cu.tgz
RTL_URL = https://www.dropbox.com/sh/5fy49wae6xwxa8a/AABNwuLz3dPHK06vEDHmG8mfa/rtl8192cu/rtl8192cu.tgz?dl=1

.PRECIOUS: tmp/cores_pavel/% tmp/cores/% tmp/%.xpr tmp/%.hdf tmp/%.bit tmp/%.fsbl/executable.elf tmp/%.tree/system.dts

all: boot.bin devicetree.dtb tmp/%.bin 

xpr: tmp/$(NAME).xpr

bit: tmp/$(NAME).bit

$(UBOOT_TAR):
	mkdir -p $(@D)
	curl -L $(UBOOT_URL) -o $@

$(LINUX_TAR):
	mkdir -p $(@D)
	curl -L $(LINUX_URL) -o $@

$(DTREE_TAR):
	mkdir -p $(@D)
	curl -L $(DTREE_URL) -o $@

$(RTL_TAR):
	mkdir -p $(@D)
	curl -L $(RTL_URL) -o $@

$(UBOOT_DIR): $(UBOOT_TAR)
	mkdir -p $@
	tar -zxf $< --strip-components=1 --directory=$@
	patch -d tmp -p 0 < patches/u-boot-xlnx-$(UBOOT_TAG).patch
	cp patches/zynq_red_pitaya_defconfig $@/configs
	cp patches/zynq-red-pitaya.dts $@/arch/arm/dts
	cp patches/zynq_red_pitaya.h $@/include/configs
	cp patches/u-boot-lantiq.c $@/drivers/net/phy/lantiq.c

$(LINUX_DIR): $(LINUX_TAR) $(RTL_TAR)
	mkdir -p $@
	tar -zxf $< --strip-components=1 --directory=$@
	tar -zxf $(RTL_TAR) --directory=$@/drivers/net/wireless/realtek
	patch -d tmp -p 0 < patches/linux-xlnx-$(LINUX_TAG).patch
	cp patches/linux-lantiq.c $@/drivers/net/phy/lantiq.c

$(DTREE_DIR): $(DTREE_TAR)
	mkdir -p $@
	tar -zxf $< --strip-components=1 --directory=$@

uImage: $(LINUX_DIR)
	make -C $< mrproper
	make -C $< ARCH=arm xilinx_zynq_defconfig
	make -C $< ARCH=arm CFLAGS=$(LINUX_CFLAGS) \
	  -j $(shell nproc 2> /dev/null || echo 1) \
	  CROSS_COMPILE=arm-linux-gnueabihf- UIMAGE_LOADADDR=0x8000 uImage
	cp $</arch/arm/boot/uImage $@

tmp/u-boot.elf: $(UBOOT_DIR)
	mkdir -p $(@D)
	make -C $< mrproper
	make -C $< ARCH=arm zynq_red_pitaya_defconfig
	make -C $< ARCH=arm CFLAGS=$(UBOOT_CFLAGS) \
	  CROSS_COMPILE=arm-linux-gnueabihf- all
	cp $</u-boot $@

fw_printenv: $(UBOOT_DIR) tmp/u-boot.elf
	make -C $< ARCH=arm CFLAGS=$(ARMHF_CFLAGS) \
	  CROSS_COMPILE=arm-linux-gnueabihf- env
	cp $</tools/env/fw_printenv $@

boot.bin: tmp/$(NAME).fsbl/executable.elf tmp/$(NAME).bit
	echo "img:{[bootloader] $^}" > tmp/boot.bif
	bootgen -image tmp/boot.bif -w -o i $@

devicetree.dtb: tmp/$(NAME).tree/system.dts
	#this is additional preprocessor call is needed because HSI produces dts files with C style "#include" syntax
	cpp -nostdinc -I include -I arch  -undef -x assembler-with-cpp tmp/$(NAME).tree/system-top.dts tmp/$(NAME).tree/system-top.dts.preprocessed
	dtc -I dts -O dtb -o devicetree.dtb \
	  -i tmp/$(NAME).tree -@ tmp/$(NAME).tree/system-top.dts.preprocessed

ocra_mri.dtbo: tmp/$(NAME).tree/system.dts
	dtc -O dtb -o tmp/ocra_mri.dtbo -b 0 -@ tmp/$(NAME).tree/pl.dtsi

tmp/cores_pavel/%: cores_pavel/%/core_config.tcl cores_pavel/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core_pavel.tcl -tclargs $* $(PART)

tmp/cores/%: cores/%/core_config.tcl cores/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core.tcl -tclargs $* $(PART)

tmp/%.xpr: projects/% $(addprefix tmp/cores_pavel/, $(CORES_PAVEL)) $(addprefix tmp/cores/, $(CORES)) 
	mkdir -p $(@D)
	$(VIVADO) -source scripts/project.tcl -tclargs $* $(PART)

tmp/%.hdf: tmp/%.xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/hwdef.tcl -tclargs $*

tmp/%.bit: tmp/%.xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/bitstream.tcl -tclargs $*

tmp/%.bin: tmp/%.bit
	echo "all:{ $^}" > tmp/ocra_mri.bif
	bootgen -image tmp/ocra_mri.bif -arch zynq -process_bitstream bin -w -o $@

tmp/%.fsbl/executable.elf: tmp/%.hdf
	mkdir -p $(@D)
	$(HSI) -source scripts/fsbl.tcl -tclargs $* $(PROC)

tmp/%.tree/system.dts: tmp/%.hdf $(DTREE_DIR)
	mkdir -p $(@D)
	$(HSI) -source scripts/devicetree.tcl -tclargs $* $(PROC) $(DTREE_DIR)
	#patch $@ patches/devicetree.patch

clean:
	$(RM) uImage fw_printenv boot.bin devicetree.dtb tmp
	$(RM) .Xil usage_statistics_webtalk.html usage_statistics_webtalk.xml
	$(RM) vivado*.jou vivado*.log
	$(RM) webtalk*.jou webtalk*.log
