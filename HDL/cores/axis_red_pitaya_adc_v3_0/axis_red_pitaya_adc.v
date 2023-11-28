/* Note:
 
 this core is written specifically assuming that the output is complex valued data, and therefore
 has the zero padding off the imaginary component, and the switching logic of which channel should be 
 placed on the real component.
 
 Also, contrary to the RedPitaya and Pavel's code this one does the two's complement conversion correctly
 and it also does the negation after the bit extension. The negation is also present in Redpitaya's code,
 and they included it to compensate for an inverting opamp on the input side of the ADC.
 
 The correct implementation can only work when there is at least 1 bit extension, so this module will fail
 compilation when the input and output bits are the same.
 
 OpenMRI 2023
 */
`timescale 1 ns / 1 ps

module axis_red_pitaya_adc #
  (
   parameter integer ADC_DATA_WIDTH = 14,
   parameter integer AXIS_TDATA_WIDTH = 32
   )
   (
    // System signals
    input wire			       aclk,

    // ADC signals
    output wire			       adc_csn,
    input wire [ADC_DATA_WIDTH-1:0]    adc_dat_a,
    input wire [ADC_DATA_WIDTH-1:0]    adc_dat_b,

    // Control signals for the switch
    input wire [1:0]		       adc_channel_switch, 
    // Master side
    output wire			       m_axis_tvalid,
    output wire [AXIS_TDATA_WIDTH-1:0] m_axis_tdata
    );
   localparam			       PADDING_WIDTH = AXIS_TDATA_WIDTH/2 - ADC_DATA_WIDTH;
   
   reg [ADC_DATA_WIDTH-1:0]	       int_dat_a_reg;
   reg [ADC_DATA_WIDTH-1:0]	       int_dat_b_reg;
   reg [1:0]			       int_channel_switch;
   
   // make an initial block to prevent compiling with invalid parameters
   initial begin
      if (AXIS_TDATA_WIDTH/2 <= ADC_DATA_WIDTH) begin
	 $error("Assertion failed: this core does not support converting data without extending by at least one bit!");
      end
   end
   
   // implement a function for the switch
   function automatic [AXIS_TDATA_WIDTH-1:0] switch (input [1:0] code, input [ADC_DATA_WIDTH-1:0] data_a, input [ADC_DATA_WIDTH-1:0] data_b);
      // generate the 2's complement correctly and store in a local variable, to make the code below more readable
      reg [ADC_DATA_WIDTH-1:0]	    channel_a;
      reg [ADC_DATA_WIDTH-1:0]	    channel_b;
      reg			    sign_a, sign_b;

      begin
	 channel_a = {~data_a[ADC_DATA_WIDTH-1], data_a[ADC_DATA_WIDTH-2:0]};
	 channel_b = {~data_b[ADC_DATA_WIDTH-1], data_b[ADC_DATA_WIDTH-2:0]};
	 sign_a = ~data_a[ADC_DATA_WIDTH-1];
	 sign_b = ~data_b[ADC_DATA_WIDTH-1];
	 
	 case (code)
	   // IQ mode, which is what redpitaya initially did, not great when there is no IQ input signal, as there will be adc noise on the the quadrature channel, unless this is
	   // a general core, and the upper bits are ignored, or a switch would be placed after this core
	   2'b00 : switch = {-{{PADDING_WIDTH{sign_a}},channel_a},-{{PADDING_WIDTH{sign_b}},channel_b}};
	   // channel a on the real part of the signal, 0 imaginary
	   2'b01 : switch = {{AXIS_TDATA_WIDTH/2{1'b0}}, -{{PADDING_WIDTH{sign_a}},channel_a}};
	   // channel b on the real part of the signal, 0 imaginary
	   2'b10 : switch = {{AXIS_TDATA_WIDTH/2{1'b0}}, -{{PADDING_WIDTH{sign_b}},channel_b}};
	   // future loopback mode
	   2'b11 : switch = {AXIS_TDATA_WIDTH{1'b0}};
	 endcase // case (code)
      end
   endfunction // switch

   // sample the input on the ADC clk rising edge
   always @(posedge aclk)
     begin
	int_dat_a_reg <= adc_dat_a;
	int_dat_b_reg <= adc_dat_b;
	int_channel_switch <= adc_channel_switch;
     end

   // this is really poor-mans handling of axi stream
   assign adc_csn = 1'b1;
   assign m_axis_tvalid = 1'b1;
   assign m_axis_tdata = switch(int_channel_switch, int_dat_a_reg, int_dat_b_reg);
   
endmodule
