module bidirectional_spi (
    input wire [7:0]  transaction_length;
    input wire [31:0] transaction_data;
    input wire [31:0] transaction_rw_mask;
    output reg [31:0] transaction_read_data;

    input wire reset_n;
    input wire spi_clk; 

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