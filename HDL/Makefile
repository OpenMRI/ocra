# 'make' builds everything
# 'make clean' deletes everything except source files and Makefile
#
# You need to set NAME, PART and PROC for your project.
# NAME is the base name for most of the generated files.
LD_LIBRARY_PATH =

NAME = ocra_mri
PART_VARIANT ?= Z20
ifeq ($(PART_VARIANT),Z20)
PART = xc7z020clg400-1
HWNAME = stemlab_sdr

CORES_PAVEL = axi_axis_reader_v1_0 axi_axis_writer_v1_0 axi_bram_reader_v1_0 \
	axi_bram_writer_v1_0 axi_cfg_register_v1_0 axis_bram_reader_v1_0 axis_bram_writer_v1_0 axis_constant_v1_0 \
        axis_fifo_v1_0 axis_lfsr_v1_0 axis_ram_writer_v1_0 axis_$(HWNAME)_adc_v1_0 axis_$(HWNAME)_dac_v1_0 \
        axis_zeroer_v1_0 axis_variable_v1_0 axis_interpolator_v1_0 \
        axi_sts_register_v1_0
else
PART = xc7z010clg400-1
HWNAME = red_pitaya

CORES_PAVEL = axi_axis_reader_v1_0 axi_axis_writer_v1_0 axi_bram_reader_v1_0 \
	axi_bram_writer_v1_0 axi_cfg_register_v1_0 axis_bram_reader_v1_0 axis_bram_writer_v1_0 axis_constant_v1_0 \
        axis_fifo_v1_0 axis_lfsr_v1_0 axis_ram_writer_v1_0 axis_$(HWNAME)_adc_v2_0 axis_$(HWNAME)_dac_v1_0 \
        axis_zeroer_v1_0 axis_variable_v1_0 axis_interpolator_v1_0 \
        axi_sts_register_v1_0
endif
PROC = ps7_cortexa9_0

CORES = micro_sequencer_v1_0 axi_dac_spi_sequencer_v1_1 axi_dac_daisy_spi_sequencer_v1_0 axis_segmented_bram_reader_v1_0 axi_serial_attenuator_v1_0 axi_four_ltc2656_spi_v1_0

VIVADO = vivado -nolog -nojournal -mode batch
HSI = hsi -nolog -nojournal -mode batch
RM = rm -rf

DTREE_TAG = xilinx-v2019.1
DTREE_DIR = utils/device-tree-xlnx-$(DTREE_TAG)
DTREE_TAR = utils/device-tree-xlnx-$(DTREE_TAG).tar.gz
DTREE_URL = https://github.com/Xilinx/device-tree-xlnx/archive/$(DTREE_TAG).tar.gz

RTL_TAR = tmp/rtl8192cu.tgz
RTL_URL = https://www.dropbox.com/sh/5fy49wae6xwxa8a/AABNwuLz3dPHK06vEDHmG8mfa/rtl8192cu/rtl8192cu.tgz?dl=1

.PRECIOUS: tmp/cores_pavel/% tmp/cores/% tmp/%.xpr tmp/%.hdf tmp/%.bit tmp/%.bit.bin tmp/%.tree/system.dts

all: tmp/$(NAME).bit.bin tmp/$(NAME).dtbo

xpr: tmp/$(NAME).xpr

bit: tmp/$(NAME).bit

hdf: tmp/$(NAME).hdf

$(DTREE_TAR):
	mkdir -p $(@D)
	curl -L $(DTREE_URL) -o $@

$(RTL_TAR):
	mkdir -p $(@D)
	curl -L $(RTL_URL) -o $@

$(DTREE_DIR): $(DTREE_TAR)
	mkdir -p $@
	tar -zxf $< --strip-components=1 --directory=$@

tmp/$(NAME).dtbo: tmp/$(NAME).tree/system.dts
	dtc -O dtb -o tmp/$(NAME).dtbo -b 0 -@ tmp/$(NAME).tree/pl.dtsi

# shim_controller.dtbo: tmp/$(NAME).tree/system.dts
# 	dtc -O dtb -o tmp/shim_controller.dtbo -b 0 -@ tmp/$(NAME).tree/pl.dtsi

tmp/cores_pavel/%: cores_pavel/%/core_config.tcl cores_pavel/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core_pavel.tcl -tclargs $* $(PART)

tmp/cores/%: cores/%/core_config.tcl cores/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core.tcl -tclargs $* $(PART)

tmp/%.xpr: projects/% $(addprefix tmp/cores_pavel/, $(CORES_PAVEL)) $(addprefix tmp/cores/, $(CORES)) 
	mkdir -p $(@D)
	$(VIVADO) -source scripts/project_$(PART_VARIANT).tcl -tclargs $* $(PART)

tmp/%.hdf: tmp/%.xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/hwdef.tcl -tclargs $*
	cp tmp/ocra_mri.xsa tmp/ocra_mri.hdf

tmp/%.bit: tmp/%.xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/bitstream.tcl -tclargs $*

tmp/%.bit.bin: tmp/%.bit
	echo "all:{ $^}" > tmp/ocra_mri.bif
	bootgen -image tmp/ocra_mri.bif -arch zynq -process_bitstream bin -w -o $@

tmp/%.tree/system.dts: tmp/%.hdf $(DTREE_DIR)
	mkdir -p $(@D)
	$(HSI) -source scripts/devicetree.tcl -tclargs $* $(PROC) $(DTREE_DIR)
#	patch $@ patches/devicetree.patch

clean:
	$(RM) fw_printenv tmp
	$(RM) .Xil usage_statistics_webtalk.html usage_statistics_webtalk.xml
	$(RM) apk-tools-static-* alpine-uboot-* linux-firmware-* stemlab-sdr-alpine-*
	$(RM) vivado*.jou vivado*.log
	$(RM) webtalk*.jou webtalk*.log
