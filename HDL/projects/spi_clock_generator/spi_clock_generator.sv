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
            if (cpha == 0) begin
                spi_clk = clk_90;   // SPI mode 0
                shift_clk = clk_0;  
            end else begin
                spi_clk = clk_0;  // SPI mode 1
                shift_clk = clk_90;
            end
        end else begin
            if (cpha == 0) begin
                spi_clk = ~clk_90;   // SPI mode 2
                shift_clk = clk_0;
            end else begin
                spi_clk = ~clk_0;  // SPI mode 3
                shift_clk = clk_90;
            end
        end
    end

endmodule
