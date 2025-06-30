`timescale 1ns/1ps
module async_fifo #(
    parameter DATA_WIDTH = 16,
    parameter ADDR_WIDTH = 4,  // FIFO depth = 2^ADDR_WIDTH
    parameter ALMOST_FULL_THRESHOLD = 2, // Adjust as needed
    parameter ALMOST_EMPTY_THRESHOLD = 2 // Adjust as needed
)(
    input  wire                   wr_clk,
    input  wire                   wr_rst_n,
    input  wire [DATA_WIDTH-1:0]  wr_data,
    input  wire                   wr_en,
    output wire                   full,
    output wire                   almost_full,

    input  wire                   rd_clk,
    input  wire                   rd_rst_n,
    output wire [DATA_WIDTH-1:0]  rd_data,
    output wire                   rd_valid,
    input  wire                   rd_en,
    output wire                   empty,
    output wire                   almost_empty
);

    // Function to convert binary to Gray code
    function [ADDR_WIDTH:0] binary_to_gray(input [ADDR_WIDTH:0] bin);
        binary_to_gray = (bin >> 1) ^ bin;
    endfunction

    // Function to convert Gray code to binary
    function [ADDR_WIDTH:0] gray_to_binary(input [ADDR_WIDTH:0] gray);
        integer i;
        begin
            gray_to_binary[ADDR_WIDTH] = gray[ADDR_WIDTH];
            for (i = ADDR_WIDTH-1; i >= 0; i = i - 1)
                gray_to_binary[i] = gray[i] ^ gray_to_binary[i+1];
        end
    endfunction

    // FIFO memory - hint for BRAM inference
    (* ram_style = "block" *) reg [DATA_WIDTH-1:0] mem [0:(1<<ADDR_WIDTH)-1];

    // Write and read pointers
    reg [ADDR_WIDTH:0] wr_ptr_bin;
    reg [ADDR_WIDTH:0] wr_ptr_gray;

    reg [ADDR_WIDTH:0] rd_ptr_bin;
    reg [ADDR_WIDTH:0] rd_ptr_gray;

    // Write logic
    always @(posedge wr_clk) begin
        if (~wr_rst_n) begin
            wr_ptr_bin <= 0;
            wr_ptr_gray <= 0;
        end else if (wr_en && ~full) begin
            mem[wr_ptr_bin[ADDR_WIDTH-1:0]] <= wr_data;
            wr_ptr_bin <= wr_ptr_bin + 1;
            wr_ptr_gray <= binary_to_gray(wr_ptr_bin + 1);
        end
    end

    // Read pointer update
    always @(posedge rd_clk) begin
        if (~rd_rst_n) begin
            rd_ptr_bin <= 0;
            rd_ptr_gray <= 0;
        end else if (rd_en && ~empty) begin
            rd_ptr_bin <= rd_ptr_bin + 1;
            rd_ptr_gray <= binary_to_gray(rd_ptr_bin + 1);
        end
    end

    // Registered read data and valid flag
    reg [DATA_WIDTH-1:0] rd_data_reg;
    reg                  rd_valid_reg;

    always @(posedge rd_clk) begin
        if (!rd_rst_n) begin
            rd_data_reg  <= 0;
            rd_valid_reg <= 1'b0;
        end else begin
            if (rd_en && !empty) begin
                rd_data_reg  <= mem[rd_ptr_bin[ADDR_WIDTH-1:0]];
                rd_valid_reg <= 1'b1;
            end else begin
                rd_valid_reg <= 1'b0;
            end
        end
    end

    assign rd_data  = rd_data_reg;
    assign rd_valid = rd_valid_reg;

    // Pointer synchronization
    (* ASYNC_REG = "TRUE" *) reg [ADDR_WIDTH:0] wr_ptr_gray_rd_clk_sync1;
    (* ASYNC_REG = "TRUE" *) reg [ADDR_WIDTH:0] wr_ptr_gray_rd_clk_sync2;

    always @(posedge rd_clk) begin
        if (~rd_rst_n) begin
            wr_ptr_gray_rd_clk_sync1 <= 0;
            wr_ptr_gray_rd_clk_sync2 <= 0;
        end else begin
            wr_ptr_gray_rd_clk_sync1 <= wr_ptr_gray;
            wr_ptr_gray_rd_clk_sync2 <= wr_ptr_gray_rd_clk_sync1;
        end
    end
    wire [ADDR_WIDTH:0] wr_ptr_bin_rd_clk = gray_to_binary(wr_ptr_gray_rd_clk_sync2);

    (* ASYNC_REG = "TRUE" *) reg [ADDR_WIDTH:0] rd_ptr_gray_wr_clk_sync1;
    (* ASYNC_REG = "TRUE" *) reg [ADDR_WIDTH:0] rd_ptr_gray_wr_clk_sync2;

    always @(posedge wr_clk) begin
        if (~wr_rst_n) begin
            rd_ptr_gray_wr_clk_sync1 <= 0;
            rd_ptr_gray_wr_clk_sync2 <= 0;
        end else begin
            rd_ptr_gray_wr_clk_sync1 <= rd_ptr_gray;
            rd_ptr_gray_wr_clk_sync2 <= rd_ptr_gray_wr_clk_sync1;
        end
    end
    wire [ADDR_WIDTH:0] rd_ptr_bin_wr_clk = gray_to_binary(rd_ptr_gray_wr_clk_sync2);

    // Flags
    assign full = ( (wr_ptr_bin[ADDR_WIDTH] != rd_ptr_bin_wr_clk[ADDR_WIDTH]) &&
                    (wr_ptr_bin[ADDR_WIDTH-1:0] == rd_ptr_bin_wr_clk[ADDR_WIDTH-1:0]) );

    assign empty = (rd_ptr_bin == wr_ptr_bin_rd_clk);

    wire [ADDR_WIDTH:0] fifo_count_wr_clk = wr_ptr_bin - rd_ptr_bin_wr_clk;
    assign almost_full = (fifo_count_wr_clk >= ((1 << ADDR_WIDTH) - ALMOST_FULL_THRESHOLD));

    wire [ADDR_WIDTH:0] fifo_count_rd_clk = wr_ptr_bin_rd_clk - rd_ptr_bin;
    assign almost_empty = (fifo_count_rd_clk <= ALMOST_EMPTY_THRESHOLD);

endmodule
