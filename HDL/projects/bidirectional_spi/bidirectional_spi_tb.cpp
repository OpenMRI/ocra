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
    vluint64_t main_time = 0;                      // Current simulation time
    const vluint64_t sim_time_reset_n_clock = 100; // Adjust as needed
    const vluint64_t sim_load_value_fifo = 600;    // Adjust as needed

    // Open VCD dump file
    Verilated::traceEverOn(true);
    VerilatedVcdC *tfp = new VerilatedVcdC;
    VerilatedVcdC *tfp2 = new VerilatedVcdC;
    VerilatedVcdC *tfp3 = new VerilatedVcdC;
    VerilatedVcdC *tfp4 = new VerilatedVcdC;
    VerilatedVcdC *tfp5 = new VerilatedVcdC;

    top->trace(tfp, 99); // Trace 99 levels of hierarchy
    tfp->open("sim_reset_n_clock.vcd");

    // Reset sequence
    while (main_time < 20)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();
        tfp->dump(main_time);
        main_time++;
    }
    top->reset_n = 1;

    while (main_time < sim_time_reset_n_clock)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();          // Evaluate model
        tfp->dump(main_time); // Dump signals to VCD file

        main_time++;
    }

    // Cleanup sim file
    tfp->close();

    top->trace(tfp2, 99); // Trace 99 levels of hierarchy
    tfp2->open("sim_load_value_mode0.vcd");
    main_time = 0; // Reset time

    top->spi_cpol = 0;
    top->spi_cpha = 0;

    // Reset sequence
    while (main_time < 20)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();
        tfp2->dump(main_time);
        main_time++;
    }
    top->reset_n = 1;

    while (main_time < sim_load_value_fifo)
    {
        if (main_time == 20)
        {
            top->transaction_length = 24;
            top->transaction_data = 0xAAA00F0F;
            top->transaction_rw_mask = 0x00FFFFFF;
        }
        else
        {
            top->transaction_length = 0;
            top->transaction_data = 0x00000000;
            top->transaction_rw_mask = 0x00000000;
        }
        top->fabric_clk = !top->fabric_clk;
        top->eval();           // Evaluate model
        tfp2->dump(main_time); // Dump signals to VCD file

        main_time++;
    }
    // cleanup sim file
    tfp2->close();

    top->trace(tfp3, 99); // Trace 99 levels of hierarchy
    tfp3->open("sim_load_value_mode1.vcd");
    main_time = 0; // Reset time

    top->spi_cpol = 0;
    top->spi_cpha = 1;
    // Reset sequence
    while (main_time < 20)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();
        tfp3->dump(main_time);
        main_time++;
    }
    top->reset_n = 1;

    while (main_time < sim_load_value_fifo)
    {
        if (main_time == 20)
        {
            top->transaction_length = 24;
            top->transaction_data = 0xAAA00F0F;
            top->transaction_rw_mask = 0x00FFFFFF;
        }
        else
        {
            top->transaction_length = 0;
            top->transaction_data = 0x00000000;
            top->transaction_rw_mask = 0x00000000;
        }
        top->fabric_clk = !top->fabric_clk;
        top->eval();           // Evaluate model
        tfp3->dump(main_time); // Dump signals to VCD file

        main_time++;
    }
    // cleanup sim file
    tfp3->close();

    top->trace(tfp4, 99); // Trace 99 levels of hierarchy
    tfp4->open("sim_load_value_mode2.vcd");
    main_time = 0; // Reset time

    top->spi_cpol = 1;
    top->spi_cpha = 0;

    // Reset sequence
    while (main_time < 20)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();
        tfp4->dump(main_time);
        main_time++;
    }
    top->reset_n = 1;

    while (main_time < sim_load_value_fifo)
    {
        if (main_time == 20)
        {
            top->transaction_length = 24;
            top->transaction_data = 0xAAA00F0F;
            top->transaction_rw_mask = 0x00FFFFFF;
        }
        else
        {
            top->transaction_length = 0;
            top->transaction_data = 0x00000000;
            top->transaction_rw_mask = 0x00000000;
        }
        top->fabric_clk = !top->fabric_clk;
        top->eval();           // Evaluate model
        tfp4->dump(main_time); // Dump signals to VCD file

        main_time++;
    }
    // cleanup sim file
    tfp4->close();

    top->trace(tfp5, 99); // Trace 99 levels of hierarchy
    tfp5->open("sim_load_value_mode3.vcd");
    main_time = 0; // Reset time

    top->spi_cpol = 1;
    top->spi_cpha = 1;
    // Reset sequence
    while (main_time < 20)
    {
        top->fabric_clk = !top->fabric_clk;
        top->eval();
        tfp5->dump(main_time);
        main_time++;
    }
    top->reset_n = 1;

    while (main_time < sim_load_value_fifo)
    {
        if (main_time == 20)
        {
            top->transaction_length = 24;
            top->transaction_data = 0xAAA00F0F;
            top->transaction_rw_mask = 0x00FFFFFF;
        }
        else
        {
            top->transaction_length = 0;
            top->transaction_data = 0x00000000;
            top->transaction_rw_mask = 0x00000000;
        }
        top->fabric_clk = !top->fabric_clk;
        top->eval();           // Evaluate model
        tfp5->dump(main_time); // Dump signals to VCD file

        main_time++;
    }
    // cleanup sim file
    tfp5->close();
    delete top;
    return 0;
}
