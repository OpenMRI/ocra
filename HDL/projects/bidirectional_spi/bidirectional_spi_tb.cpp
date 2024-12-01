// main.cpp
#include "Vbidirectional_spi.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <iostream>
#include <fstream>

int main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);

    // Instantiate the top module
    Vbidirectional_spi *top = new Vbidirectional_spi;

    // Initialize simulation inputs
    top->transaction_length = 0;
    top->transaction_data = 0;
    top->transaction_rw_mask = 0;
    top->transaction_read_data = 0;
    top->reset_n = 0;
    top->fabric_clk = 0;
    top->spi_cpol = 0;
    top->spi_cpha = 0;
    top->spi_sdio = 0;

    // Variables for simulation
    vluint64_t main_time = 0;            // Current simulation time
    const vluint64_t sim_time = 4000000; // Adjust as needed

    // Open VCD dump file
    Verilated::traceEverOn(true);
    VerilatedVcdC *tfp = new VerilatedVcdC;
    top->trace(tfp, 99); // Trace 99 levels of hierarchy
    tfp->open("sim.vcd");

    // Reset sequence
    while (main_time < 20)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();
        tfp->dump(main_time);
        main_time++;
    }
    top->reset_n = 1;

    while (main_time < sim_time)
    {
        // Toggle clocks
        if ((main_time % 5) == 0)
        {
            top->fabric_clk = !top->fabric_clk;
        }

        top->eval();          // Evaluate model
        tfp->dump(main_time); // Dump signals to VCD file

        main_time++;
    }

    // Cleanup
    tfp->close();
    delete top;
    return 0;
}
