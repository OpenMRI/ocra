
interface axi4_lite_intf #(parameter AXI_DATA_WIDTH = 32, parameter AXI_ADDR_WIDTH=16)
    (input logic clk, rst);
    logic[AXI_ADDR_WIDTH-1 : 0]      M_AXI_AWADDR;
    logic[2 : 0]                     M_AXI_AWPROT;
    logic                            M_AXI_AWVALID;
    logic                            M_AXI_AWREADY;
    logic[AXI_DATA_WIDTH-1 : 0]      M_AXI_WDATA;
    logic[(AXI_DATA_WIDTH/8)-1 : 0]  M_AXI_WSTRB;
    logic                            M_AXI_WVALID;
    logic                            M_AXI_WREADY;
    logic [1 : 0]                    M_AXI_BRESP;
    logic                            M_AXI_BVALID;
    logic                            M_AXI_BREADY;
    logic[AXI_ADDR_WIDTH-1 : 0]      M_AXI_ARADDR;
    logic[2 : 0]                     M_AXI_ARPROT;
    logic                            M_AXI_ARVALID;
    logic                            M_AXI_ARREADY;
    logic [AXI_DATA_WIDTH-1 : 0]     M_AXI_RDATA;
    logic [1 : 0]                    M_AXI_RRESP;
    logic                            M_AXI_RVALID;
    logic                            M_AXI_RREADY;
endinterface : axi4_lite_intf
