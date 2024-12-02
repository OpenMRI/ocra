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

    // SPI Mode control
    input wire spi_cpol,   // Clock polarity
    input wire spi_cpha,   // Clock phase

    inout wire spi_sdio,
    output reg spi_sclk,
    output reg spi_cs_n
);

  reg spi_dir;           // Direction control for the SPI interface (1 for write, 0 for read)
  reg shift_out;  // SPI Data to be shifted out

  // Some of our data in the spi_clk domain
  reg [TRANSACTION_LEN_WIDTH-1:0] bitcounter_sc, r_transaction_length;
  reg [TRANSACTION_LEN_WIDTH-1:0] read_bitcounter_sc;

  reg [DATA_WIDTH-1:0] transaction_rw_mask_sc, r_transaction_rw_mask;
  reg [DATA_WIDTH-1:0] transaction_data_sc, r_transaction_data;

  reg [TRANSACTION_LEN_WIDTH+DATA_WIDTH+DATA_WIDTH-1:0] sc_data, fc_data;

  reg [DATA_WIDTH-1:0] transaction_read_data_sc;

  assign fc_data = {r_transaction_length, r_transaction_rw_mask, r_transaction_data};

  assign spi_sdio = spi_dir ? shift_out : 1'bz;
  wire spi_data_clk;
  wire spi_clk, spi_clk_gen;

  reg to_spi_fifo_empty;
  
  // fabric side state machine states
  typedef enum logic [1:0] {
    F_IDLE,     
    F_WRITE,
    F_DONE
  } fstate_t;

  fstate_t fabric_state;

  // Fabric side state machine
  always @(posedge fabric_clk or negedge reset_n) begin
    if (~reset_n) begin
      to_spi_fifo_wr_en <= 1'b0;
      to_fabric_fifo_rd_en <= 1'b0;
      fabric_state <= F_IDLE;
      r_transaction_length <= 0;
      r_transaction_rw_mask <= 0;
      r_transaction_data <= 0;
    end else if (fabric_state == F_IDLE) begin
      if (transaction_length > 0) begin
        fabric_state <= F_WRITE;
        to_spi_fifo_wr_en <= 1'b1;
        r_transaction_length <= transaction_length;
        r_transaction_rw_mask <= transaction_rw_mask;
        r_transaction_data <= transaction_data;
      end else begin
        fabric_state <= F_IDLE;
      end
    end else if (fabric_state == F_WRITE) begin
      fabric_state <= F_IDLE;
      to_spi_fifo_wr_en <= 1'b0;
    end
  end 


  wire spi_clk_0,spi_clk_90;

  // Generate the clocks
  quadrature_clock_divider clock_div (
    .reset_n(reset_n),
    .clk_in(fabric_clk),
    .div_factor_4(2),
    .sck_0(spi_clk_0),
    .sck_90(spi_clk_90)
  );

  // Reset synchronizer
  wire reset_n_sc, reset_n_sc2;
  reset_synchronizer reset_sync (
    .reset_n(reset_n),
    .clk(spi_data_clk),
    .sync_reset_n(reset_n_sc)
  );

  
  reset_synchronizer reset_sync2 (
    .reset_n(reset_n),
    .clk(spi_clk),
    .sync_reset_n(reset_n_sc2)
  );
  

  // assign the SPI clocks based on the SPI mode
  spi_clock_generator spi_clock_gen (
    .clk_0(spi_clk_0),
    .clk_90(spi_clk_90),
    .cpol(spi_cpol),
    .cpha(spi_cpha),
    .spi_clk(spi_clk_gen),
    .shift_clk(spi_data_clk)
  );

  // I know this is super hacky, but it allows the logic below to look cleaner
  assign spi_clk = spi_cpol ? ~spi_clk_gen : spi_clk_gen;

  reg to_spi_fifo_rd_en, to_spi_fifo_wr_en;
  // Instantiate the asynchronous FIFO for the data going to the SPI side
  async_fifo #(
    .DATA_WIDTH(TRANSACTION_LEN_WIDTH+2*DATA_WIDTH),
    .ADDR_WIDTH(3)
  ) to_spi_fifo (
    .wr_clk(fabric_clk),
    .wr_rst_n(reset_n),
    .wr_data(fc_data),
    .wr_en(to_spi_fifo_wr_en),
    .rd_clk(spi_data_clk),
    .rd_rst_n(reset_n),
    .rd_data(sc_data),
    .rd_en(to_spi_fifo_rd_en),
    .empty(to_spi_fifo_empty),
    /* verilator lint_off PINCONNECTEMPTY */
    .almost_empty(),
    .full(),
    .almost_full()
    /* verilator lint_on PINCONNECTEMPTY */ 
  );

  reg to_fabric_fifo_full, to_fabric_fifo_wr_en, to_fabric_fifo_rd_en;

  // Instantiate the asynchronous FIFO for the data coming from the SPI side
  async_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(3)
  ) to_fabric_fifo (
    .wr_clk(spi_data_clk),
    .wr_rst_n(reset_n),
    .wr_data(transaction_read_data_sc),
    .wr_en(to_fabric_fifo_wr_en),
    .rd_clk(fabric_clk),
    .rd_rst_n(reset_n),
    .rd_data(transaction_read_data),
    .rd_en(to_fabric_fifo_rd_en),
    .full(to_fabric_fifo_full),
    /* verilator lint_off PINCONNECTEMPTY */
    .empty(),  
    .almost_empty(),
    .almost_full()
    /* verilator lint_on PINCONNECTEMPTY */ 
  );

  // SPI side reset logic
  always @(posedge spi_data_clk or negedge reset_n_sc) begin
    if (~reset_n_sc) begin
      spi_dir <= 1'b1;
      shift_out <= 1'b0;
      spi_cs_n <= 1'b1;
      to_fabric_fifo_wr_en <= 1'b0;
      to_spi_fifo_rd_en <= 1'b0;
      //read_bitcounter_sc <= 0;
    end
  end 

  // SPI state machine stuff
  typedef enum logic [2:0] {
    IDLE,
    FIFO_READ,     
    CS_ASSERT,
    WRITE,
    DONE
  } state_t;

  state_t spi_state;

  // reset the state machine
  always_ff @(posedge spi_data_clk or negedge reset_n_sc) begin
    if (~reset_n_sc) begin
      spi_state <= IDLE;
      spi_clock_hot <= 1'b0;
    end
  end 

  // combinatorial logic to assign the SPI clock
  assign spi_sclk = spi_clk_en ? (spi_cpol ? ~spi_clk : spi_clk) : spi_cpol;

  reg spi_clk_en;

  // Synchronize the SPI clock enable signal
  always_ff @(posedge spi_clk or negedge reset_n_sc2) begin
    if (~reset_n_sc2) begin
      spi_clk_en <= 1'b0;
    end else if (spi_clock_hot) begin
      spi_clk_en <= 1'b1;
      if (spi_dir == 0) begin
        read_bitcounter_sc <= read_bitcounter_sc + 1;
        transaction_read_data_sc[bitcounter_sc -1] <= spi_sdio;
      end
    end else begin
      spi_clk_en <= 1'b0;
    end
  end

  reg spi_clock_hot;

  always_ff @(posedge spi_data_clk or negedge reset_n_sc) begin
    if (reset_n_sc) begin
      if (spi_state == IDLE) begin
        to_fabric_fifo_wr_en <= 1'b0;
        shift_out <= 1'b0;
        if(~to_spi_fifo_empty) begin
          spi_state <= FIFO_READ;
          to_spi_fifo_rd_en <= 1'b1; // assert the read enable
         end else begin
          spi_state <= IDLE;
         end
      end else if (spi_state == FIFO_READ) begin
        spi_state <= WRITE;
        spi_cs_n <= 1'b0;
        to_spi_fifo_rd_en <= 1'b0; // deassert the read enable
         // copy the data from the fifo
        bitcounter_sc <= sc_data[TRANSACTION_LEN_WIDTH+DATA_WIDTH+DATA_WIDTH-1:DATA_WIDTH+DATA_WIDTH];
        transaction_rw_mask_sc <= sc_data[DATA_WIDTH+DATA_WIDTH-1:DATA_WIDTH];
        transaction_data_sc <= sc_data[DATA_WIDTH-1:0];

        /*
        read_bitcounter_sc <= 0;
        transaction_read_data_sc <= 0;
        */
        if (spi_cpha) begin
          spi_clock_hot <= 1'b1;
        end
      end else if (spi_state == CS_ASSERT) begin
        spi_state <= WRITE;
        spi_cs_n <= 1'b0;
      end else if (spi_state == WRITE) begin
        if (bitcounter_sc == 0) begin
          spi_state <= DONE;
          spi_cs_n <= 1'b1;
          spi_dir <= 1'b1;
          spi_clock_hot <= 1'b0;
          shift_out <= 0;
        end else begin
          if (spi_cpha && bitcounter_sc == 1) begin
            spi_clock_hot <= 1'b0;
          end else begin
            spi_clock_hot <= 1'b1;
          end
          spi_state <= WRITE;
          spi_dir <= transaction_rw_mask_sc[bitcounter_sc - 1];
          if (transaction_rw_mask_sc[bitcounter_sc - 1]) begin
            shift_out <= transaction_data_sc[bitcounter_sc - 1];
          end else begin
            shift_out <= 0;
          end
          bitcounter_sc <= bitcounter_sc - 1;
          /*
          if (~transaction_rw_mask_sc[bitcounter_sc - 1]) begin
            read_bitcounter_sc <= read_bitcounter_sc + 1;
            transaction_read_data_sc[bitcounter_sc -1] <= spi_sdio;
          end else begin
            // this is to fill in blank bits if the mask is not continuous
            transaction_read_data_sc[bitcounter_sc -1] <= 0;
          end
          */
        end
      end else if (spi_state == DONE) begin
        shift_out <= 1'b0;
        if (read_bitcounter_sc == 0) begin
          spi_state <= IDLE;
          to_fabric_fifo_wr_en <= 1'b0;
        end else if (~to_fabric_fifo_full) begin
          spi_state <= IDLE;
          to_fabric_fifo_wr_en <= 1'b1;
        end else begin
          spi_state <= DONE;
        end
      end
    end
  end

  endmodule

