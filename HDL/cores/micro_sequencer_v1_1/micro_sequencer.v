`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company:
// Engineer: Thomas Witzel
//
// Create Date: 03/18/2020
// Design Name:
// Module Name: micro_sequencer
// Project Name: ocra
// Target Devices: Zynq
// Tool Versions:
// Description:
//
// Dependencies:
//
// Revision:
// Revision 1.1
// Additional Comments:
//
//////////////////////////////////////////////////////////////////////////////////

// TW notes 2020:
//
// TODO:
// -need to make sure C_S_AXIS_DATA_WIDTH is never less than 32, because
//  thats the only way the register assignments will work

module micro_sequencer #(parameter integer C_S_AXI_DATA_WIDTH = 32,
                         parameter integer C_S_AXI_ADDR_WIDTH = 16,
                         parameter integer C_M_AXI_ADDR_WIDTH = 32,
                         parameter integer BRAM_DATA_WIDTH = 64,
                         parameter integer BRAM_ADDR_WIDTH = 10,
                         parameter integer C_M_AXI_ADDR_OFFSET = 32'h4000_0000,
                         parameter integer ADDRESS_LUT_DEPTH = 256,
                         parameter         MS_RASTER_CLOCK_PERIOD = 1250)
   (output wire                         bram_porta_clk,
    output wire                         bram_porta_rst,
    output wire [BRAM_ADDR_WIDTH-1:0]   bram_porta_addr,
    input wire [BRAM_DATA_WIDTH-1:0]    bram_porta_rddata,
    output wire [2:0]                   tick,
    output wire [31:0]                  pc,
    output wire [15:0]                  tx_offset,
    output wire [15:0]                  grad_offset,
    output wire [31:0]                  phase_offset,
    output wire                         m_en,
    output wire [63:0]                  pulse,
    output wire                         timer_enable,
    output wire [3:0]                   ps_interrupts,
    output wire [1:0]                   raster_clk_rstn,
    input  wire                         unpause,
    output wire  [C_S_AXI_DATA_WIDTH-1:0] axi_wdata,
    output wire  [C_M_AXI_ADDR_WIDTH-1:0] axi_waddr,
    output wire  [3:0]                  axi_wstrb,
    output wire                         axi_write,
    input wire                          axi_write_busy,
    input wire                          axi_write_failed,
    output wire                         tr_start,
    output wire                         sequencer_active,
    input wire                          S_AXI_ACLK,
    input wire                          S_AXI_ARESETN,
    input wire [C_S_AXI_ADDR_WIDTH-1 : 0] S_AXI_AWADDR,
    input wire [2 : 0]                  S_AXI_AWPROT,
    input wire                          S_AXI_AWVALID,
    output wire                         S_AXI_AWREADY,
    input wire [C_S_AXI_DATA_WIDTH-1 : 0] S_AXI_WDATA,
    input wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0] S_AXI_WSTRB,
    input wire                          S_AXI_WVALID,
    output wire                         S_AXI_WREADY,
    output wire [1 : 0]                 S_AXI_BRESP,
    output wire                         S_AXI_BVALID,
    input wire                          S_AXI_BREADY,
    input wire [C_S_AXI_ADDR_WIDTH-1 : 0] S_AXI_ARADDR,
    input wire [2 : 0]                  S_AXI_ARPROT,
    input wire                          S_AXI_ARVALID,
    output wire                         S_AXI_ARREADY,
    output wire [C_S_AXI_DATA_WIDTH-1 : 0] S_AXI_RDATA,
    output wire [1 : 0]                 S_AXI_RRESP,
    output wire                         S_AXI_RVALID,
    input wire                          S_AXI_RREADY
    );

    micro_sequencer_top #(
        .C_S_AXI_DATA_WIDTH (C_S_AXI_DATA_WIDTH ),
        .C_S_AXI_ADDR_WIDTH (C_S_AXI_ADDR_WIDTH ),
        .BRAM_DATA_WIDTH    (BRAM_DATA_WIDTH    ),
        .BRAM_ADDR_WIDTH    (BRAM_ADDR_WIDTH    ),
        .ADDRESS_LUT_DEPTH  (ADDRESS_LUT_DEPTH  ),
        .MS_RASTER_CLOCK_PERIOD(MS_RASTER_CLOCK_PERIOD)
    ) micro_sequencer_inst (
        .bram_porta_clk         (bram_porta_clk     ),
        .bram_porta_rst         (bram_porta_rst     ),
        .bram_porta_addr        (bram_porta_addr    ),
        .bram_porta_rddata      (bram_porta_rddata  ),
        .tick                   (tick               ),
        .pc                     (pc                 ),
        .tx_offset              (tx_offset          ),
        .grad_offset            (grad_offset        ),
        .phase_offset           (phase_offset       ),
        .m_en                   (m_en               ),
        .pulse                  (pulse              ),
        .timer_enable           (timer_enable       ),
        .ps_interrupts          (ps_interrupts      ),
        .raster_clk_rstn        (raster_clk_rstn    ),
        .unpause                (unpause            ),
        .m_axi_wdata            (axi_wdata          ),
        .m_axi_waddr            (axi_waddr          ),
        .m_axi_wstrb            (axi_wstrb          ),
        .m_axi_write            (axi_write          ),
        .m_axi_write_busy       (axi_write_busy     ),
        .m_axi_write_failed     (axi_write_failed   ),
        .tr_start               (tr_start           ),
        .sequencer_active       (sequencer_active   ),
        .S_AXI_ACLK             (S_AXI_ACLK         ),
        .S_AXI_ARESETN          (S_AXI_ARESETN      ),
        .S_AXI_AWADDR           (S_AXI_AWADDR       ),
        .S_AXI_AWPROT           (S_AXI_AWPROT       ),
        .S_AXI_AWVALID          (S_AXI_AWVALID      ),
        .S_AXI_AWREADY          (S_AXI_AWREADY      ),
        .S_AXI_WDATA            (S_AXI_WDATA        ),
        .S_AXI_WSTRB            (S_AXI_WSTRB        ),
        .S_AXI_WVALID           (S_AXI_WVALID       ),
        .S_AXI_WREADY           (S_AXI_WREADY       ),
        .S_AXI_BRESP            (S_AXI_BRESP        ),
        .S_AXI_BVALID           (S_AXI_BVALID       ),
        .S_AXI_BREADY           (S_AXI_BREADY       ),
        .S_AXI_ARADDR           (S_AXI_ARADDR       ),
        .S_AXI_ARPROT           (S_AXI_ARPROT       ),
        .S_AXI_ARVALID          (S_AXI_ARVALID      ),
        .S_AXI_ARREADY          (S_AXI_ARREADY      ),
        .S_AXI_RDATA            (S_AXI_RDATA        ),
        .S_AXI_RRESP            (S_AXI_RRESP        ),
        .S_AXI_RVALID           (S_AXI_RVALID       ),
        .S_AXI_RREADY           (S_AXI_RREADY       )
    );

endmodule
