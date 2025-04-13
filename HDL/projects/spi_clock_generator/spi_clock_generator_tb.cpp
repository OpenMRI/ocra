#include <iostream>
#include <verilated.h>
#include <verilated_vcd_c.h>
#include "Vspi_clock_generator.h" // Include the generated Verilator header

// Define clock signal generation helper
void toggle_clock(bool &clk)
{
    clk = !clk;
}

int main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // Instantiate the DUT (Device Under Test)
    Vspi_clock_generator *dut = new Vspi_clock_generator;

    // Initialize trace file
    VerilatedVcdC *vcd = new VerilatedVcdC;
    dut->trace(vcd, 10);
    vcd->open("spi_clock_generator.vcd");

    // Simulation variables
    bool clk_0 = 0;  // Clock signal (0° phase)
    bool clk_90 = 0; // Clock signal (90° phase)
    int clk_0_count = 0;

    // Test CPOL and CPHA configurations
    // The way of doing these tests is causing ugly glitches in the cpol=1 case
    for (int cpol = 0; cpol <= 1; ++cpol)
    {
        for (int cpha = 0; cpha <= 1; ++cpha)
        {
            // Initialize DUT inputs
            dut->cpol = cpol;
            dut->cpha = cpha;

            // Run simulation for a few clock cycles
            for (int i = 0; i < 20; ++i)
            {
                // Toggle clocks
                if (clk_0_count % 2 == 0)
                    toggle_clock(clk_0);
                if (clk_0_count % 2 == 1)
                    toggle_clock(clk_90); // 90° phase assumes clk_90 toggles half as often

                // Drive inputs
                dut->clk_0 = clk_0;
                dut->clk_90 = clk_90;

                // Evaluate the DUT
                dut->eval();
                vcd->dump(clk_0_count);
                // Print results
                std::cout << "CPOL: " << cpol
                          << " CPHA: " << cpha
                          << " clk_0: " << clk_0
                          << " clk_90: " << clk_90
                          << " spi_clk: " << (dut->spi_clk ? "1" : "0")
                          << " shift_clk: " << (dut->shift_clk ? "1" : "0")
                          << std::endl;

                // Increment clock cycle count
                clk_0_count++;
            }
        }
    }

    // Cleanup
    dut->final();
    vcd->close();
    delete dut;
    return 0;
}