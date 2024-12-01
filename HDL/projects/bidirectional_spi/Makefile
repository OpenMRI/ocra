VERILATOR = verilator
TOP_MODULE = bidirectional_spi
VERILATED = obj_dir/V$(TOP_MODULE)

SRC_FILES = bidirectional_spi.sv ../async_fifo/async_fifo.sv ../spi_clock_generator/spi_clock_generator.sv ../reset_synchronizer/reset_synchronizer.sv ../quadrature_clock_divider/quadrature_clock_divider.sv
CPP_FILES = bidirectional_spi_tb.cpp

all: sim

sim: $(VERILATED)
	./$(VERILATED)

$(VERILATED): $(SRC_FILES) $(CPP_FILES)
	$(VERILATOR) -Wall --cc $(SRC_FILES) --exe $(CPP_FILES) --top-module $(TOP_MODULE) --trace --timing
	make -C obj_dir -f V$(TOP_MODULE).mk V$(TOP_MODULE)

clean:
	rm -rf obj_dir
	rm -f sim.vcd

.PHONY: all sim clean
