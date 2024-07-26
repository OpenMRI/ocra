`timescale 1ns/100ps
module testbench_top;

parameter PERIOD = 8;

logic aclk;
logic aresetn;

wire n_cs;
wire sclk;
wire sdio;
int i;
reg [15:0] data_sampled;

wire [15:0] data_exp[4:1];
assign data_exp[1] = 16'h0100;
assign data_exp[2] = 16'h0201;
assign data_exp[3] = 16'h0302;
assign data_exp[4] = 16'h0400;

always @(posedge sclk) begin
    data_sampled <= {data_sampled[14:0], sdio};
end
always @(posedge n_cs) begin
    if (i != 0) begin
        $display("Data Transferred: %x", data_sampled);
        assert(data_sampled == data_exp[i]) else $error();
    end
    i++;
end

red_pitaya_adc_spi dut(
.*
);

//Reset State - Initialization
initial begin
	aclk = 0;
	aresetn = 0;
    i = 0;
end

initial begin
  @(posedge aclk);
  repeat (10) @(negedge aclk);
  aresetn = 1;

  repeat (4*(8*16+10+128)) @(negedge aclk);
  $finish();
end

initial begin
forever 
   #(PERIOD/2.0) aclk = !aclk;
end

endmodule
