
`timescale 1 ns / 1 ps

module axi_lite_master #
(
  parameter integer AXI_DATA_WIDTH = 32,
  parameter integer AXI_ADDR_WIDTH = 32,
  parameter integer FIFO_DEPTH     = 16
)
(
  // System signals
  input wire 			                   aclk,
  input wire 			                   aresetn,

  // Master side
  output wire  [AXI_ADDR_WIDTH-1 : 0]      M_AXI_AWADDR,
  output wire  [2 : 0]                     M_AXI_AWPROT,
  output wire                              M_AXI_AWVALID,
  input  wire                              M_AXI_AWREADY,
  output wire  [AXI_DATA_WIDTH-1 : 0]      M_AXI_WDATA,
  output wire  [(AXI_DATA_WIDTH/8)-1 : 0]  M_AXI_WSTRB,
  output wire                              M_AXI_WVALID,
  input  wire                              M_AXI_WREADY,
  input  wire  [1 : 0]                     M_AXI_BRESP,
  input  wire                              M_AXI_BVALID,
  output wire                              M_AXI_BREADY,
  output wire  [AXI_ADDR_WIDTH-1 : 0]      M_AXI_ARADDR,
  output wire  [2 : 0]                     M_AXI_ARPROT,
  output wire                              M_AXI_ARVALID,
  input  wire                              M_AXI_ARREADY,
  input  wire  [AXI_DATA_WIDTH-1 : 0]      M_AXI_RDATA,
  input  wire  [1 : 0]                     M_AXI_RRESP,
  input  wire                              M_AXI_RVALID,
  output wire                              M_AXI_RREADY,

  //
  input  wire  [AXI_DATA_WIDTH-1 : 0]      wdata_i,
  input  wire  [AXI_ADDR_WIDTH-1 : 0]      waddr_i,
  input  wire  [(AXI_DATA_WIDTH/8)-1 : 0]  wstrb_i,
  input  wire                              write_i,
  output wire                              full_o,
  output wire                              write_failure_o,
  output wire                              timeout_failure_o
);

axi_lite_master_core #(
    .AXI_DATA_WIDTH (AXI_DATA_WIDTH),
    .AXI_ADDR_WIDTH (AXI_ADDR_WIDTH),
    .FIFO_DEPTH     (FIFO_DEPTH)
) inst (
  .aclk             (aclk             ),
  .aresetn          (aresetn          ),
                                      
  .M_AXI_AWADDR     (M_AXI_AWADDR     ),
  .M_AXI_AWPROT     (M_AXI_AWPROT     ),
  .M_AXI_AWVALID    (M_AXI_AWVALID    ),
  .M_AXI_AWREADY    (M_AXI_AWREADY    ),
  .M_AXI_WDATA      (M_AXI_WDATA      ),
  .M_AXI_WSTRB      (M_AXI_WSTRB      ),
  .M_AXI_WVALID     (M_AXI_WVALID     ),
  .M_AXI_WREADY     (M_AXI_WREADY     ),
  .M_AXI_BRESP      (M_AXI_BRESP      ),
  .M_AXI_BVALID     (M_AXI_BVALID     ),
  .M_AXI_BREADY     (M_AXI_BREADY     ),
  .M_AXI_ARADDR     (M_AXI_ARADDR     ),
  .M_AXI_ARPROT     (M_AXI_ARPROT     ),
  .M_AXI_ARVALID    (M_AXI_ARVALID    ),
  .M_AXI_ARREADY    (M_AXI_ARREADY    ),
  .M_AXI_RDATA      (M_AXI_RDATA      ),
  .M_AXI_RRESP      (M_AXI_RRESP      ),
  .M_AXI_RVALID     (M_AXI_RVALID     ),
  .M_AXI_RREADY     (M_AXI_RREADY     ),
                                      
  .wdata_i          (wdata_i          ),
  .waddr_i          (waddr_i          ),
  .wstrb_i          (wstrb_i          ),
  .write_i          (write_i          ),
  .full_o           (full_o           ),
  .write_failure_o  (write_failure_o  ),
  .timeout_failure_o(timeout_failure_o)
);

endmodule
