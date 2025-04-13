/* a top level module with built-in clock divider */
module half_duplex_spi_master_clkdiv #(
  parameter DATA_WIDTH = 32,
  parameter TRANSACTION_LEN_WIDTH = 6,
  parameter CLOCK_DIVIDER = 1
)(
    input wire [TRANSACTION_LEN_WIDTH-1:0]  transaction_length,
    input wire [DATA_WIDTH-1:0] transaction_data,
    input wire [DATA_WIDTH-1:0] transaction_rw_mask,
    output reg [DATA_WIDTH-1:0] transaction_read_data,

    input wire reset_n,
    input wire fabric_clk,

    // SPI Mode control
    input wire spi_cpol,   // Clock polarity
    input wire spi_cpha,   // Clock phase

    inout wire spi_sdio,
    output reg spi_sclk,
    output reg spi_cs_n
);

wire spi_clk_gen;

// Generate the clocks
quadrature_clock_divider clock_div (
  .reset_n(reset_n),
  .clk_in(fabric_clk),
  .div_factor_4(CLOCK_DIVIDER),
  .sck_0(spi_clk_gen),
  /* verilator lint_off PINCONNECTEMPTY */
  .sck_90()
  /* verilator lint_on PINCONNECTEMPTY */
  );

// Instantiate the spi_master core
half_duplex_spi_master #(
  .DATA_WIDTH(DATA_WIDTH), .TRANSACTION_LEN_WIDTH(TRANSACTION_LEN_WIDTH)
) hdsm (
  .transaction_length(transaction_length),
  .transaction_data(transaction_data),
  .transaction_rw_mask(transaction_rw_mask),
  .transaction_read_data(transaction_read_data),
  .reset_n(reset_n),
  .fabric_clk(fabric_clk),
  .spi_clk_in(spi_clk_gen),
  .spi_cpol(spi_cpol),
  .spi_cpha(spi_cpha), 

  .spi_sdio(spi_sdio),
  .spi_sclk(spi_sclk),
  .spi_cs_n(spi_cs_n)
);

endmodule
