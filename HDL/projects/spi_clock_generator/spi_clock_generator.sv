module spi_clock_generator (
    input  wire clk_0,             // External clock (0° phase)
    input  wire clk_90,            // External clock (90° phase)
    input  wire cpol,              // Clock Polarity
    input  wire cpha,              // Clock Phase
    output logic spi_clk,          // Generated SPI clock
    output logic shift_clk         // Data shift clock
);

    // Generate spi_clk based on cpol
    always_comb begin
        if (cpol == 0) begin
            spi_clk = clk_0;       // SPI clock idle state low
        end else begin
            spi_clk = ~clk_0;      // SPI clock idle state high
        end
    end

    // Generate shift_clk based on cpha
    always_comb begin
        if (cpha == 0) begin
            shift_clk = clk_0;     // Sample on first edge of spi_clk
        end else begin
            shift_clk = clk_90;    // Sample on second edge of spi_clk
        end
    end

endmodule