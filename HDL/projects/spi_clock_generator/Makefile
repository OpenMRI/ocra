VERILATOR = verilator
TOP_MODULE = spi_clock_generator
VERILATED = obj_dir/V$(TOP_MODULE)

SRC_FILES = spi_clock_generator.sv
CPP_FILES = spi_clock_generator_tb.cpp

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
