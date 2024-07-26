`timescale 1 ns / 100 ps

module validate_pattern #(
    parameter integer DATA_WIDTH = 14,
    parameter integer CNT_WIDTH = 17
) (
    // System signals
    input wire                         aclk,
    input wire                         resetn,
    input wire [DATA_WIDTH-1:0]        data,
    output wire                        valid
);
    //test pattern validation 
    logic [CNT_WIDTH-1:0]  cnt;
    logic [DATA_WIDTH-1:0] data_ex;
    logic vld;

    always_ff @(posedge aclk) begin
        if (!resetn || (data_ex != data)) begin
            cnt <= 0;
            data_ex <= 0;
            vld <= 0;
        end else begin
            vld <= &cnt;
            data_ex <= ~data_ex;
            cnt <= (cnt != '1)? cnt + 'd1 : cnt;
        end
    end
    assign valid = vld;

endmodule
