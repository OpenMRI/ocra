# async_fifo

This project is to build and understand asynchronous FIFOs for clock-domain crossing. 

At the same time this is also a testbed on how to leverage both verilator and Vivado techniques to generate simulations and reports on
clock-domain crossing issues.

## Requirements

This project requires verilator and a tool to display the simulations. There are either gtkwave or surfer project that I would recommend.


## Stuff

Run the synthesis check in vivado
vivado -mode batch -source synth_async_fifo_project.tcl