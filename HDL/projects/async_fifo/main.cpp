// main.cpp
#include "Vtb_async_fifo.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <iostream>
#include <fstream>

int main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);

    // Instantiate the top module
    Vtb_async_fifo *top = new Vtb_async_fifo;

    // Initialize simulation inputs
    top->wr_clk = 0;
    top->rd_clk = 0;
    top->wr_rst_n = 0;
    top->rd_rst_n = 0;
    top->wr_en = 0;
    top->rd_en = 0;

    // Variables for simulation
    vluint64_t main_time = 0;           // Current simulation time
    const vluint64_t sim_time = 100000; // Adjust as needed

    // Open VCD dump file
    Verilated::traceEverOn(true);
    VerilatedVcdC *tfp = new VerilatedVcdC;
    top->trace(tfp, 99); // Trace 99 levels of hierarchy
    tfp->open("sim.vcd");

    // Reset sequence
    while (main_time < 20)
    {
        top->wr_clk = !top->wr_clk;
        top->rd_clk = !top->rd_clk;
        top->eval();
        tfp->dump(main_time);
        main_time++;
    }
    top->wr_rst_n = 1;
    top->rd_rst_n = 1;

    bool prev_wr_clk = 0;
    bool prev_rd_clk = 0;

    while (main_time < sim_time)
    {
        // Toggle clocks
        if ((main_time % 5) == 0)
        {
            top->wr_clk = !top->wr_clk;
        }
        if ((main_time % 7) == 0)
        {
            top->rd_clk = !top->rd_clk;
        }

        // Write process
        if (top->wr_clk && !prev_wr_clk)
        { // Rising edge of wr_clk
            if (main_time > 20)
            { // After reset
                if (!top->full)
                {
                    top->wr_en = 1;
                    top->wr_data = wr_data;
                    wr_data++;
                    write_count++;
                }
                else
                {
                    top->wr_en = 0;
                }
            }
        }
        prev_wr_clk = top->wr_clk;

        // Read process
        if (top->rd_clk && !prev_rd_clk)
        { // Rising edge of rd_clk
            if (main_time > 20)
            { // After reset
                if (!top->empty)
                {
                    top->rd_en = 1;
                }
                else
                {
                    top->rd_en = 0;
                }

                // Data integrity check
                if (top->rd_en && !top->empty)
                {
                    if (top->rd_data != expected_data)
                    {
                        std::cout << "ERROR: Data Mismatch at time " << main_time
                                  << ": Expected " << expected_data << ", Got " << top->rd_data << std::endl;
                        exit(1);
                    }
                    expected_data++;
                    read_count++;
                }
            }
        }
        prev_rd_clk = top->rd_clk;

        // Check for simulation end
        if (write_count >= 50 && read_count >= 50)
        {
            std::cout << "Simulation completed successfully at time " << main_time << std::endl;
            break;
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
