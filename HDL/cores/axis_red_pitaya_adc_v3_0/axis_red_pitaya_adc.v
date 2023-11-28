
`timescale 1 ns / 1 ps

module axis_red_pitaya_adc #
(
  parameter integer ADC_DATA_WIDTH = 14,
  parameter integer AXIS_TDATA_WIDTH = 32
)
(
  // System signals
  input wire 			     aclk,

  // ADC signals
  output wire 			     adc_csn,
  input wire [ADC_DATA_WIDTH-1:0]    adc_dat_a,
  input wire [ADC_DATA_WIDTH-1:0]    adc_dat_b,

  // Control signals for the switch
  input wire [1:0]                   adc_channel_switch,     
  // Master side
  output wire  			     m_axis_tvalid,
  output wire [AXIS_TDATA_WIDTH-1:0] m_axis_tdata
);
  localparam PADDING_WIDTH = AXIS_TDATA_WIDTH/2 - ADC_DATA_WIDTH;
  localparam SINGLE_PADDING_WIDTH = AXIS_TDATA_WIDTH - ADC_DATA_WIDTH;
   
  reg  [ADC_DATA_WIDTH-1:0] int_dat_a_reg;
  reg  [ADC_DATA_WIDTH-1:0] int_dat_b_reg;
  reg [1:0] 		    int_channel_switch;
  wire [ADC_DATA_WIDTH-1:0] channel_a;
  wire [ADC_DATA_WIDTH-1:0] channel_b;
   
  initial begin
     if (AXIS_TDATA_WIDTH/2 <= ADC_DATA_WIDTH) begin
	$error("Assertion failed: this core does not support converting data without extending by at least one bit!");
     end
  end
   
  always @(posedge aclk)
  begin
    int_dat_a_reg <= adc_dat_a;
    int_dat_b_reg <= adc_dat_b;
    int_channel_switch <= adc_channel_switch;
  end

  assign adc_csn = 1'b1;

  assign m_axis_tvalid = 1'b1;

  always @(*) begin
     // generate the 2's complement correctly
     assign channel_a = {~int_dat_a_reg[WIDTH-1], int_dat_a_reg[WIDTH-2:0]};
     assign channel_b = {~int_dat_b_reg[WIDTH-1], int_dat_b_reg[WIDTH-2:0]};

     // now construct the output
     case (int_channel_switch)
       2'b00:
	m_axis_tdata = {{AXIS_TDATA_WIDTH/2{1'b0}}, -{{PADDING_WIDTH{channel_a[WIDTH-1]}},channel_a}};
       2'b01:
	m_axis_tdata = {{AXIS_TDATA_WIDTH/2{1'b0}}, -{{PADDING_WIDTH{channel_b[WIDTH-1]}},channel_b}};
       2'b10:
	// IQ mode
	m_axis_tdata = {{AXIS_TDATA_WIDTH/2{1'b0}}, -{{PADDING_WIDTH{channel_a[WIDTH-1]}},channel_a},{AXIS_TDATA_WIDTH/2{1'b0}}, -{{PADDING_WIDTH{channel_b[WIDTH-1]}},channel_b}};
       2'b11:
	 // future loopback mode
	 m_axis_tdata = {AXIS_TDATA_WIDTH{1'b0}};
     endcase
  end

endmodule
