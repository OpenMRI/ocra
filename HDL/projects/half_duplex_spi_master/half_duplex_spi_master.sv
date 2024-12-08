// half_duplex_spi_master module
// This module implements a half-duplex (bidirectional) SPI master interface with the following features:
// - uses a mask to determine which bits are written or read
// - supports all four SPI modes (CPOL=0, CPHA=0; CPOL=0, CPHA=1; CPOL=1, CPHA=0; CPOL=1, CPHA=1)
// - supports configurable data width
// - supports input of an arbitary spi clock
// - raise an error flag if invalid parameters are used
// Half-duplex SPI is an interface where the data can be written and read using a single wire.
module half_duplex_spi_master #(
  parameter DATA_WIDTH = 32,
  parameter TRANSACTION_LEN_WIDTH = 6
)(
    input wire [TRANSACTION_LEN_WIDTH-1:0]  transaction_length,
    input wire [DATA_WIDTH-1:0] transaction_data,
    input wire [DATA_WIDTH-1:0] transaction_rw_mask,
    output reg [DATA_WIDTH-1:0] transaction_read_data,

    input wire reset_n,
    input wire fabric_clk,
    input wire spi_clk_in,

    // SPI Mode control
    input wire spi_cpol,   // Clock polarity
    input wire spi_cpha,   // Clock phase

    // The 3-wire output
    inout wire spi_sdio,
    output reg spi_sclk,
    output reg spi_cs_n
);

  reg spi_dir;           // Direction control for the SPI interface (1 for write, 0 for read)
  reg shift_out;  // SPI Data to be shifted out
  reg r_spi_cpol, r_spi_cpha, spi_cpol_sc, spi_cpha_sc;

  localparam BIT_COUNT_WIDTH = $clog2(DATA_WIDTH);

  // Some of our data in the spi_clk domain
  reg [TRANSACTION_LEN_WIDTH-1:0] r_transaction_length;
  reg [BIT_COUNT_WIDTH:0] bitcounter_sc, read_bitcounter_sc;

  //reg [DATA_WIDTH-1:0] transaction_rw_mask_sc
  reg [DATA_WIDTH-1:0] r_transaction_rw_mask;
  //reg [DATA_WIDTH-1:0] transaction_data_sc, 
  reg [DATA_WIDTH-1:0] r_transaction_data;
  reg [DATA_WIDTH-1:0] r_transaction_read_data, f_transaction_read_data;

  reg [2+TRANSACTION_LEN_WIDTH+DATA_WIDTH+DATA_WIDTH-1:0] sc_data, fc_data;

  reg [DATA_WIDTH-1:0] transaction_read_data_sc;
  
  assign fc_data = {r_spi_cpol, r_spi_cpha, r_transaction_length, r_transaction_rw_mask, r_transaction_data};

  assign spi_sdio = spi_dir ? shift_out : 1'bz;

  assign transaction_read_data = r_transaction_read_data;

  wire spi_clk;

  reg to_spi_fifo_empty;

  // fabric side state machine states
  typedef enum logic [1:0] {
    F_IDLE,     
    F_WRITE,
    F_READ,
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
      r_spi_cpol <= 0;
      r_spi_cpha <= 0;
    end else if (fabric_state == F_IDLE) begin
      if (transaction_length > 0) begin
        fabric_state <= F_WRITE;
        to_spi_fifo_wr_en <= 1'b1;
        r_transaction_length <= transaction_length;
        r_transaction_rw_mask <= transaction_rw_mask;
        r_transaction_data <= transaction_data;
        r_spi_cpol <= spi_cpol;
        r_spi_cpha <=  spi_cpha;
      end else begin
        fabric_state <= F_IDLE;
      end
      // check if there is something to read
      if (~to_fabric_fifo_empty) begin
        to_fabric_fifo_rd_en <= 1'b1;
        fabric_state <= F_READ;
      end else begin
        to_fabric_fifo_rd_en <= 1'b0;
      end
    end else if (fabric_state == F_WRITE) begin
      fabric_state <= F_IDLE;
      to_spi_fifo_wr_en <= 1'b0;
    end else if (fabric_state == F_READ) begin
      to_fabric_fifo_rd_en <= 1'b0;
      fabric_state <= F_IDLE;
      // should also copy the data from the FIFO
      r_transaction_read_data <= f_transaction_read_data;
    end
  end

  // Reset synchronizer
  wire reset_n_sc;

  reset_synchronizer reset_sync (
    .reset_n(reset_n),
    .clk(spi_clk),
    .sync_reset_n(reset_n_sc)
  );
  
  // I know this is super hacky, but it allows the logic below to look cleaner
  assign spi_clk = spi_cpol_sc ? ~spi_clk_in : spi_clk_in;

  reg to_spi_fifo_rd_en, to_spi_fifo_wr_en;
  // Instantiate the asynchronous FIFO for the data going to the SPI side
  async_fifo #(
    .DATA_WIDTH(2+TRANSACTION_LEN_WIDTH+2*DATA_WIDTH),
    .ADDR_WIDTH(3)
  ) to_spi_fifo (
    .wr_clk(fabric_clk),
    .wr_rst_n(reset_n),
    .wr_data(fc_data),
    .wr_en(to_spi_fifo_wr_en),
    .rd_clk(spi_clk),
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

  reg to_fabric_fifo_full, to_fabric_fifo_empty, to_fabric_fifo_wr_en, to_fabric_fifo_rd_en;

  // Instantiate the asynchronous FIFO for the data coming from the SPI side
  async_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(3)
  ) to_fabric_fifo (
    .wr_clk(spi_clk),
    .wr_rst_n(reset_n),
    .wr_data(transaction_read_data_sc),
    .wr_en(to_fabric_fifo_wr_en),
    .rd_clk(fabric_clk),
    .rd_rst_n(reset_n),
    .rd_data(f_transaction_read_data),
    .rd_en(to_fabric_fifo_rd_en),
    .full(to_fabric_fifo_full),
    .empty(to_fabric_fifo_empty),
    /* verilator lint_off PINCONNECTEMPTY */
    .almost_empty(),
    .almost_full()
    /* verilator lint_on PINCONNECTEMPTY */ 
  );

  // SPI state machine stuff
  typedef enum logic [2:0] {
    IDLE,
    FIFO_READ,     
    CS_ASSERT,
    READ,
    WRITE,
    DONE,
    FIFO_WRITE
  } state_t;

  /* verilator lint_off UNUSEDSIGNAL */
  state_t spi_state, next_spi_state;
  /* verilator lint_on UNUSEDSIGNAL */

  // combinatorial logic to assign the SPI clock
  assign spi_sclk = spi_clock_hot ? (spi_cpol_sc ? ~spi_clk : spi_clk) : spi_cpol_sc;

  reg spi_clock_hot;
  reg [DATA_WIDTH-1:0] shiftout_register, rw_shift_register, shiftin_register;

  assign transaction_read_data_sc = shiftin_register;

  // traditional FSM pattern

  always_comb begin
    next_spi_state = spi_state;

    case (spi_state)
      IDLE: begin
        if(~to_spi_fifo_empty) next_spi_state = FIFO_READ;
      end

      FIFO_READ: begin
        next_spi_state = CS_ASSERT;
      end

      CS_ASSERT: begin
        if (rw_shift_register[DATA_WIDTH-1]) begin
          next_spi_state = WRITE;
        end else begin
          next_spi_state = READ;
        end
      end

      WRITE: begin
        if (bitcounter_sc == 0) begin
          next_spi_state = DONE;
        end else if (~rw_shift_register[DATA_WIDTH-1]) begin
          next_spi_state = READ;
        end
      end

      READ: begin
        if (bitcounter_sc == 0) begin
          next_spi_state = DONE;
        end else if (rw_shift_register[DATA_WIDTH-1]) begin
          next_spi_state = WRITE;
        end
      end

      DONE: begin
        if (read_bitcounter_sc == 0 || to_fabric_fifo_full) begin
          next_spi_state = IDLE;
        end else begin
          next_spi_state = FIFO_WRITE;
        end
      end

      FIFO_WRITE: next_spi_state = IDLE;

      default: next_spi_state = IDLE;
    endcase
  end

  always_ff @(posedge spi_clk or negedge spi_clk or negedge reset_n_sc) begin
    if (~reset_n_sc) begin
      spi_dir <= 1'b1;
      shift_out <= 1'b0;
      spi_cs_n <= 1'b1;
      to_spi_fifo_rd_en <= 1'b0;
      to_fabric_fifo_wr_en <= 1'b0;
      spi_state <= IDLE;
      spi_clock_hot <= 1'b0;
      read_bitcounter_sc <= 0;
      shiftin_register <= 0;
      // pickup the mode on reset
      spi_cpol_sc <= spi_cpol;
      spi_cpha_sc <= spi_cpha;
    end else begin
      if (spi_state == IDLE) begin
        to_fabric_fifo_wr_en <= 1'b0;
        shift_out <= 1'b0;
        spi_cs_n <= 1'b1;
        read_bitcounter_sc <= 0;
        shiftin_register <= 0;
        if(~to_spi_fifo_empty) begin
          spi_state <= FIFO_READ;
          to_spi_fifo_rd_en <= 1'b1; // assert the read enable
         end else begin
          spi_state <= IDLE;
         end
      end else if (spi_state == FIFO_READ) begin
        spi_state <= CS_ASSERT;
        to_spi_fifo_rd_en <= 1'b0; // deassert the read enable
        // copy the data from the fifo
        spi_cpol_sc <= sc_data[TRANSACTION_LEN_WIDTH+DATA_WIDTH+DATA_WIDTH+1];
        spi_cpha_sc <= sc_data[TRANSACTION_LEN_WIDTH+DATA_WIDTH+DATA_WIDTH];
        bitcounter_sc <= sc_data[TRANSACTION_LEN_WIDTH+DATA_WIDTH+DATA_WIDTH-1:DATA_WIDTH+DATA_WIDTH];
        shiftout_register <= sc_data[DATA_WIDTH-1:0];
        rw_shift_register <= sc_data[DATA_WIDTH+DATA_WIDTH-1:DATA_WIDTH];
      end else if (spi_state == CS_ASSERT) begin
        if (rw_shift_register[DATA_WIDTH-1]) begin
          spi_state <= WRITE;
        end else begin
          spi_state <= READ;
        end
        spi_cs_n <= 1'b0;
        spi_clock_hot <= 1'b1;

        // deal with the write case for Mode 0 & 2, I doubt there is a read case here
        // at all directly after CS is asserted
        if (~spi_clk && ~spi_cpha_sc && spi_dir) begin
          spi_dir <= rw_shift_register[DATA_WIDTH-1];
          rw_shift_register <= {rw_shift_register[DATA_WIDTH-2:0], 1'b0};

          shift_out <= shiftout_register[DATA_WIDTH-1];
          shiftout_register <= {shiftout_register[DATA_WIDTH-2:0],1'b0};
          shiftin_register <= {shiftin_register[DATA_WIDTH-2:0],1'b0};
          if (spi_dir == rw_shift_register[DATA_WIDTH-1]) begin
            bitcounter_sc <= bitcounter_sc - 1;
          end
        end

      end else if (spi_state == WRITE) begin
        if (bitcounter_sc == 0) begin
          spi_state <= DONE;
        end else begin
          spi_state <= WRITE;
        end

        // all valid transitions that advance the state machine
        if ((spi_clk && spi_cpha_sc) || (~spi_clk && ~spi_cpha_sc)) begin
          spi_dir <= rw_shift_register[DATA_WIDTH-1];
          rw_shift_register <= {rw_shift_register[DATA_WIDTH-2:0], 1'b0};
          if (rw_shift_register[DATA_WIDTH-1]) begin
            // only decrement when direction stays the same
            bitcounter_sc <= bitcounter_sc - 1;
          end else begin
            spi_state <= READ;
          end
        end

        if (((spi_clk && spi_cpha_sc) || (~spi_clk && ~spi_cpha_sc)) && rw_shift_register[DATA_WIDTH-1]) begin  
          shift_out <= shiftout_register[DATA_WIDTH-1];
          shiftout_register <= {shiftout_register[DATA_WIDTH-2:0],1'b0};
          shiftin_register <= {shiftin_register[DATA_WIDTH-2:0],1'b0};
        end 

      end else if (spi_state == READ) begin
        if (bitcounter_sc == 0) begin
          spi_state <= DONE;
        end else begin
          spi_state <= READ;
        end

        if ((spi_clk && ~spi_cpha_sc) || (~spi_clk && spi_cpha_sc)) begin
          read_bitcounter_sc <= read_bitcounter_sc + 1;
          shiftin_register <= {shiftin_register[DATA_WIDTH-2:0],1'b1};
          bitcounter_sc <= bitcounter_sc - 1;
          if (~rw_shift_register[DATA_WIDTH-1]) begin
            spi_dir <= rw_shift_register[DATA_WIDTH-1];
            rw_shift_register <= {rw_shift_register[DATA_WIDTH-2:0], 1'b0};
          end else begin
            spi_state <= WRITE;
          end
        end

      end else if (spi_state == DONE) begin
        if (spi_clk) begin
          shift_out <= 1'b0;
          spi_clock_hot <= 1'b0;
          spi_dir <= 1'b1;
          spi_cs_n <= 1'b1;
          if (read_bitcounter_sc == 0 || to_fabric_fifo_full) begin
            spi_state <= IDLE;
            to_fabric_fifo_wr_en <= 1'b0;
          end else begin
            spi_state <= FIFO_WRITE;
            to_fabric_fifo_wr_en <= 1'b1;
          end          
        end
      end else if (spi_state == FIFO_WRITE) begin
        if (spi_clk) begin
          spi_state <= IDLE;
          to_fabric_fifo_wr_en <= 1'b0;
        end
      end
    end
  end

  endmodule
