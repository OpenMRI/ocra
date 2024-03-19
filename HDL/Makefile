# 'make' builds everything
# 'make clean' deletes everything except source files and Makefile
#
# You need to set NAME, PART and PROC for your project.
# NAME is the base name for most of the generated files.

NAME ?= ocra_mri
BOARD ?= stemlab_125_14
export PART=$(shell jq -r '.HDL.part' boards/$(BOARD)/ocra_config.json)
export PROC=$(shell jq -r '.HDL.proc' boards/$(BOARD)/ocra_config.json)

CORES_PAVEL = axi_axis_reader_v1_0 axi_axis_writer_v1_0 axi_bram_reader_v1_0 \
	axi_bram_writer_v1_0 axi_cfg_register_v1_0 axis_bram_reader_v1_0 axis_bram_writer_v1_0 axis_constant_v1_0 \
        axis_fifo_v1_0 axis_lfsr_v1_0 axis_ram_writer_v1_0 axis_red_pitaya_adc_v2_0 axis_red_pitaya_dac_v1_0 \
        axis_zeroer_v1_0 axis_variable_v1_0 axis_interpolator_v1_0 \
        axi_sts_register_v1_0

CORES = micro_sequencer_v1_0 axi_dac_spi_sequencer_v1_1 axi_dac_daisy_spi_sequencer_v1_0 axis_segmented_bram_reader_v1_0 axi_serial_attenuator_v1_0 axi_four_ltc2656_spi_v1_0 axi_trigger_core_v1_0 axis_red_pitaya_adc_v3_0 \
axi_config_registers_v1_0 axis_dma_rx_v1_0 axi_sniffer_v1_0 axis_red_pitaya_adc_ddr_v1_0 red_pitaya_adc_spi_v1_0 axis_acq_trigger_v1_0

VIVADO = vivado -nolog -nojournal -mode batch
HSI = xsct
RM = rm -rf

VIVADO_VER = $(shell vivado -version | grep "v20" | sed -r 's/.*v(20[0-9]{2}.[0-9]).*/\1/g')

DTREE_TAG = xlnx_rel_v2022.2

DTREE_DIR = tmp/device-tree-xlnx-$(DTREE_TAG)
DTREE_URL = https://github.com/Xilinx/device-tree-xlnx/


.PRECIOUS: tmp/cores_pavel/% tmp/cores/% tmp/%.xpr tmp/%.xsa tmp/%.bit tmp/%.tree/system.dts

.PHONY: clean all xpr bit dtbo setup

.ONESHELL:
all: setup tmp/%.bin tmp/%.dtbo


.ONESHELL:
xpr: setup tmp/%.xpr

.ONESHELL:
bit: setup tmp/%.bit

.ONESHELL:
dtbo: setup tmp/%.dtbo

setup:
    ifeq ("$(wildcard boards/$(BOARD)/ocra_config.json)","")
        # The file doesn't exist
		@echo "There seems to be no configuration for the board: $(BOARD)"
		@echo "Please check the board string, and try again. Good luck!!"
		exit 1
    endif

	@if ! jq -r '.HDL.projects' boards/$(BOARD)/ocra_config.json | grep -qw "$(NAME)"; then \
        echo "The board: $(BOARD) does not appear to be supported by project $(NAME). Sorry!"; \
        exit 1; \
    fi

	@echo "Great!! Building project: ${NAME} for board: ${BOARD} !"
	@echo "part: $(PART)"

$(DTREE_DIR): 
	mkdir -p $@
	git clone $(DTREE_URL) $@
	git --git-dir $@/.git --work-tree $@ checkout $(DTREE_TAG)

tmp/%.dtbo: tmp/$(BOARD)_$(NAME).tree/system.dts
	dtc -O dtb -o tmp/$(BOARD)_$(NAME).dtbo -b 0 -@ devicetree/$(BOARD)_$(NAME).dtsi

tmp/cores_pavel/%: cores_pavel/%/core_config.tcl cores_pavel/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core_pavel.tcl -tclargs $* $(PART)

tmp/cores/%: cores/%/core_config.tcl cores/%/*.v
	mkdir -p $(@D)
	$(VIVADO) -source scripts/core.tcl -tclargs $* $(PART)

tmp/%.xpr: $(addprefix tmp/cores_pavel/, $(CORES_PAVEL)) $(addprefix tmp/cores/, $(CORES)) 
	mkdir -p $(@D)
	$(VIVADO) -source scripts/project.tcl -tclargs $(NAME) $(BOARD) $(PART)

tmp/%.xsa: tmp/$(BOARD)_$(NAME).xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/hwdef.tcl -tclargs $(NAME) $(BOARD)

tmp/%.bit: tmp/$(BOARD)_$(NAME).xpr
	mkdir -p $(@D)
	$(VIVADO) -source scripts/bitstream.tcl -tclargs $(NAME) $(BOARD)

tmp/%.bin: tmp/$(BOARD)_$(NAME).bit
	echo "all:{ $^}" > tmp/$(BOARD)_$(NAME).bif
	bootgen -image tmp/$(BOARD)_$(NAME).bif -arch zynq -process_bitstream bin -w -o $@
	rm tmp/$(BOARD)_$(NAME).bif

tmp/%.tree/system.dts: tmp/$(BOARD)_$(NAME).xsa $(DTREE_DIR)
	$(HSI) scripts/devicetree.tcl $(NAME) $(PROC) $(DTREE_DIR) $(VIVADO_VER) $(BOARD)

clean:
	$(RM) tmp
	$(RM) .Xil usage_statistics_webtalk.html usage_statistics_webtalk.xml
	$(RM) vivado*.jou vivado*.log
	$(RM) webtalk*.jou webtalk*.log
