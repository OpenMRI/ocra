VERILATOR = verilator
TOP_MODULE = half_duplex_spi_master
VERILATED = obj_dir/V$(TOP_MODULE)

SRC_FILES = half_duplex_spi_master.sv ../async_fifo/async_fifo.sv ../reset_synchronizer/reset_synchronizer.sv ../quadrature_clock_divider/quadrature_clock_divider.sv
CPP_FILES = half_duplex_spi_master_tb.cpp

all: sim

sim: $(VERILATED)
	./$(VERILATED)

$(VERILATED): $(SRC_FILES) $(CPP_FILES)
	$(VERILATOR) -Wall --cc $(SRC_FILES) --exe $(CPP_FILES) --top-module $(TOP_MODULE) --trace --timing
	make -C obj_dir -f V$(TOP_MODULE).mk V$(TOP_MODULE)

clean:
	rm -rf obj_dir
	rm -f sim.vcd
	rm -f sim_reset_n_clock.vcd
	rm -f sim_load_value_mode0.vcd
	rm -f sim_load_value_mode1.vcd
	rm -f sim_load_value_mode2.vcd
	rm -f sim_load_value_mode3.vcd

.PHONY: all sim clean
