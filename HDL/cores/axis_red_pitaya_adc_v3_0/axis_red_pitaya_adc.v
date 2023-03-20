
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

  always @(posedge aclk)
  begin
    int_dat_a_reg <= adc_dat_a;
    int_dat_b_reg <= adc_dat_b;
    int_channel_switch <= adc_channel_switch;
     
  end

  assign adc_csn = 1'b1;

  assign m_axis_tvalid = 1'b1;
 
  assign m_axis_tdata = (int_channel_switch == 2'b01) ? {{(SINGLE_PADDING_WIDTH+1){int_dat_a_reg[ADC_DATA_WIDTH-1]}}, ~int_dat_a_reg[ADC_DATA_WIDTH-2:0]} :
			(int_channel_switch == 2'b10) ? {{(SINGLE_PADDING_WIDTH+1){int_dat_b_reg[ADC_DATA_WIDTH-1]}}, ~int_dat_b_reg[ADC_DATA_WIDTH-2:0]} :
			                                {{(PADDING_WIDTH+1){int_dat_b_reg[ADC_DATA_WIDTH-1]}}, ~int_dat_b_reg[ADC_DATA_WIDTH-2:0],
                                                        {(PADDING_WIDTH+1){int_dat_a_reg[ADC_DATA_WIDTH-1]}}, ~int_dat_a_reg[ADC_DATA_WIDTH-2:0]};

endmodule
