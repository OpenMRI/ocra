
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
module axi_four_ltc2656_spi #
(
 parameter integer C_S_AXI_DATA_WIDTH = 32,
 parameter integer C_S_AXI_ADDR_WIDTH = 16,
 parameter integer BRAM_DATA_WIDTH = 32,
 parameter integer BRAM_ADDR_WIDTH = 16,
 parameter CONTINUOUS = "FALSE"
)
(
  // System signals
  input wire 				    aclk,
  input wire 				    aresetn,

  input wire [BRAM_ADDR_WIDTH-1:0] 	    cfg_data,
  output wire [BRAM_ADDR_WIDTH-1:0] 	    sts_data,
  input wire [BRAM_ADDR_WIDTH-1:0] 	    current_offset,
 		     
  // X BRAM port
  output wire 				    bram_port0_clk,
  output wire 				    bram_port0_rst,
  output wire [BRAM_ADDR_WIDTH-1:0] 	    bram_port0_addr,
  input wire [BRAM_DATA_WIDTH-1:0] 	    bram_port0_rddata,
 
  // SPI signals for the three DAC ICs
  output wire 				    spi_clk,
  output wire 				    spi_bank0,
  output wire 				    spi_bank1,
  output wire 				    spi_bank2,
  output wire 				    spi_bank3,
  output wire 				    spi_ldacn,
  output wire 				    spi_clrn,
  output wire 				    spi_cs, 

 // Do not modify the ports beyond this line
 
 // Global Clock Signal
  input wire 				    S_AXI_ACLK,
 // Global Reset Signal. This Signal is Active LOW
  input wire 				    S_AXI_ARESETN,
 // Write address (issued by master, acceped by Slave)
  input wire [C_S_AXI_ADDR_WIDTH-1 : 0]     S_AXI_AWADDR,
 // Write channel Protection type. This signal indicates the
 // privilege and security level of the transaction, and whether
 // the transaction is a data access or an instruction access.
  input wire [2 : 0] 			    S_AXI_AWPROT,
 // Write address valid. This signal indicates that the master signaling
 // valid write address and control information.
  input wire 				    S_AXI_AWVALID,
 // Write address ready. This signal indicates that the slave is ready
 // to accept an address and associated control signals.
  output wire 				    S_AXI_AWREADY,
 // Write data (issued by master, acceped by Slave) 
  input wire [C_S_AXI_DATA_WIDTH-1 : 0]     S_AXI_WDATA,
 // Write strobes. This signal indicates which byte lanes hold
 // valid data. There is one write strobe bit for each eight
 // bits of the write data bus.    
  input wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0] S_AXI_WSTRB,
 // Write valid. This signal indicates that valid write
 // data and strobes are available.
  input wire 				    S_AXI_WVALID,
 // Write ready. This signal indicates that the slave
 // can accept the write data.
  output wire 				    S_AXI_WREADY,
 // Write response. This signal indicates the status
 // of the write transaction.
  output wire [1 : 0] 			    S_AXI_BRESP,
 // Write response valid. This signal indicates that the channel
 // is signaling a valid write response.
  output wire 				    S_AXI_BVALID,
 // Response ready. This signal indicates that the master
 // can accept a write response.
  input wire 				    S_AXI_BREADY,
 // Read address (issued by master, acceped by Slave)
  input wire [C_S_AXI_ADDR_WIDTH-1 : 0]     S_AXI_ARADDR,
 // Protection type. This signal indicates the privilege
 // and security level of the transaction, and whether the
 // transaction is a data access or an instruction access.
  input wire [2 : 0] 			    S_AXI_ARPROT,
 // Read address valid. This signal indicates that the channel
 // is signaling valid read address and control information.
  input wire 				    S_AXI_ARVALID,
 // Read address ready. This signal indicates that the slave is
 // ready to accept an address and associated control signals.
  output wire 				    S_AXI_ARREADY,
    // Read data (issued by slave)
  output wire [C_S_AXI_DATA_WIDTH-1 : 0]    S_AXI_RDATA,
 // Read response. This signal indicates the status of the
 // read transfer.
  output wire [1 : 0] 			    S_AXI_RRESP,
 // Read valid. This signal indicates that the channel is
 // signaling the required read data.
  output wire 				    S_AXI_RVALID,
 // Read ready. This signal indicates that the master can
 // accept the read data and response information.
  input wire 				    S_AXI_RREADY
);
   reg [BRAM_ADDR_WIDTH-1:0] 	    bram_addr_reg;

   wire [BRAM_ADDR_WIDTH-1:0] 	    sum_cntr_wire;
   wire 			    int_comp_wire, int_tlast_wire;
   
   reg				    serial_clock_reg;
   reg [3:0] 			    serial_clock_counter;

   wire 			    gradient_update_clock;
   reg [39:0] 			    gradient_update_clock_counter;

   reg [3:0] 			    cmd_word_counter;
 			    
   reg [23:0] 			    test_data;

   reg                              enable_transfer;
   reg 				    syncn_reg;
   reg 				    ldacn_reg; 				    
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
   reg [23:0] 			    spi_data_regz2;
   reg 				    spi_transfer_out_regx;
   reg 				    spi_transfer_out_regy;
   reg 				    spi_transfer_out_regz;
   reg 				    spi_transfer_out_regz2;
   
   reg                              spi_first_cmd_reg;
   reg 				    spi_second_cmd_reg;
	
   reg [15:0] 			    gradient_sample_count_reg;

   // DECODER assignment, maybe move somehwere else
   //assign formatAa = bram_porta_rddata[36:32];      // register address for format A
   //assign formatBa = bram_porta_rddata[44:40];      // register address for format B
   //assign op = bram_porta_rddata[63:58];            // pcp0 opcode is ALWAYS top 6 bits
   //assign directAddress = bram_porta_rddata[31:0];  // format A direct address
   //assign delayConstanst = bram_porta_rddata[39:0]; // 40 bit constant for format B
   //    
   // AXI4LITE signals
   reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_awaddr;
   reg 				  axi_awready;
   reg 				  axi_wready;
   reg [1 : 0] 			  axi_bresp;
   reg 				  axi_bvalid;
   reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_araddr;
   reg 				  axi_arready;
   reg [C_S_AXI_DATA_WIDTH-1 : 0] axi_rdata;
   reg [1 : 0] 			  axi_rresp;
   reg 				  axi_rvalid;
   
   // Example-specific design signals
   // local parameter for addressing 32 bit / 64 bit C_S_AXI_DATA_WIDTH
   // ADDR_LSB is used for addressing 32/64 bit registers/memories
   // ADDR_LSB = 2 for 32 bits (n downto 2)
   // ADDR_LSB = 3 for 64 bits (n downto 3)
   localparam integer 		  ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1;
   localparam integer 		  OPT_MEM_ADDR_BITS = 3;
   //----------------------------------------------
   //-- Signals for user logic register space example
   //------------------------------------------------
   //-- Number of Slave Registers 4
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg0;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg1;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg2;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg3;
   // additional registers
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg4;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg5;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg6;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg7;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg8;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg9;
   reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg10;
   
   wire 			  slv_reg_rden;
   wire 			  slv_reg_wren;
   reg [C_S_AXI_DATA_WIDTH-1:0]   reg_data_out;
   integer 			  byte_index;
   
   // I/O Connections assignments
   
   assign S_AXI_AWREADY    = axi_awready;
   assign S_AXI_WREADY    = axi_wready;
   assign S_AXI_BRESP    = axi_bresp;
   assign S_AXI_BVALID    = axi_bvalid;
   assign S_AXI_ARREADY    = axi_arready;
   assign S_AXI_RDATA    = axi_rdata;
   assign S_AXI_RRESP    = axi_rresp;
   assign S_AXI_RVALID    = axi_rvalid;
   // Implement axi_awready generation
   // axi_awready is asserted for one S_AXI_ACLK clock cycle when both
   // S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_awready is
   // de-asserted when reset is low.
   
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_awready <= 1'b0;
	  end 
	else
	  begin    
	     if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID)
               begin
		  // slave is ready to accept write address when 
		  // there is a valid write address and write data
		  // on the write address and data bus. This design 
		  // expects no outstanding transactions. 
		  axi_awready <= 1'b1;
               end
	     else           
               begin
		  axi_awready <= 1'b0;
               end
	  end 
     end       
   
   // Implement axi_awaddr latching
   // This process is used to latch the address when both 
   // S_AXI_AWVALID and S_AXI_WVALID are valid. 
   
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_awaddr <= 0;
	  end 
	else
	  begin    
	     if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID)
               begin
		  // Write Address latching 
		  axi_awaddr <= S_AXI_AWADDR;
               end
	  end 
     end       
   
   // Implement axi_wready generation
   // axi_wready is asserted for one S_AXI_ACLK clock cycle when both
   // S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_wready is 
   // de-asserted when reset is low. 
   
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_wready <= 1'b0;
	  end 
	else
	  begin    
	     if (~axi_wready && S_AXI_WVALID && S_AXI_AWVALID)
               begin
		  // slave is ready to accept write data when 
		  // there is a valid write address and write data
		  // on the write address and data bus. This design 
		  // expects no outstanding transactions. 
		  axi_wready <= 1'b1;
               end
	     else
               begin
		  axi_wready <= 1'b0;
               end
	  end 
     end       
   
   // Implement memory mapped register select and write logic generation
   // The write data is accepted and written to memory mapped registers when
   // axi_awready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted. Write strobes are used to
   // select byte enables of slave registers while writing.
   // These registers are cleared when reset (active low) is applied.
   // Slave register write enable is asserted when valid address and data are available
   // and the slave is ready to accept the write address and write data.
   assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;
   
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     //slv_reg0 <= 8'h00;
	     //slv_reg1 <= 8'h10;
	     //slv_reg2 <= 8'h20;
	     //slv_reg3 <= 8'h30;
	     //slv_reg4 <= 8'h40;
	     //slv_reg5 <= 8'h50;
	     //slv_reg6 <= 8'h60;
	     //slv_reg7 <= 8'h70;
	     //slv_reg8 <= 8'h80;
	     //slv_reg9 <= 8'h90;
	     //slv_reg10 <= 8'h77;
	  end 
	else begin
	   if (slv_reg_wren)
	     begin
		case ( axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] )
		  2'h0:
		    for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
		      if ( S_AXI_WSTRB[byte_index] == 1 ) begin
			 // Respective byte enables are asserted as per write strobes 
			 // Slave register 0
			 slv_reg0[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
		      end  
		  2'h1:
		    for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
		      if ( S_AXI_WSTRB[byte_index] == 1 ) begin
			 // Respective byte enables are asserted as per write strobes 
			 // Slave register 1
			 //slv_reg1[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
		      end  
		  2'h2:
		    for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
		      if ( S_AXI_WSTRB[byte_index] == 1 ) begin
			 // Respective byte enables are asserted as per write strobes 
			 // Slave register 2
			 //slv_reg2[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
		      end  
		  2'h3:
		    for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
		      if ( S_AXI_WSTRB[byte_index] == 1 ) begin
			 // Respective byte enables are asserted as per write strobes 
			 // Slave register 3
			 //slv_reg3[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
		      end  
		  default : begin
                     //slv_reg0 <= slv_reg0;
                     //slv_reg1 <= slv_reg1;
                     //slv_reg2 <= slv_reg2;
                     //slv_reg3 <= slv_reg3;
                  end
		endcase
	     end
	end
     end    
   
   // Implement write response logic generation
   // The write response and response valid signals are asserted by the slave 
   // when axi_wready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted.  
   // This marks the acceptance of address and indicates the status of 
   // write transaction.
   
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_bvalid  <= 0;
	     axi_bresp   <= 2'b0;
	  end 
	else
	  begin    
	     if (axi_awready && S_AXI_AWVALID && ~axi_bvalid && axi_wready && S_AXI_WVALID)
               begin
		  // indicates a valid write response is available
		  axi_bvalid <= 1'b1;
		  axi_bresp  <= 2'b0; // 'OKAY' response 
               end                   // work error responses in future
	     else
               begin
		  if (S_AXI_BREADY && axi_bvalid) 
		    //check if bready is asserted while bvalid is high) 
		    //(there is a possibility that bready is always asserted high)   
		    begin
		       axi_bvalid <= 1'b0; 
		    end  
               end
	  end
     end   
   
   // Implement axi_arready generation
   // axi_arready is asserted for one S_AXI_ACLK clock cycle when
   // S_AXI_ARVALID is asserted. axi_awready is 
   // de-asserted when reset (active low) is asserted. 
   // The read address is also latched when S_AXI_ARVALID is 
   // asserted. axi_araddr is reset to zero on reset assertion.
   
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_arready <= 1'b0;
	     axi_araddr  <= 32'b0;
	  end 
	else
	  begin    
	     if (~axi_arready && S_AXI_ARVALID)
               begin
		  // indicates that the slave has acceped the valid read address
		  axi_arready <= 1'b1;
		  // Read address latching
		  axi_araddr  <= S_AXI_ARADDR;
               end
	     else
               begin
		  axi_arready <= 1'b0;
               end
	  end 
     end       
   
   // Implement axi_arvalid generation
   // axi_rvalid is asserted for one S_AXI_ACLK clock cycle when both 
   // S_AXI_ARVALID and axi_arready are asserted. The slave registers 
   // data are available on the axi_rdata bus at this instance. The 
   // assertion of axi_rvalid marks the validity of read data on the 
   // bus and axi_rresp indicates the status of read transaction.axi_rvalid 
   // is deasserted on reset (active low). axi_rresp and axi_rdata are 
   // cleared to zero on reset (active low).  
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_rvalid <= 0;
	     axi_rresp  <= 0;
	  end 
	else
	  begin    
	     if (axi_arready && S_AXI_ARVALID && ~axi_rvalid)
               begin
		  // Valid read data is available at the read data bus
		  axi_rvalid <= 1'b1;
		  axi_rresp  <= 2'b0; // 'OKAY' response
               end   
	     else if (axi_rvalid && S_AXI_RREADY)
               begin
		  // Read data is accepted by the master
		  axi_rvalid <= 1'b0;
               end                
	  end
     end    
   
   // Implement memory mapped register select and read logic generation
   // Slave register read enable is asserted when valid address is available
   // and the slave is ready to accept the read address.
   assign slv_reg_rden = axi_arready & S_AXI_ARVALID & ~axi_rvalid;
   always @(*)
     begin
	// Address decoding for reading registers
	case ( axi_araddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] )
          4'h0   : reg_data_out <= slv_reg0;
          4'h1   : reg_data_out <= slv_reg1;
          4'h2   : reg_data_out <= slv_reg2;
          4'h3   : reg_data_out <= slv_reg3;
	  4'h4   : reg_data_out <= slv_reg4;
          4'h5   : reg_data_out <= slv_reg5;
          4'h6   : reg_data_out <= slv_reg6;
          4'h7   : reg_data_out <= slv_reg7;
	  4'h8   : reg_data_out <= slv_reg8;
          4'h9   : reg_data_out <= slv_reg9;
          4'hA   : reg_data_out <= slv_reg10;
          default : reg_data_out <= 0;
	endcase
     end
   
   // Output register or memory read data
   always @( posedge S_AXI_ACLK )
     begin
	if ( S_AXI_ARESETN == 1'b0 )
	  begin
	     axi_rdata  <= 0;
	  end 
	else
	  begin    
	     // When there is a valid read address (S_AXI_ARVALID) with 
	     // acceptance of read address by the slave (axi_arready), 
	     // output the read dada 
	     if (slv_reg_rden)
               begin
		  axi_rdata <= reg_data_out;     // register read data
               end   
	  end
     end    
   
   // Add user logic here
   
   // assign the outputs
   assign spi_clrn = 1'b1;              // don't clear ever

   // multiplex the spi_clk output, this could be done simpler
   assign spi_clk = serial_clock_reg & spi_clock_enable_reg;
   
   assign spi_cs = syncn_reg;      
   assign spi_ldacn = ldacn_reg;
   assign spi_bank0 = spi_transfer_out_regx;
   assign spi_bank1 = spi_transfer_out_regy;
   assign spi_bank2 = spi_transfer_out_regz;
   assign spi_bank3 = spi_transfer_out_regz2;
   // generate the gradient update clock, which should also be done by a different core at some point
   // For a 143 MHz FPGA clock, we would divide by 1430 to get a 100 kHz clock
   
   assign gradient_update_clock = (gradient_update_clock_counter == 16'd1430);

   reg lclk_reg;
   reg [7:0] aclk_counter;

   wire      lclk;
   
   assign lclk = lclk_reg;
   
   always @(posedge aclk)
     begin
	if(~aresetn)
	  begin
	     lclk_reg <= 0;
	     aclk_counter <= 8'd0;
	  end
	else
	  begin
	     if(aclk_counter == 10)
	       begin
		  lclk_reg <= ~lclk_reg;
		  aclk_counter <= 0;
	       end
	     else
	       begin
		  aclk_counter <= aclk_counter + 8'd1;
	       end
	  end // else: !if(~aresetn)
     end // always @ (posedge aclk)
   
   // this block just deals with the SPI data transfer out (serializer)
   always @(posedge aclk)
     begin
	if(~aresetn)
	  begin
	     spi_data_regx <= 24'd0;
	     spi_transfer_out_regx <= 1'b0;
	  end
	else
	  begin
	     case(spi_sequencer_state_reg)
	       3'd1:
		 begin
		    spi_data_regx <= bram_port0_rddata[23:0];
		    // TW: 01/22/2020 clone the data
		    spi_data_regy <= bram_port0_rddata[23:0];
		    spi_data_regz <= bram_port0_rddata[23:0];
		    spi_data_regz2 <= bram_port0_rddata[23:0];
		    spi_transfer_out_regx <= 1'b0;
		 end // case: 3'd1
	       
	       3'd2:
		 begin
		    if(serial_clock_counter == 4'd0) // update before clock rises
		      begin
			 // update on a rising clock only
			 if(serial_clock_reg == 0)
			   begin
			      spi_transfer_out_regx <= spi_data_regx[23];
			      spi_data_regx <= {spi_data_regx[22:0],1'b0};
			      
			      spi_transfer_out_regy <= spi_data_regy[23];
                              spi_data_regy <= {spi_data_regy[22:0],1'b0};
			      
			      spi_transfer_out_regz <= spi_data_regz[23];
                              spi_data_regz <= {spi_data_regz[22:0],1'b0};
			      
			      spi_transfer_out_regz2 <= spi_data_regz2[23];
                              spi_data_regz2 <= {spi_data_regz2[22:0],1'b0};
			      
			   end
			 else
			   begin
			      spi_transfer_out_regx <= spi_transfer_out_regx;
			      spi_data_regx <= spi_data_regx;
			      spi_transfer_out_regy <= spi_transfer_out_regy;
			      spi_data_regy <= spi_data_regy;
			      spi_transfer_out_regz <= spi_transfer_out_regz;
			      spi_data_regz <= spi_data_regz;
			      spi_transfer_out_regz2 <= spi_transfer_out_regz2;
			      spi_data_regz2 <= spi_data_regz2;
			   end // else: !if(serial_clock_reg == 0)
		      end
		    else
		      begin
			 spi_transfer_out_regx <= spi_transfer_out_regx;
			 spi_data_regx <= spi_data_regx;
			 spi_transfer_out_regy <= spi_transfer_out_regy;
			 spi_data_regy <= spi_data_regy;
			 spi_transfer_out_regz <= spi_transfer_out_regz;
			 spi_data_regz <= spi_data_regz;
			 spi_transfer_out_regz2 <= spi_transfer_out_regz2;
			 spi_data_regz2 <= spi_data_regz2;
		      end // if (serial_clock_counter == 4'd1)
		 end
	       
	       default:
		 begin
		    spi_data_regx <= 24'd0;
		    spi_data_regy <= 24'd0;
		    spi_data_regz <= 24'd0;
		    spi_data_regz2 <= 24'd0;
		    
		    spi_transfer_out_regx <= 1'b0;
		    spi_transfer_out_regy <= 1'b0;
		    spi_transfer_out_regz <= 1'b0;
		    spi_transfer_out_regz2 <= 1'b0;
		 end
	     endcase
	  end // else: !if(~aresetn)
     end // always @ (posedge aclk)

   // this block deals with the memory addressing alone
   always @(posedge aclk)
     begin
	if(~aresetn)
	  begin
	     //bram_addr_reg <= {(BRAM_ADDR_WIDTH){1'b0}};
	     bram_addr_reg <= current_offset; // set the start offset
	  end
	else
	  begin
	     case(spi_sequencer_state_reg)
	        3'd0:
		  begin
		     if(gradient_sample_count_reg == 16'd7999)
		       begin
			  // after 200 samples wrap around
			  //bram_addr_reg <= {(BRAM_ADDR_WIDTH){1'b0}};
		       end
		     else
		       begin
			  bram_addr_reg <= bram_addr_reg;
		       end
		  end // case: 3'd0
	       3'd1:
		 begin		    
		    bram_addr_reg <= bram_addr_reg + 1;
		 end
	       default:
		 begin
		    bram_addr_reg <= bram_addr_reg;
		 end
	     endcase
	  end
     end // always @ (posedge aclk)
   
  // after every gradient update clock:
  // - signal LDAC, except for the first sample
  // - load the next value from the three BRAM ports and send out with SPI clock
   always @(posedge aclk)
     begin
	if(~aresetn)
	  begin
	     // when we trigger this block, sync should go to zero
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
	     
	     spi_first_cmd_reg <= 1'b1;
	     spi_second_cmd_reg <= 1'b0;
	     
	     gradient_sample_count_reg <= 16'd0;

	     cmd_word_counter <= 4'd0;
	     
	  end
	else
	  begin
	     case(spi_sequencer_state_reg)
	       3'd0:
		 begin
		    if(gradient_sample_count_reg == 16'd7999)
		      begin
			 // after 16000 samples stop
			 gradient_sample_count_reg <= 16'd0;
			 spi_sequencer_state_reg <= 3'd5;
		      end
		    else
		      begin
			 spi_sequencer_state_reg <= 3'd6;
		      end
		    syncn_reg <= 1'b1;
		    ldacn_reg <= 1'b1;
		    serial_clock_counter <= 4'd0;
		 end // case: 3'd0
	       3'd6:
		 begin
		    // wait for RAM
		    spi_sequencer_state_reg <= 3'd7;
		    serial_clock_counter <= 4'd0;
		 end
	       3'd7:
		 begin
		    // wait for RAM
		    spi_sequencer_state_reg <= 3'd1;
		    serial_clock_counter <= 4'd0;
		 end
	       3'd1:
		 begin		    
		    gradient_sample_count_reg <= gradient_sample_count_reg + 1;
		    // increase cmd_word_counter
		    cmd_word_counter <= cmd_word_counter + 1;
		    
		    spi_sequencer_state_reg <= 3'd2;
		    spi_first_cmd_reg <= 1'b0;
		    syncn_reg <= 1'b1;
		    ldacn_reg <= 1'b1;
		    serial_clock_reg <= 1'b0;
		    serial_clock_counter <= 4'd0; // start with clock low
		    serial_fe_counter <= 6'd0;
		    spi_transfer_counter_reg <= 8'd0;
		 end
	       3'd2:
		 begin
		    // Just like in the next comment block, counting the transfer counter and the serial_fe_counter
		    // separately is nothing but trouble, and should be removed asap.
		    if(spi_transfer_counter_reg == 8'd96)
		      begin
			 if(cmd_word_counter <= 4'd4)
			   begin
			      spi_sequencer_state_reg <= 3'd0;
			   end
			 else
			   begin
			      cmd_word_counter <= 4'd0;
			      spi_sequencer_state_reg <= 3'd3;
			   end
			 spi_transfer_counter_reg <= 8'd0;
			 spi_clock_enable_reg <= 1'b0;
			 syncn_reg <= 1'b1;
			 // stop the clock generation
			 serial_clock_counter <= 4'd0;
			 serial_clock_reg <= 1'b0;
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
			 
			 spi_sequencer_state_reg <= 3'd2;
		      
			 // serial clock generation in this state
			 if(serial_clock_counter == 4'd1)
			   begin
			      serial_clock_counter <= 4'd0;
			      serial_clock_reg <= ~serial_clock_reg;

			      if(serial_clock_reg == 1)
				begin
				   //count the falling edges
				   serial_fe_counter <= serial_fe_counter+1;
				end
			      
			      // count the transfer clock cycles (stupid idea)
			      spi_transfer_counter_reg <= spi_transfer_counter_reg + 1;
			   end
			 else
			   begin
			      serial_clock_counter <= serial_clock_counter + 1'b1;
			      spi_transfer_counter_reg <= spi_transfer_counter_reg + 1;
			   end
		      end // else: !if(spi_transfer_counter_reg == 8'd192)
		    ldacn_reg <= 1'b1;
		 end // case: 3'd2
	       3'd3:
		 begin
		    // deal with the wait for ldac      
		    if(gradient_update_clock_counter == 16'd715) //1430)
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
	      if(gradient_update_clock_counter == 16'd715) // 40 per second
		begin
		  gradient_update_clock_counter <= 40'd0;
	       end
	     else
	       begin
		  gradient_update_clock_counter <= gradient_update_clock_counter+1;
	       end // else: !if(gradient_update_clock_counter == 16'd1430)
	  end
	
     end // always @ (posedge aclk)
   
   //assign sts_data = int_addr_reg;
   
   assign bram_port0_clk = aclk;
   assign bram_port0_rst = ~aresetn;
   assign bram_port0_addr = bram_addr_reg;

   //assign bram_porty_clk = aclk;
   //assign bram_porty_rst = ~aresetn;
   //assign bram_porty_addr = bram_addr_reg;

   //assign bram_portz_clk = aclk;
   //assign bram_portz_rst = ~aresetn;
   //assign bram_portz_addr = bram_addr_reg;

   //assign bram_portz2_clk = aclk;
   //assign bram_portz2_rst = ~aresetn;
   //assign bram_portz2_addr = bram_addr_reg;
endmodule
