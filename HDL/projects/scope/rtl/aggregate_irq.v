module aggregate_irq #(
    parameter WIDTH = 8
) (
    input               aresetn,
    input               soft_reset,
    input               aclk,
    input [WIDTH-1:0]   irq_i,
    output reg          irq_o,
    output reg [31:0]   irq_counter_o  //backup approach through polling
);

    reg  [WIDTH-1:0]    irq_q;
    wire [WIDTH-1:0]    irq_d;
    reg                 aggregate_irq_q;
    reg                 aggregate_irq_2q;
    wire                aggregate_irq_d;

    assign              irq_d = aggregate_irq_d ? {WIDTH{1'b0}} : irq_q;
    assign              aggregate_irq_d = &irq_q;

    always @(posedge aclk) begin
        if(!aresetn || soft_reset) begin
            irq_q <= 0;
            aggregate_irq_q <= 0;
            aggregate_irq_2q <= 0;
            irq_o <= 0;
            irq_counter_o <= 0;
        end else begin
            irq_q <= irq_i | irq_d;
            aggregate_irq_q <= aggregate_irq_d;
            aggregate_irq_2q <= aggregate_irq_q;
            irq_o <= aggregate_irq_q || aggregate_irq_2q;
            irq_counter_o <= !aggregate_irq_2q && aggregate_irq_q ? irq_counter_o + 1 : irq_counter_o;
        end
    end
    

endmodule

