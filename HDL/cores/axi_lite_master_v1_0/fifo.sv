// synchronous fifo
// reads on empty and writes on full are ignored
module fifo #(
    parameter integer DEPTH = 16,
    parameter integer WIDTH = 32
) (
    input aclk,
    input resetn,
    input [WIDTH-1:0] wdata_i,
    input write_i,
    input read_i,
    output [WIDTH-1:0] rdata_o,
    output empty_o,
    output full_o
);

    localparam integer ADDR_WIDTH = $clog2(DEPTH);

    logic [WIDTH-1:0] mem [DEPTH-1:0];
    logic [WIDTH-1:0] rdata_q;
    logic [ADDR_WIDTH:0] wptr_q, wptr_d;
    logic [ADDR_WIDTH:0] rptr_q, rptr_d;

    logic empty_q, empty_d;
    logic full_q, full_d;

    assign empty_d = (wptr_d == rptr_d);
    assign full_d = wptr_d[ADDR_WIDTH-1:0] == rptr_d[ADDR_WIDTH-1:0] && (wptr_d[ADDR_WIDTH] ^ rptr_d[ADDR_WIDTH]);

    assign wptr_d = (write_i && !full_q) ? wptr_q + 1 : wptr_q;
    assign rptr_d = (read_i && !empty_q) ? rptr_q + 1 : rptr_q;

    // Write
    always_ff @(posedge aclk) begin
        if (write_i && !full_q)
            mem[wptr_q[ADDR_WIDTH-1:0]] <= wdata_i;
    end
    // Read - No prefetch stage. will add if needed
    always_ff @(posedge aclk) begin
        rdata_q <= mem[rptr_q[ADDR_WIDTH-1:0]];
    end
    // Ptr update
    always_ff @(posedge aclk) begin
        if (!resetn) begin
            wptr_q <= 0;
            rptr_q <= 0;
            empty_q <= 1;
            full_q <= 0;
        end else begin
            wptr_q <= wptr_d;
            rptr_q <= rptr_d;
            empty_q <= empty_d;
            full_q <= full_d;
        end
    end

    assign empty_o = empty_q;
    assign full_o = full_q;
    assign rdata_o = rdata_q;

endmodule