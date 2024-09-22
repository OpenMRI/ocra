VERILATOR = verilator
TOP_MODULE = async_fifo
VERILATED = obj_dir/V$(TOP_MODULE)

SRC_FILES = async_fifo.sv
CPP_FILES = main.cpp

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
