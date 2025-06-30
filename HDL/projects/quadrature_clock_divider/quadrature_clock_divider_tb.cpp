// main.cpp
#include "Vquadrature_clock_divider.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <iostream>
#include <fstream>

int main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);

    // Instantiate the top module
    Vquadrature_clock_divider *top = new Vquadrature_clock_divider;

    // Initialize simulation inputs
    top->reset_n = 0;
    top->div_factor_4 = 1;
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
        top->clk_in = !top->clk_in;
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
            top->clk_in = !top->clk_in;
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
