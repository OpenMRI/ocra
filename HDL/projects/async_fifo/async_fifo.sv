module async_fifo_custom #(
    parameter DATA_WIDTH = 16,
    parameter ADDR_WIDTH = 4  // FIFO depth = 2^ADDR_WIDTH
)(
    input  wire                   wr_clk,
    input  wire                   wr_rst_n,
    input  wire [DATA_WIDTH-1:0]  wr_data,
    input  wire                   wr_en,
    output wire                   full,

    input  wire                   rd_clk,
    input  wire                   rd_rst_n,
    output wire [DATA_WIDTH-1:0]  rd_data,
    input  wire                   rd_en,
    output wire                   empty
);
    // FIFO memory
    reg [DATA_WIDTH-1:0] mem [0:(1<<ADDR_WIDTH)-1];

    // Write and read pointers
    reg [ADDR_WIDTH:0] wr_ptr;
    reg [ADDR_WIDTH:0] rd_ptr;

    // Pointer synchronization
    reg [ADDR_WIDTH:0] wr_ptr_rd_clk;
    reg [ADDR_WIDTH:0] rd_ptr_wr_clk;

    // Write logic
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (~wr_rst_n) begin
            wr_ptr <= 0;
        end else if (wr_en && ~full) begin
            mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
            wr_ptr <= wr_ptr + 1;
        end
    end

    // Read logic
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (~rd_rst_n) begin
            rd_ptr <= 0;
        end else if (rd_en && ~empty) begin
            rd_ptr <= rd_ptr + 1;
        end
    end

    assign rd_data = mem[rd_ptr[ADDR_WIDTH-1:0]];

    // Synchronize pointers across clock domains
    // Use double-flop synchronizers for wr_ptr in read clock domain
    reg [ADDR_WIDTH:0] wr_ptr_rd_clk_sync1, wr_ptr_rd_clk_sync2;
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (~rd_rst_n) begin
            wr_ptr_rd_clk_sync1 <= 0;
            wr_ptr_rd_clk_sync2 <= 0;
        end else begin
            wr_ptr_rd_clk_sync1 <= wr_ptr;
            wr_ptr_rd_clk_sync2 <= wr_ptr_rd_clk_sync1;
        end
    end
    assign wr_ptr_rd_clk = wr_ptr_rd_clk_sync2;

    // Use double-flop synchronizers for rd_ptr in write clock domain
    reg [ADDR_WIDTH:0] rd_ptr_wr_clk_sync1, rd_ptr_wr_clk_sync2;
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (~wr_rst_n) begin
            rd_ptr_wr_clk_sync1 <= 0;
            rd_ptr_wr_clk_sync2 <= 0;
        end else begin
            rd_ptr_wr_clk_sync1 <= rd_ptr;
            rd_ptr_wr_clk_sync2 <= rd_ptr_wr_clk_sync1;
        end
    end
    assign rd_ptr_wr_clk = rd_ptr_wr_clk_sync2;

    // Generate full and empty flags
    assign full  = (wr_ptr[ADDR_WIDTH] != rd_ptr_wr_clk[ADDR_WIDTH]) &&
                   (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr_wr_clk[ADDR_WIDTH-1:0]);
    assign empty = (wr_ptr_rd_clk == rd_ptr);

endmodule
