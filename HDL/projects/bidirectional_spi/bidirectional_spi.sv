// bidirectional_spi module
// This module implements a bidirectional SPI interface with the following features:
// - uses a mask to determine which bits are written or read
// - supports all four SPI modes (CPOL=0, CPHA=0; CPOL=0, CPHA=1; CPOL=1, CPHA=0; CPOL=1, CPHA=1)
// - supports configurable data width
// - supports input of an arbitary quadrature clock for SPI clocking
// - raise an error flag if invalid parameters are used
// Bidirectional SPI is an interface where the data can be written and read using a single wire.
// this is also known as half-duplex SPI.
// this core can be adapted to full-duplex SPI by adding a second data wire.
module bidirectional_spi #(
  parameter DATA_WIDTH = 32,
  parameter TRANSACTION_LEN_WIDTH = 8
)
(
    input wire [TRANSACTION_LEN_WIDTH-1:0]  transaction_length;
    input wire [DATA_WIDTH-1:0] transaction_data;
    input wire [DATA_WIDTH-1:0] transaction_rw_mask;
    output reg [DATA_WIDTH-1:0] transaction_read_data;

    input wire reset_n;
    input wire fabric_clk;
    input wire spi_clk_0;  // 0 degree clock
    input wire spi_clk_90; // 90 degree clock 
    // SPI Mode control
    input wire spi_cpol;   // Clock polarity
    input wire spi_cpha;   // Clock phase

    inout wire spi_sdio;
    output reg spi_sclk;
    output reg spi_cs_n;
);

  reg spi_dir;           // Direction control for the SPI interface (1 for write, 0 for read)
  reg [31:0] shift_out;  // SPI Data to be shifted out
  reg [31:0] shift_in;   // SPI Data to be shifted in
  assign spi_sdio = spi_dir ? shift_out[31] : 1'bz;

   
  // State Machine to Control the SPI Interface
  always @(posedge spi_clk or negedge reset_n) begin
    if (~reset_n) begin
        spi_dir <= 1'b1;
        shift_out <= 32'b0;
        shift_in <= 32'b0;  
        spi
    end