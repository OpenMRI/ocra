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
BOARD = stemlab

CORES_PAVEL = axi_axis_reader_v1_0 axi_axis_writer_v1_0 axi_bram_reader_v1_0 \
	axi_bram_writer_v1_0 axi_cfg_register_v1_0 axis_bram_reader_v1_0 axis_bram_writer_v1_0 axis_constant_v1_0 \
        axis_fifo_v1_0 axis_lfsr_v1_0 axis_ram_writer_v1_0 axis_red_pitaya_adc_v2_0 axis_red_pitaya_dac_v1_0 \
        axis_zeroer_v1_0 axis_variable_v1_0 axis_interpolator_v1_0 \
        axi_sts_register_v1_0

CORES = micro_sequencer_v1_0 axi_dac_spi_sequencer_v1_1 axi_dac_daisy_spi_sequencer_v1_0 axis_segmented_bram_reader_v1_0 axi_serial_attenuator_v1_0 axi_four_ltc2656_spi_v1_0 axi_trigger_core_v1_0

VIVADO = vivado -nolog -nojournal -mode batch
HSI = xsct
RM = rm -rf

VIVADO_VER = $(shell vivado -version | grep "v20" | sed -r 's/.*v(20[0-9]{2}.[0-9]).*/\1/g')

UBOOT_TAG = xilinx-v2022.2
LINUX_TAG = xilinx-v2022.2
DTREE_TAG = xlnx_rel_v2022.2

UBOOT_DIR = tmp/u-boot-xlnx-$(UBOOT_TAG)
LINUX_DIR = tmp/linux-xlnx-$(LINUX_TAG)

UBOOT_TAR = tmp/u-boot-xlnx-$(UBOOT_TAG).tar.gz
LINUX_TAR = tmp/linux-xlnx-$(LINUX_TAG).tar.gz

UBOOT_URL = https://github.com/Xilinx/u-boot-xlnx/archive/$(UBOOT_TAG).tar.gz
LINUX_URL = https://github.com/Xilinx/linux-xlnx/archive/$(LINUX_TAG).tar.gz

DTREE_DIR = tmp/device-tree-xlnx-$(DTREE_TAG)
DTREE_URL = https://github.com/Xilinx/device-tree-xlnx/

LINUX_CFLAGS = "-O2 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard"
UBOOT_CFLAGS = "-O2 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard"
ARMHF_CFLAGS = "-O2 -march=armv7-a -mcpu=cortex-a9 -mtune=cortex-a9 -mfpu=neon -mfloat-abi=hard"

RTL_TAR = tmp/rtl8192cu.tgz
RTL_URL = https://www.dropbox.com/sh/5fy49wae6xwxa8a/AABNwuLz3dPHK06vEDHmG8mfa/rtl8192cu/rtl8192cu.tgz?dl=1

.PRECIOUS: tmp/cores_pavel/% tmp/cores/% tmp/%.xpr tmp/%.hdf tmp/%.bit tmp/%.fsbl/executable.elf tmp/%.tree/system.dts

all: devicetree.dtb tmp/$(BOARD)_$(NAME).bit

xpr: tmp/$(BOARD)_$(NAME).xpr

bit: tmp/$(BOARD)_$(NAME).bit

$(UBOOT_TAR):
	mkdir -p $(@D)
	curl -L $(UBOOT_URL) -o $@

$(LINUX_TAR):
	mkdir -p $(@D)
	curl -L $(LINUX_URL) -o $@

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

$(DTREE_DIR): 
	mkdir -p $@
	git clone $(DTREE_URL) $@
	git --git-dir $@/.git --work-tree $@ checkout $(DTREE_TAG)
	
devicetree.dtb: tmp/$(BOARD)_$(NAME).tree/system.dts
	#this is additional preprocessor call is needed because HSI produces dts files with C style "#include" syntax
	cpp -nostdinc -I include -I arch  -undef -x assembler-with-cpp tmp/$(BOARD)_$(NAME).tree/system-top.dts tmp/$(BOARD)_$(NAME).tree/system-top.dts.preprocessed
	dtc -I dts -O dtb -o devicetree.dtb \
	  -i tmp/$(BOARD)_$(NAME).tree -@ tmp/$(BOARD)_$(NAME).tree/system-top.dts.preprocessed

ocra_mri.dtbo: tmp/$(BOARD)_$(NAME).tree/system.dts
	dtc -O dtb -o tmp/ocra_mri.dtbo -b 0 -@ tmp/$(BOARD)_$(NAME).tree/pl.dtsi

shim_controller.dtbo: tmp/$(BOARD)_$(NAME).tree/system.dts
	dtc -O dtb -o tmp/shim_controller.dtbo -b 0 -@ tmp/$(BOARD)_$(NAME).tree/pl.dtsi

tmp/cores_pavel/%: cores_pavel/%/core_config.tcl cores_pavel/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core_pavel.tcl -tclargs $* $(PART)

tmp/cores/%: cores/%/core_config.tcl cores/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core.tcl -tclargs $* $(PART)

tmp/%.xpr: projects/% $(addprefix tmp/cores_pavel/, $(CORES_PAVEL)) $(addprefix tmp/cores/, $(CORES)) 
	mkdir -p $(@D)
	$(VIVADO) -source scripts/project.tcl -tclargs $(NAME) $(BOARD) $(PART)

tmp/%.hdf: tmp/%.xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/hwdef.tcl -tclargs $(NAME) $(BOARD)

tmp/$(BOARD)_$(NAME).bit: tmp/$(BOARD)_$(NAME).xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/bitstream.tcl -tclargs $(NAME) $(BOARD)

tmp/%.bin: tmp/$(BOARD)_$(NAME).xpr
	echo "all:{ $^}" > tmp/$(BOARD)_$(NAME).bif
	bootgen -image tmp/$(BOARD)_$(NAME).bif -arch zynq -process_bitstream bin -w -o $@

tmp/%.tree/system.dts: tmp/$(BOARD)_$(NAME).hdf $(DTREE_DIR)
	$(HSI) scripts/devicetree.tcl $(NAME) $(PROC) $(DTREE_DIR) $(VIVADO_VER) $(BOARD)
	#patch $@ patches/devicetree.patch

clean:
	$(RM) uImage fw_printenv boot.bin devicetree.dtb tmp
	$(RM) .Xil usage_statistics_webtalk.html usage_statistics_webtalk.xml
	$(RM) vivado*.jou vivado*.log
	$(RM) webtalk*.jou webtalk*.log
