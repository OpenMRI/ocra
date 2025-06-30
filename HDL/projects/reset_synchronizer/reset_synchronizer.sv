// A reset synchronizer synchronizes the deassertion of reset with respect to the clock domain. 
// In other words, a reset synchronizer manipulates the asynchronous reset to have synchronous deassertion.

module reset_synchronizer (
    input wire reset_n,
    input wire clk,
    output reg sync_reset_n
);
    reg Q1;
    always @ (posedge clk or negedge reset_n) begin
        if(~reset_n) begin
            Q1 <= 1'b0;
            sync_reset_n <= 1'b0;
        end else begin
            Q1 <= 1'b1;
            sync_reset_n <= Q1;
        end
    end
endmodule
