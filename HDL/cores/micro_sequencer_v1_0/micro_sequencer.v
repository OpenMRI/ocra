`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 12/28/2015 09:51:17 PM
// Design Name: 
// Module Name: top
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

// Make some declarations for 512KB memory for now
`define MEMSIZE 'h80000
`define MEMEMPTY 8'hFF
`define NULL 8'h00
`define IOADDR 'h80000 // IO mapping address

// Operand width
`define QUAD 2'b11 // 64 bits
`define LONG 2'b10 // 32 bits
`define WORD 2'b01 // 16 bits
`define BYTE 2'b00 // 8 bits
`define EXE 3'b000
`define RESET 3'b001
`define ABORT 3'b010
`define IRQ 3'b011
`define ERROR 3'b100

module micro_sequencer #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 16,
    parameter integer BRAM_DATA_WIDTH = 64,
    parameter integer BRAM_ADDR_WIDTH = 10
)
(

    // Users to add ports here
    
    //
    // BRAM interface, addr is set to 16 bit, data to 64 bit by parameters
    //
    output wire 			      bram_porta_clk,
    output wire 			      bram_porta_rst,
    output wire [BRAM_ADDR_WIDTH-1:0] 	      bram_porta_addr,
    input wire [BRAM_DATA_WIDTH-1:0] 	      bram_porta_rddata,
    
    // pcp specific stuff, needs some revision
    output reg [2:0] 			      tick,
    output reg [31:0] 			      pc, 
    output reg [15:0] 			      tx_offset,
    output reg [15:0] 			      grad_offset,
    output reg 				      m_en, 
    output reg [63:0] 			      pulse,
    input 				      cfg,
	
    // User ports ends
    // Do not modify the ports beyond this line

    // Global Clock Signal
    input wire 				      S_AXI_ACLK,
    // Global Reset Signal. This Signal is Active LOW
    input wire 				      S_AXI_ARESETN,
    // Write address (issued by master, acceped by Slave)
    input wire [C_S_AXI_ADDR_WIDTH-1 : 0]     S_AXI_AWADDR,
    // Write channel Protection type. This signal indicates the
        // privilege and security level of the transaction, and whether
        // the transaction is a data access or an instruction access.
    input wire [2 : 0] 			      S_AXI_AWPROT,
    // Write address valid. This signal indicates that the master signaling
        // valid write address and control information.
    input wire 				      S_AXI_AWVALID,
    // Write address ready. This signal indicates that the slave is ready
        // to accept an address and associated control signals.
    output wire 			      S_AXI_AWREADY,
    // Write data (issued by master, acceped by Slave) 
    input wire [C_S_AXI_DATA_WIDTH-1 : 0]     S_AXI_WDATA,
    // Write strobes. This signal indicates which byte lanes hold
        // valid data. There is one write strobe bit for each eight
        // bits of the write data bus.    
    input wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0] S_AXI_WSTRB,
    // Write valid. This signal indicates that valid write
        // data and strobes are available.
    input wire 				      S_AXI_WVALID,
    // Write ready. This signal indicates that the slave
        // can accept the write data.
    output wire 			      S_AXI_WREADY,
    // Write response. This signal indicates the status
        // of the write transaction.
    output wire [1 : 0] 		      S_AXI_BRESP,
    // Write response valid. This signal indicates that the channel
        // is signaling a valid write response.
    output wire 			      S_AXI_BVALID,
    // Response ready. This signal indicates that the master
        // can accept a write response.
    input wire 				      S_AXI_BREADY,
    // Read address (issued by master, acceped by Slave)
    input wire [C_S_AXI_ADDR_WIDTH-1 : 0]     S_AXI_ARADDR,
    // Protection type. This signal indicates the privilege
        // and security level of the transaction, and whether the
        // transaction is a data access or an instruction access.
    input wire [2 : 0] 			      S_AXI_ARPROT,
    // Read address valid. This signal indicates that the channel
        // is signaling valid read address and control information.
    input wire 				      S_AXI_ARVALID,
    // Read address ready. This signal indicates that the slave is
        // ready to accept an address and associated control signals.
    output wire 			      S_AXI_ARREADY,
    // Read data (issued by slave)
    output wire [C_S_AXI_DATA_WIDTH-1 : 0]    S_AXI_RDATA,
    // Read response. This signal indicates the status of the
        // read transfer.
    output wire [1 : 0] 		      S_AXI_RRESP,
    // Read valid. This signal indicates that the channel is
        // signaling the required read data.
    output wire 			      S_AXI_RVALID,
    // Read ready. This signal indicates that the master can
        // accept the read data and response information.
    input wire 				      S_AXI_RREADY
);

   // USER stuff
   wire aclk = S_AXI_ACLK;
   wire aresetn = S_AXI_ARESETN;
   
   // 40 bit stall timer stuff
   reg [39:0] stallTimerReg;
   reg        stallTimerEnable;
   
   // Make 35 registers, we don't need all that many
   reg signed [63:0] R [0:34]; 
   reg signed [63:0] C0R [0:1]; // co-processor 0 register
   
   reg [5:0] 	     op; // TW, for PCP0 I use 6 bits
   reg [BRAM_ADDR_WIDTH-1:0] 	     directAddress; // we only have 13 bits deep memory
   reg [39:0] 	     delayConstant;
   reg [4:0] 	     formatAa, formatBa;
   reg signed [31:0] pc0;
   
   //reg [5:0] a, b, c;
   reg [31:0] 	     CF;
   
   //reg [4:0] c5;
	//reg signed [31:0] c12, c16, c24, Ra, Rb, Rc, pc0; // pc0: instruction pc
   //reg [63:0] uc16, URa, URb, URc, HI, LO, CF, tmp;
   reg [63:0] 	     cycles;
   
   // register name
`define SP R[33]    // Stack Pointer
`define LR R[33]    // Link Register
`define SW R[34]    // Status Word
   
   // C0 register name
`define PC C0R[0]   // Program Counter
`define EPC C0R[1]  // exception PC value
   
   // SW Flage
`define I2 `SW[16]  // Hardware Interrupt 1, IO1 interrupt, status,
   // 1: in interrupt
	`define I1 `SW[15]  // Hardware Interrupt 0, timer interrupt, status,
						// 1: in interrupt
						
	`define I0 `SW[14]  // Software interrupt, status, 1: in interrupt
	`define I `SW[13]   // Interrupt, 1: in interrupt
	`define I2E `SW[12] // Hardware Interrupt 1, IO1 interrupt, Enable
	`define I1E `SW[11] // Hardware Interrupt 0, timer interrupt, Enable
	`define I0E `SW[10] // Software Interrupt Enable
	`define IE `SW[9]   // Interrupt Enable	
	`define M `SW[8:6]  // Mode bits, itype
	`define D `SW[5]    // Debug Trace
	`define V `SW[3]    // Overflow
	`define C `SW[2]    // Carry
	`define Z `SW[1]    // Zero
	`define N `SW[0]    // Negative flag
	`define LE CF[0]    // Endian bit, Big Endian:0, Little Endian:1

   // Instruction Opcodes for PCP0 are only 6 bit
   parameter [5:0] 
     NOP= 	6'b000000,	// do nothing
     DEC=       6'b000001,      // decrement value of register by one
     INC=       6'b000010,      // increment value of regiuster by one
     LD64=	6'b000100,	// load 64 bit value to register
     TXOFFSET=  6'b001000,      // set the txoffset to a 16 bit value in formatA
     GRADOFFSET=  6'b001001,      // set the txoffset to a 16 bit value in formatA
     JNZ=       6'b010000,      // jump to immeduate address of register is nonzero
     BTR=	6'b010100,	// branch to immediate address if triggered
     J=		6'b010111,	// jump to immediate address
     HALT=	6'b011001,	// halt
     PI=	6'b011100,	// pulse lower 32 bit immediately with up to 23 bit delay
     PR=	6'b011101;	// pulse 64 bit register with up to 40 bit delay
   
   reg [0:0] 	     inExe;				// instruction execution
   reg [3:0] 	     state, next_state;		// execution FSM state
   reg [2:0] 	     st_taskInt, ns_taskInt;
   parameter Reset=4'h0, Fetch=4'h1, Decode=4'h2, Execute=4'h3, MemAccess=4'h4, WriteBack=4'h5, Stall=4'h6, Halted=4'h7, WaitForFetch=4'h8, WaitForFetch2=4'h9, MemAccess2=4'hA, MemAccess3=4'hB; // available states
   integer 	     i;
   reg [BRAM_ADDR_WIDTH-1:0] 	     int_mem_addr;
   
   `ifdef SIMULATE_DELAY_SLOT
     reg [0:0] 	     nextInstIsDelaySlot;
     reg [0:0] 	     isDelaySlot;
     reg signed [31:0] delaySlotNextPC;
   `endif
   reg [63:0] 	       result;
   reg [BRAM_ADDR_WIDTH-1:0] 	       NextPC;
   reg [63:0] 	       opA, opB; 	       
	
   // assign the memory interface outputs
   assign bram_porta_addr = int_mem_addr;
   assign bram_porta_clk = aclk;
   assign bram_porta_rst = 0;

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

   // Read Memory Word
   task memReadStart(input [BRAM_ADDR_WIDTH-1:0] addr, input [1:0] size); begin
      int_mem_addr <= addr; // read(m[addr])
      m_en <= 1; // Enable read
      //m_size = size;
   end endtask
   
   // Read Memory Finish, get data
   task memReadEnd(output [63:0] data); begin
      data <= bram_porta_rddata; // return to data
      
      m_en <= 0; // read complete
   end endtask
   
   // Write memory -- addr: address to write, data: date to write
   task memWriteStart(input [31:0] addr, input [63:0] data, input [1:0] size);
      begin
	 //mar = addr; // write(m[addr], data)
	 //mdr = data;
	 //m_rw = 0; // access mode: write
	 //m_en = 1; // Enable write
	 //m_size = size;
      end endtask
   
   task memWriteEnd; begin // Write Memory Finish
      m_en = 0; // write complete
   end endtask
   
   // there is only 8 general user registers in this model
   task regSet(input [3:0] i, input [63:0] data); begin
      if (i != 0) R[i] = data;
   end endtask
   
   task C0regSet(input [3:0] i, input [31:0] data); begin
      if (i < 2) C0R[i] = data;
   end endtask
   
   // increased this to 64 bit data, but the PC cannot be 64 bit wide, naturally
   task PCSet(input [63:0] data); begin
   `ifdef SIMULATE_DELAY_SLOT
      nextInstIsDelaySlot = 1;
      delaySlotNextPC = data;
   `else
      `PC = data;
   `endif
   end endtask
   
   task retValSet(input [3:0] i, input [63:0] data); begin
      if (i != 0)
   `ifdef SIMULATE_DELAY_SLOT
	R[i] = data + 4;
   `else
      R[i] = data;
   `endif
   end endtask
   
   // TW may not need this, as we will have a 64 bit machine anyway
   //task regHILOSet(input [31:0] data1, input [31:0] data2); begin
   //	HI = data1;
   //	LO = data2;
   //end endtask
   
   // output a word to Output port (equal to display the word to terminal)
   task outw(input [63:0] data); begin
      if (data[7:0] != 8'h00) begin
	 $write("%c", data[7:0]);
	 if (data[15:8] != 8'h00)
	   $write("%c", data[15:8]);
	 if (data[23:16] != 8'h00)
	   $write("%c", data[23:16]);
	 if (data[31:24] != 8'h00)
	   $write("%c", data[31:24]);
	 if (data[39:32] != 8'h00)
	   $write("%c", data[39:32]);
	 if (data[47:40] != 8'h00)
	   $write("%c", data[47:40]);
	 if (data[55:48] != 8'h00)
	   $write("%c", data[55:48]);
	 if (data[63:56] != 8'h00)
	   $write("%c", data[63:56]);
      end
   end endtask
   
   // output a character (a byte)
   task outc(input [7:0] data); begin
      $write("%c", data);
   end endtask
   
   task taskInterrupt(input [2:0] iMode); begin
      if (inExe == 0) begin
	 case (iMode)
	   `RESET: begin
	      `PC <= 0; 
	      tick <= 0; 
	      R[0] <= 0; 
	      `SW <= 0; 
	      `LR <= -1;
	      `IE <= 0; 
	      `I0E <= 1; 
	      `I1E <= 1; 
	      `I2E <= 1;
	      `I <= 0; 
	      `I0 <= 0; 
	      `I1 <= 0; 
	      `I2 <= 0; 
	      inExe <= 1;
	      `LE <= cfg;
	      // disable stall timer
	      stallTimerEnable <= 0; 
	      stallTimerReg <= 40'hffffffffff;
	      // output no pulse
	      //pulse = 64'h000000000000ff00;
	      cycles <= 0;
	   end
	   `ABORT: begin `PC <= 1; end
	   `IRQ: begin `PC <= 2; `IE <= 0; inExe <= 1; end
	   `ERROR: begin `PC <= 3; end // without jumping in pcp0 this may not work well
	 endcase
      end
      $display("taskInterrupt(%3b)", iMode);
   end endtask
	
   // State machine without any pipelining
   task taskExecute; begin
      tick <= tick+1;
      case (state)
	Fetch: begin // Tick 1 : instruction fetch, throw PC to address bus,
	   $display("%4dns %8x : Fetching 64 bits ", $stime, `PC);
	   
	   // memory.read(m[PC])
	   memReadStart(`PC[BRAM_ADDR_WIDTH-1:0], `QUAD);
	   pc0 <= `PC;
	   NextPC <= `PC+1;
	   state <= WaitForFetch;
	end

	WaitForFetch: begin
	   state <= MemAccess3;
	end

	MemAccess3: begin
	   state <= WaitForFetch2;
	end
	
	WaitForFetch2: begin
	   state <= Decode;
	   op <= bram_porta_rddata[63:58]; // pcp0 opcode is ALWAYS top 6 bits
	   directAddress <= bram_porta_rddata[BRAM_ADDR_WIDTH-1:0]; // format A direct address
	   delayConstant <= bram_porta_rddata[39:0]; // 40 bit constant for format B
	   formatAa <= bram_porta_rddata[36:32];     // register address for format A
	   formatBa <= bram_porta_rddata[44:40];     // register address for format B
	end
	
	Decode: begin // Tick 2 : instruction decode, ir = m[PC]
	   //memReadEnd(ir); // IR = dbus = m[PC]
	   //$display("%4dns %8x : Decoding ir %b", $stime, pc0, ir);
	   //slv_reg1 <= bram_porta_rddata[63:32];
	   //slv_reg2 <= bram_porta_rddata[31:0];
	   //slv_reg8[7:0] <= 8'b00000011;
	   //slv_reg9[7:0] <= 8'b11000000;
	   state <= Execute;
	   opA <= R[formatAa];
	   opB <= R[formatBa];
	   
	end
	
	Execute: begin // Tick 3 : instruction execution
	   $display("%4dns %8x : Executing op code %6b", $stime, pc0, op);
	   case (op)
	     NOP: begin
		state <= MemAccess;
		end
	     LD64: begin
		memReadStart(directAddress, `QUAD); // LD Ra,directAddress; Ra<=[directAddress]
		state <= MemAccess;		
	     end
	     TXOFFSET: begin
		result[15:0] <= delayConstant[15:0];
		state <= MemAccess;
	     end
	     GRADOFFSET: begin
		result[15:0] <= delayConstant[15:0];
		state <= MemAccess;
	     end
	     JNZ: begin
		if(opA != 64'h0) begin
		  result[BRAM_ADDR_WIDTH-1:0] <= directAddress;
		end
		else
		  begin
		     result[BRAM_ADDR_WIDTH-1:0] <= NextPC;
		  end
		state <= MemAccess;
	     end
	     DEC: begin
		result <= opA - 64'b1;
		state <= MemAccess;
	     end
	     INC: begin  
		result <= opA + 64'b1;
		state <= MemAccess;
	     end
	     J: begin
		result[BRAM_ADDR_WIDTH-1:0] <= directAddress;                   // J directAddress
		state <= MemAccess;
	     end
	     BTR: ;
	     HALT: begin
		pulse[15:8] <= `PC;
		state <= Halted;
		end // when the HALT command is encountered, end the simulation, needs to be modified later
	     PI: begin
		state <= MemAccess;
		end
	     PR: begin
		pulse <= opB; //R[formatBa];
		stallTimerReg <= delayConstant;
		stallTimerEnable <= 1;
		state <= Stall;
	     end
	     default: begin
	       state <= MemAccess;
	       $display("%4dns %8x : OP code %8x not support", $stime, pc0, op);
	     end
	   endcase
	   	      
	end // end Execute
	
	Stall: begin
	   if(stallTimerEnable) 
	     begin
		if(stallTimerReg == 40'h0000000000) 
		  begin
		     stallTimerEnable <= 0;
		     state <= MemAccess;
		  end 
		else 
		  begin 
		     stallTimerReg <= stallTimerReg - 1;
		     state <= Stall;
		  end
             end
	end // end Stall
	
	Halted: begin
	   state <= Halted;
	end // end Halted
	
	MemAccess: begin
	   // we have to wait for the memory again here, because its registered
	   //case (op)
	   //ST, SB, SH : memWriteEnd(); // write memory complete
	   //endcase
	   state <= MemAccess2;
	   `PC <= NextPC;
	end

	MemAccess2: begin
	   state <= WriteBack;
	end
	
	WriteBack: begin // Read/Write finish, close memory
	   case (op)
	     LD64 : begin
		R[formatAa] <= bram_porta_rddata;
	     end
	     TXOFFSET: begin
		tx_offset <= result[15:0];
	     end
	     GRADOFFSET: begin
		grad_offset <= result[15:0];
	     end
	     DEC: begin 
	       R[formatAa] <= result;
	     end
	     INC: begin
		R[formatAa] <= result;
	     end
	     JNZ: begin
		`PC <= result[BRAM_ADDR_WIDTH-1:0];
	     end
	     J: begin 
		`PC <= result[BRAM_ADDR_WIDTH-1:0];
	     end
	   endcase // case (op)
	   
	   state <= Fetch;
	  
	end // WriteBack:
      endcase
   end endtask

   /* This BS doesn't seem to work
   // stall timer
   always @(posedge aclk) begin   
      if(stallTimerEnable && state == Stall && inExe == 1) 
	begin
           if(stallTimerReg == 40'h0000000000) 
	     begin
		stallTimerEnable <= 0;
		//state <= Fetch;
             end 
	   else 
	     begin 
		stallTimerReg <= stallTimerReg - 1;
		//state <= Stall;
             end
	end 
   end
   */
   
   // main loop
   always @(posedge aclk) begin
         
      if(slv_reg0[2:0] == 3'b000) 
	begin
	   inExe <= 0;
	   `PC <= 0;
	   state <= Halted;
	   next_state <= Halted;
	   
	   pulse[15:8]<= 8'b11111111;
	   pulse[7:0] <= 8'b00000000;
	   // for debugging transfer the register over
	   slv_reg1 <= 0; //slv_reg0;
	   slv_reg2 <= 0; 
	   slv_reg3 <= 0; 
	   slv_reg4 <= 0; 
	   slv_reg5 <= 0; 
	   slv_reg6 <= 0; 
	   slv_reg7 <= 0; 
	   slv_reg8 <= 0; 
	   slv_reg9 <= 0; 
	   slv_reg10 <= 0;
	   int_mem_addr <= 0;
	   cycles <= 0;
	   stallTimerEnable <= 0; 
	   stallTimerReg <= 40'hffffffffff;
	   tx_offset <= 0;
	   grad_offset <= 0;
	   
	end
      else if (inExe == 0 && slv_reg0[2:0] == 3'b111) 
	begin
	   // Condition itype == `RESET must after the other `IE condition
	   taskInterrupt(`RESET);
	   state <= Fetch;
	   pulse[15:8] <= 8'b10101010;
	   slv_reg1 <= 8'h88; //slv_reg0;
	end 
      else if (inExe == 1)
	begin
	   taskExecute();
	   //state <= next_state;
	   slv_reg2[31:0] <= `PC;
	   
	   // set the status for the AXI register 3
	   slv_reg3[0] <= inExe;
	   slv_reg3[4:1] <= state;
	   
	   // set register 4 to the last memory address
	   slv_reg1 <= int_mem_addr;
	   
	   // set register 5 to the top half of register 4 and register 6 to the bottom half
	   slv_reg4 <= R[4][63:32];
	   slv_reg5 <= R[4][31:0];
	   slv_reg6 <= R[3][63:32];
	   slv_reg7 <= R[3][31:0];
	   slv_reg8 <= R[2][63:32];
	   slv_reg9 <= R[2][31:0];
	   slv_reg10[12:0] <= directAddress;
	   slv_reg10[31:26] <= op;

	   
	   // 1000 0000 = 0x80
	   // 1001 0000 = 0x90
	   
	   if(cycles == 125000000) begin
	      //pulse[15:8] <= slv_reg8[7:0]; // set the LEDs to the register written
	      cycles <= cycles + 1;
	   end
	   else if(cycles == 250000000) begin
	      //pulse[15:8] <= slv_reg9[7:0];
	      cycles <= 0;
	   end
	   else begin
	      cycles <= cycles+1;
	   end
	end // if (inExe == 1)
      else
	begin
	   pulse[15:8] <= 8'b11111111;
	end
      
      // thats just the output register for debugging
      pc <= `PC;
      //cycles <= cycles + 1;
   end
   
   //
   // User logic ends
endmodule