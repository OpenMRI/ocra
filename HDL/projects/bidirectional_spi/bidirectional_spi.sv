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
)(
    input wire [TRANSACTION_LEN_WIDTH-1:0]  transaction_length,
    input wire [DATA_WIDTH-1:0] transaction_data,
    input wire [DATA_WIDTH-1:0] transaction_rw_mask,
    output reg [DATA_WIDTH-1:0] transaction_read_data,

    input wire reset_n,
    input wire fabric_clk,
    input wire spi_clk_0,  // 0 degree clock
    input wire spi_clk_90, // 90 degree clock 
    // SPI Mode control
    input wire spi_cpol,   // Clock polarity
    input wire spi_cpha,   // Clock phase

    inout wire spi_sdio,
    output reg spi_sclk,
    output reg spi_cs_n
);

  reg spi_dir;           // Direction control for the SPI interface (1 for write, 0 for read)
  reg [DATA_WIDTH-1:0] shift_out;  // SPI Data to be shifted out
  reg [DATA_WIDTH-1:0] shift_in;   // SPI Data to be shifted in
  assign spi_sdio = spi_dir ? shift_out[31] : 1'bz;
  wire spi_data_clk;

  // Reset logic for the core
  always @(posedge fabric_clk or negedge reset_n) begin
    if (~reset_n) begin
        spi_dir <= 1'b1;
        shift_out <= 32'b0;
        shift_in <= 32'b0;
        spi_sclk <= 1'b0;
        spi_cs_n <= 1'b1;
    end
  end 

  // assign the SPI clocks based on the SPI mode
  spi_clock_generator #(
    .DATA_WIDTH(DATA_WIDTH)
  ) spi_clock_gen (
    .clk_0(spi_clk_0),
    .clk_90(spi_clk_90),
    .cpol(spi_cpol),
    .cpha(spi_cpha),
    .spi_clk(spi_data_clk),
    .shift_clk(spi_sclk)
  );

  // Instantiate the asynchronous FIFO for the transaction length
  async_fifo #(
    .DATA_WIDTH(TRANSACTION_LEN_WIDTH),
    .ADDR_WIDTH(3)
  ) fifo (
    .wr_clk(fabric_clk),
    .wr_rst_n(reset_n),
    .wr_data(transaction_length),
    .wr_en(1'b1),
    .rd_clk(spi_data_clk),
    .rd_rst_n(reset_n),
    .rd_data(transaction_length),
    .rd_en(1'b1),
    .empty(),
    .almost_empty()
  );


  endmodule

