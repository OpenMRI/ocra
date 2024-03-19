`timescale 1ns / 1ps
module axi_sniffer #
(
    parameter integer C_S_AXI_DATA_WIDTH = 64,
    parameter integer C_S_AXI_ADDR_WIDTH = 32
)
(
    input                                  aclk,
    input                                  aresetn,

    //
    output [3:0]                           awid,
    output [C_S_AXI_ADDR_WIDTH-1:0]        awaddr,
    output [(C_S_AXI_DATA_WIDTH/8)-1:0]    awlen,
    output [2:0]                           awsize,
    output [1:0]                           awburst,
    output [2:0]                           awprot,
    output [3:0]                           awcache,
    output [3:0]                           awuser,
    output                                 awvalid,
    output                                 awready,
    output [C_S_AXI_DATA_WIDTH-1:0]        wdata,
    output [(C_S_AXI_DATA_WIDTH/8)-1:0]    wstrb,
    output                                 wlast,
    output                                 wvalid,
    output                                 wready,
    output [1:0]                           bresp,
    output                                 bvalid,
    output                                 bready,

    //AXI
    input [3:0]                            s_axi_awid,
    input [C_S_AXI_ADDR_WIDTH-1:0]         s_axi_awaddr,
    input [(C_S_AXI_DATA_WIDTH/8)-1:0]     s_axi_awlen,
    input [2:0]                            s_axi_awsize,
    input [1:0]                            s_axi_awburst,
    input [2:0]                            s_axi_awprot,
    input [3:0]                            s_axi_awcache,
    input [3:0]                            s_axi_awuser,
    input                                  s_axi_awvalid,
    input                                  s_axi_awready,
    input [C_S_AXI_DATA_WIDTH-1:0]         s_axi_wdata,
    input [(C_S_AXI_DATA_WIDTH/8)-1:0]     s_axi_wstrb,
    input                                  s_axi_wlast,
    input                                  s_axi_wvalid,
    input                                  s_axi_wready,
    input [1:0]                            s_axi_bresp,
    input                                  s_axi_bvalid,
    input                                  s_axi_bready
);

assign awid         = s_axi_awid;
assign awaddr       = s_axi_awaddr;
assign awlen        = s_axi_awlen;
assign awsize       = s_axi_awsize;
assign awburst      = s_axi_awburst;
assign awprot       = s_axi_awprot;
assign awcache      = s_axi_awcache;
assign awuser       = s_axi_awuser;
assign awvalid      = s_axi_awvalid;
assign awready      = s_axi_awready;
assign wdata        = s_axi_wdata;
assign wstrb        = s_axi_wstrb;
assign wlast        = s_axi_wlast;
assign wvalid       = s_axi_wvalid;
assign wready       = s_axi_wready;
assign bresp        = s_axi_bresp;
assign bvalid       = s_axi_bvalid;
assign bready       = s_axi_bready;

endmodule