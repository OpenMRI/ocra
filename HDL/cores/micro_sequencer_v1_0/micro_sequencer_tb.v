//-----------------------------------------------------------------------------
// Title         : Micro sequencer testbench
// Project       : ocra
//-----------------------------------------------------------------------------
// File          : micro_sequencer_tb.v
// Author        : Vlad Negnevitsky
// Created       : 06.12.2019
// Last modified : 06.12.2019
//-----------------------------------------------------------------------------
// Description :
// Micro sequencer TB
//-----------------------------------------------------------------------------
// Modification history :
// 06.12.2019 : created
//-----------------------------------------------------------------------------

`ifndef _MICRO_SEQUENCER_TB_
 `define _MICRO_SEQUENCER_TB_

`ifndef _MICRO_SEQUENCER_
 `include "micro_sequencer.v"
`endif

 `timescale 1ns/1ns

module micro_sequencer_tb;

   /*AUTOREGINPUT*/
   // Beginning of automatic reg inputs (for undeclared instantiated-module inputs)
   reg			S_AXI_ACLK;		// To UUT of micro_sequencer.v
   reg [C_S_AXI_ADDR_WIDTH-1:0] S_AXI_ARADDR;	// To UUT of micro_sequencer.v
   reg			S_AXI_ARESETN;		// To UUT of micro_sequencer.v
   reg [2:0]		S_AXI_ARPROT;		// To UUT of micro_sequencer.v
   reg			S_AXI_ARVALID;		// To UUT of micro_sequencer.v
   reg [C_S_AXI_ADDR_WIDTH-1:0] S_AXI_AWADDR;	// To UUT of micro_sequencer.v
   reg [2:0]		S_AXI_AWPROT;		// To UUT of micro_sequencer.v
   reg			S_AXI_AWVALID;		// To UUT of micro_sequencer.v
   reg			S_AXI_BREADY;		// To UUT of micro_sequencer.v
   reg			S_AXI_RREADY;		// To UUT of micro_sequencer.v
   reg [C_S_AXI_DATA_WIDTH-1:0] S_AXI_WDATA;	// To UUT of micro_sequencer.v
   reg [(C_S_AXI_DATA_WIDTH/8)-1:0] S_AXI_WSTRB;// To UUT of micro_sequencer.v
   reg			S_AXI_WVALID;		// To UUT of micro_sequencer.v
   reg [BRAM_DATA_WIDTH-1:0] bram_porta_rddata;	// To UUT of micro_sequencer.v
   reg			cfg;			// To UUT of micro_sequencer.v
   // End of automatics

   /*AUTOWIRE*/
   // Beginning of automatic wires (for undeclared instantiated-module outputs)
   wire			S_AXI_ARREADY;		// From UUT of micro_sequencer.v
   wire			S_AXI_AWREADY;		// From UUT of micro_sequencer.v
   wire [1:0]		S_AXI_BRESP;		// From UUT of micro_sequencer.v
   wire			S_AXI_BVALID;		// From UUT of micro_sequencer.v
   wire [C_S_AXI_DATA_WIDTH-1:0] S_AXI_RDATA;	// From UUT of micro_sequencer.v
   wire [1:0]		S_AXI_RRESP;		// From UUT of micro_sequencer.v
   wire			S_AXI_RVALID;		// From UUT of micro_sequencer.v
   wire			S_AXI_WREADY;		// From UUT of micro_sequencer.v
   wire [BRAM_ADDR_WIDTH-1:0] bram_porta_addr;	// From UUT of micro_sequencer.v
   wire			bram_porta_clk;		// From UUT of micro_sequencer.v
   wire			bram_porta_rst;		// From UUT of micro_sequencer.v
   wire [15:0]		grad_offset;		// From UUT of micro_sequencer.v
   wire			m_en;			// From UUT of micro_sequencer.v
   wire [31:0]		pc;			// From UUT of micro_sequencer.v
   wire [63:0]		pulse;			// From UUT of micro_sequencer.v
   wire [2:0]		tick;			// From UUT of micro_sequencer.v
   wire [15:0]		tx_offset;		// From UUT of micro_sequencer.v
   // End of automatics

   micro_sequencer #(/*AUTOINSTPARAM*/
		     // Parameters
		     .C_S_AXI_DATA_WIDTH(C_S_AXI_DATA_WIDTH),
		     .C_S_AXI_ADDR_WIDTH(C_S_AXI_ADDR_WIDTH),
		     .BRAM_DATA_WIDTH	(BRAM_DATA_WIDTH),
		     .BRAM_ADDR_WIDTH	(BRAM_ADDR_WIDTH),
		     .NOP		(NOP[5:0]),
		     .DEC		(DEC[5:0]),
		     .INC		(INC[5:0]),
		     .LD64		(LD64[5:0]),
		     .TXOFFSET		(TXOFFSET[5:0]),
		     .GRADOFFSET	(GRADOFFSET[5:0]),
		     .JNZ		(JNZ[5:0]),
		     .BTR		(BTR[5:0]),
		     .J			(J[5:0]),
		     .HALT		(HALT[5:0]),
		     .PI		(PI[5:0]),
		     .PR		(PR[5:0]),
		     .Reset		(Reset),
		     .Fetch		(Fetch),
		     .Decode		(Decode),
		     .Execute		(Execute),
		     .MemAccess		(MemAccess),
		     .WriteBack		(WriteBack),
		     .Stall		(Stall),
		     .Halted		(Halted),
		     .WaitForFetch	(WaitForFetch),
		     .WaitForFetch2	(WaitForFetch2),
		     .MemAccess2	(MemAccess2),
		     .MemAccess3	(MemAccess3)) UUT (/*AUTOINST*/
							   // Outputs
							   .bram_porta_clk	(bram_porta_clk),
							   .bram_porta_rst	(bram_porta_rst),
							   .bram_porta_addr	(bram_porta_addr[BRAM_ADDR_WIDTH-1:0]),
							   .tick		(tick[2:0]),
							   .pc			(pc[31:0]),
							   .tx_offset		(tx_offset[15:0]),
							   .grad_offset		(grad_offset[15:0]),
							   .m_en		(m_en),
							   .pulse		(pulse[63:0]),
							   .S_AXI_AWREADY	(S_AXI_AWREADY),
							   .S_AXI_WREADY	(S_AXI_WREADY),
							   .S_AXI_BRESP		(S_AXI_BRESP[1:0]),
							   .S_AXI_BVALID	(S_AXI_BVALID),
							   .S_AXI_ARREADY	(S_AXI_ARREADY),
							   .S_AXI_RDATA		(S_AXI_RDATA[C_S_AXI_DATA_WIDTH-1:0]),
							   .S_AXI_RRESP		(S_AXI_RRESP[1:0]),
							   .S_AXI_RVALID	(S_AXI_RVALID),
							   // Inputs
							   .bram_porta_rddata	(bram_porta_rddata[BRAM_DATA_WIDTH-1:0]),
							   .cfg			(cfg),
							   .S_AXI_ACLK		(S_AXI_ACLK),
							   .S_AXI_ARESETN	(S_AXI_ARESETN),
							   .S_AXI_AWADDR	(S_AXI_AWADDR[C_S_AXI_ADDR_WIDTH-1:0]),
							   .S_AXI_AWPROT	(S_AXI_AWPROT[2:0]),
							   .S_AXI_AWVALID	(S_AXI_AWVALID),
							   .S_AXI_WDATA		(S_AXI_WDATA[C_S_AXI_DATA_WIDTH-1:0]),
							   .S_AXI_WSTRB		(S_AXI_WSTRB[(C_S_AXI_DATA_WIDTH/8)-1:0]),
							   .S_AXI_WVALID	(S_AXI_WVALID),
							   .S_AXI_BREADY	(S_AXI_BREADY),
							   .S_AXI_ARADDR	(S_AXI_ARADDR[C_S_AXI_ADDR_WIDTH-1:0]),
							   .S_AXI_ARPROT	(S_AXI_ARPROT[2:0]),
							   .S_AXI_ARVALID	(S_AXI_ARVALID),
							   .S_AXI_RREADY	(S_AXI_RREADY));

endmodule // micro_sequencer_tb

`endif //  `ifndef _MICRO_SEQUENCER_TB_

