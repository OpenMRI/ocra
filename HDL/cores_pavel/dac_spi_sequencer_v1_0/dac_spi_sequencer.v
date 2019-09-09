
`timescale 1 ns / 1 ps

// This module will first be used for 3 AD5780s
// the maximum SPI clock speed on this DAC is 35 MHz
// the DAC has two update modes
//
// Synchronous DAC Update:
//   In this mode, LDACn is held low while data is being clocked into the input shift register.
//   The DAC output is updated on the rising edge of SYNCn
//
// Asynchronous DAC Update:
//   In this mode, LDACn is held high while data is being clocked into the input shift register (SYNCn low)
//   The DAC output is asynchronously updated by taking LDACn low after SYNCn has been taken high.
//   The update now occurs on the falling edge of LDACn
//
// The serial interface works with both a continuous and noncontinous serial clock. A continuous SCLK
// source can be used *only if* SYNCn is held low for the correct number of clock cycles.
//
// In gated clock mode, a burst clock containing the exact number of clock cycles must be used, and SYNCn
// must be taken high after the final clock to latch the data. The first falling clock edge if SYNCn starts
// the write cycle. Exactly 24 falling clock edges must be appled to SCLK before SYNCn is brought high again,
// If SYNCn is brought high before the 24th falling edge, the data written is invalid. If more than 24 falling
// SCLK edges are applied before SYNCn is brought high, the input data is also invalid.
//
// The input shift register is updated on the rising edge of SYNCn. For another serial transfer to take place,
// SYNCn must be brought low again. After the end of the serial data transfer, data is automatically transferred
// from the the input shift register to the addressed register. When the write cycle is complete, the output
// can be updated by taking LDACn low while SYNCn is high.
//
module dac_spi_sequencer #
(
  parameter integer BRAM_DATA_WIDTH = 32,
  parameter integer BRAM_ADDR_WIDTH = 10,
  parameter         CONTINUOUS = "FALSE"
)
(
  // System signals
  input wire 			    aclk,
  input wire 			    aresetn,

  input wire [BRAM_ADDR_WIDTH-1:0]  cfg_data,
  output wire [BRAM_ADDR_WIDTH-1:0] sts_data,
  input wire [BRAM_ADDR_WIDTH-1:0]  current_offset,
 		     
  // X BRAM port
  output wire 			    bram_portx_clk,
  output wire 			    bram_portx_rst,
  output wire [BRAM_ADDR_WIDTH-1:0] bram_portx_addr,
  input wire [BRAM_DATA_WIDTH-1:0]  bram_portx_rddata,

  // Y BRAM port
  output wire 			    bram_porty_clk,
  output wire 			    bram_porty_rst,
  output wire [BRAM_ADDR_WIDTH-1:0] bram_porty_addr,
  input wire [BRAM_DATA_WIDTH-1:0]  bram_porty_rddata,

  // Z BRAM port
  output wire 			    bram_portz_clk,
  output wire 			    bram_portz_rst,
  output wire [BRAM_ADDR_WIDTH-1:0] bram_portz_addr,
  input wire [BRAM_DATA_WIDTH-1:0]  bram_portz_rddata,

  // SPI signals for the three DAC ICs
  output wire 			    spi_clk,
  output wire 			    spi_sdox,
  output wire 			    spi_sdoy,
  output wire 			    spi_sdoz,
  output wire 			    spi_ldacn,
  output wire 			    spi_clrn,
  output wire 			    spi_syncn 			    
);

   reg [BRAM_ADDR_WIDTH-1:0] 	    int_addr_reg, int_addr_next;
   reg [BRAM_ADDR_WIDTH-1:0] 	    int_data_reg;
   reg [BRAM_ADDR_WIDTH-1:0] 	    bram_addr_reg;
   
   reg 				    int_enbl_reg, int_enbl_next;
   reg 				    int_conf_reg, int_conf_next;

   wire [BRAM_ADDR_WIDTH-1:0] 	    sum_cntr_wire;
   wire 			    int_comp_wire, int_tlast_wire;
   
   reg				    serial_clock_reg;
   reg [3:0] 			    serial_clock_counter;

   wire 			    gradient_update_clock;
   reg [39:0] 			    gradient_update_clock_counter;

   reg [23:0] 			    test_data;

   reg                              enable_transfer;
   reg 				    syncn_reg;
   reg 				    ldacn_reg; 				    
   reg                              serial_clock_enable_reg;
   reg [6:0] 			    serial_fe_counter;
   reg [2:0] 			    ldac_counter_reg;
   wire                             m_axis_tready;
   wire 			    m_axis_config_tready;

   reg [3:0] 			    post_ldac_count;
   
   reg 				    spi_clock_enable_reg;
   reg [2:0] 			    spi_sequencer_state_reg;
   reg [7:0] 			    spi_transfer_counter_reg;
   reg [23:0] 			    spi_data_regx;
   reg [23:0] 			    spi_data_regy;
   reg [23:0] 			    spi_data_regz;
   reg 				    spi_transfer_out_regx;
   reg 				    spi_transfer_out_regy;
   reg 				    spi_transfer_out_regz;
   
   reg                              spi_first_cmd_reg;
   reg 				    spi_second_cmd_reg;
	
   reg [15:0] 			    gradient_sample_count_reg;
			    
   assign m_axis_tready = 1'b0;
   assign m_axis_config_tready = 1'b0;
  
   // assign the outputs
   assign spi_clrn = 1'b1;              // don't clear ever

   // multiplex the spi_clk output, this could be done simpler
   assign spi_clk = serial_clock_reg & spi_clock_enable_reg;
   
   assign spi_syncn = syncn_reg;      
   assign spi_ldacn = ldacn_reg;
   assign spi_sdox = spi_transfer_out_regx;
   assign spi_sdoy = spi_transfer_out_regy;
   assign spi_sdoz = spi_transfer_out_regz;
   
   // generate the gradient update clock, which should also be done by a different core at some point
   // For a 143 MHz FPGA clock, we would divide by 1430 to get a 100 kHz clock
   
   assign gradient_update_clock = (gradient_update_clock_counter == 16'd1430);

  // after every gradient update clock:
  // - signal LDAC, except for the first sample
  // - load the next value from the three BRAM ports and send out with SPI clock
   always @(posedge aclk)
     begin
	if(~aresetn)
	  begin
	     // when we trigger this block, sync should go to zero
	     serial_clock_enable_reg <= 1'b1;
	     spi_clock_enable_reg <= 1'b0;
	     syncn_reg <= 1'b1;
	     ldacn_reg <= 1'b1;
	     spi_sequencer_state_reg <= 3'd0;
	     spi_transfer_counter_reg <= 8'd0;
	     gradient_update_clock_counter <= 40'd0;
	     serial_clock_counter <= 4'd0;
	     serial_clock_reg <= 1'b0;
	     serial_fe_counter <= 6'd0;
	     post_ldac_count <= 3'd0;

	     spi_data_regx <= 24'd0;
	     spi_data_regy <= 24'd0;
	     spi_data_regz <= 24'd0;
	     
	     spi_transfer_out_regx <= 1'b0;
	     spi_transfer_out_regy <= 1'b0;
	     spi_transfer_out_regz <= 1'b0;
	     
	     spi_first_cmd_reg <= 1'b1;
	     spi_second_cmd_reg <= 1'b0;
	     bram_addr_reg <= 16'd0;
	     gradient_sample_count_reg <= 16'd0;
	  end
	else
	  begin
	     case(spi_sequencer_state_reg)
	       3'd0:
		 begin
		    spi_sequencer_state_reg <= 3'd1;
		    if(gradient_sample_count_reg == 16'd199)
		      begin
			 // after 200 samples wrap around
			 gradient_sample_count_reg <= 16'd0;
			 bram_addr_reg <= 16'd0;
		      end
		    else
		      begin
			 bram_addr_reg <= bram_addr_reg;
		      end
		    syncn_reg <= 1'b1;
		    ldacn_reg <= 1'b1;
		 end
	       3'd1:
		 begin
		    // For 18 bit go with
		    // spi_data_reg <= {4'b0001,spi_data_val[17:0],2'b00};
		    
		    //spi_data_reg <= {4'b0001,spi_data_val[15:0],4'b0000};
		    spi_data_regx <= bram_portx_rddata[23:0];
		    spi_data_regy <= bram_porty_rddata[23:0];
		    spi_data_regz <= bram_portz_rddata[23:0];
		    
		    bram_addr_reg <= bram_addr_reg + 1;
		    gradient_sample_count_reg <= gradient_sample_count_reg + 1;
		    
		    spi_sequencer_state_reg <= 3'd2;
		    spi_first_cmd_reg <= 1'b0;
		    syncn_reg <= 1'b1;
		    ldacn_reg <= 1'b1;
		    serial_clock_counter <= 4'd0;
		    serial_clock_enable_reg <= 1'b0;
		    serial_fe_counter <= 6'd0;
		    spi_transfer_counter_reg <= 8'd0;
		 end
	       3'd2:
		 begin
		    if(spi_transfer_counter_reg == 8'd192)
		      begin
			 spi_sequencer_state_reg <= 3'd3;
			 spi_transfer_counter_reg <= 8'd0;
			 serial_clock_enable_reg <= 1'b0;
			 spi_clock_enable_reg <= 1'b0;
			 syncn_reg <= 1'b1;
			 // stop the clock generation
			 serial_clock_counter <= 4'd0;
			 // this seems silly, but it is to make sure that we don't
			 // have a falling edge before sync goes high
			 serial_clock_reg <= 1'b1;
		      end
		    else
		      begin
			 syncn_reg <= 1'b0;

			 // this is some pretty crappy way of preventing the
			 // clock from cycling again. This is shit, combined
			 // with the other 192 cycle counter
			 if(serial_fe_counter >= 6'd24)
			   begin
			      spi_clock_enable_reg <= 1'b0;
			   end
			 else
			   begin
			      spi_clock_enable_reg <= 1'b1;
			   end
			 serial_clock_enable_reg <= 1'b1;

			 spi_sequencer_state_reg <= 3'd2;
		      
			 // serial clock generation in this state
			 if(serial_clock_counter == 4'd3)
			   begin
			      serial_clock_counter <= 4'd0;
			      serial_clock_reg <= ~serial_clock_reg;
			      // update on a rising clock only
			      if(serial_clock_reg == 0)
				begin
				   spi_transfer_out_regx <= spi_data_regx[23];
				   spi_data_regx <= {spi_data_regx[22:0],1'b0};
				   spi_transfer_out_regy <= spi_data_regy[23];
				   spi_data_regy <= {spi_data_regy[22:0],1'b0};
				   spi_transfer_out_regz <= spi_data_regz[23];
				   spi_data_regz <= {spi_data_regz[22:0],1'b0};
				end
			      else
				begin
				   //count the falling edges
				   serial_fe_counter <= serial_fe_counter+1;
				end

			      // count the transfer clock cycles (stupid idea)
			      spi_transfer_counter_reg <= spi_transfer_counter_reg + 1;
			   end
			 else
			   if(serial_clock_enable_reg == 1'b0)
			     begin
				// if the clock was just enabled, start counting at zero
				serial_clock_counter <= 4'd0;
				serial_clock_reg <= 1'b1;
				// also push out the first data bit
				spi_transfer_out_regx <= spi_data_regx[23];
				spi_data_regx <= {spi_data_regx[22:0],1'b0};
				spi_transfer_out_regy <= spi_data_regy[23];
				spi_data_regy <= {spi_data_regy[22:0],1'b0};
				spi_transfer_out_regz <= spi_data_regz[23];
				spi_data_regz <= {spi_data_regz[22:0],1'b0};
				
				spi_transfer_counter_reg <= 1'b0;
			     end
			   else
			     begin
				serial_clock_counter <= serial_clock_counter+1;
				spi_transfer_counter_reg <= spi_transfer_counter_reg + 1;
			     end
		      end // else: !if(spi_transfer_counter_reg == 8'd192)
		    ldacn_reg <= 1'b1;
		 end // case: 3'd2
	       3'd3:
		 begin
		    // clear the output
		    spi_transfer_out_regx <= 0;
		    spi_transfer_out_regy <= 0;
		    spi_transfer_out_regz <= 0;
		    // deal with the wait for ldac      
		    //if(gradient_update_clock_counter == 40'd3571428) //16'd1430)
		    if(gradient_update_clock_counter == 16'd1430)
		       begin
			 ldacn_reg <= 1'b0;
			 spi_sequencer_state_reg <= 3'd4;
		      end
		    else
		      begin
			 ldacn_reg <= 1'b1;
			 spi_sequencer_state_reg <= 3'd3;
		      end
		    syncn_reg <= 1'b1;
		    spi_transfer_counter_reg <= 8'd0;
		    serial_clock_enable_reg <= 1'b0;
		    serial_clock_counter <= 4'd0;
		    serial_clock_reg <= 1'b0;
		 end // case: 3'd3
	      
	       3'd4:
		 begin
		    if(post_ldac_count == 3'd2)
		      begin
			 post_ldac_count <= 3'd0;
			 // make ldac the proper length
			 ldacn_reg <= 1'b1;
			 spi_sequencer_state_reg <= 3'd0;
			 spi_transfer_counter_reg <= 8'd0;
			 serial_clock_enable_reg <= 1'b0;
			 serial_clock_counter <= 4'd0;
			 serial_clock_reg <= 1'b0;
		      end // if (post_ldac_count == 3'd4)
		    else
		      begin
			 post_ldac_count <= post_ldac_count + 1;
			 spi_sequencer_state_reg <= 3'd4;
		      end // else: !if(post_ldac_count == 3'd2)
		    syncn_reg <= 1'b1;
		    spi_transfer_counter_reg <= 8'd0;
		 end // case: 3'd4
	       3'd5:
		 begin
		    spi_sequencer_state_reg <= 3'd5;
		 end
	     endcase // case (spi_sequencer_state_reg)

	     // gradient update clock
	     //if(gradient_update_clock_counter == 16'd1430)
	     //if(gradient_update_clock_counter == 40'd285714286)
	      if(gradient_update_clock_counter == 16'd1430) // 40 per second
		begin
		  gradient_update_clock_counter <= 40'd0;
	       end
	     else
	       begin
		  gradient_update_clock_counter <= gradient_update_clock_counter+1;
	       end // else: !if(gradient_update_clock_counter == 16'd1430)
	  end
	
     end // always @ (posedge aclk)
   
   assign sts_data = int_addr_reg;
   
   assign bram_portx_clk = aclk;
   assign bram_portx_rst = ~aresetn;
   assign bram_portx_addr = bram_addr_reg;

   assign bram_porty_clk = aclk;
   assign bram_porty_rst = ~aresetn;
   assign bram_porty_addr = bram_addr_reg;

   assign bram_portz_clk = aclk;
   assign bram_portz_rst = ~aresetn;
   assign bram_portz_addr = bram_addr_reg;
endmodule
