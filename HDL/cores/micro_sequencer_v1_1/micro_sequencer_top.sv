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

module micro_sequencer_top #(parameter integer C_S_AXI_DATA_WIDTH = 32,
                         parameter integer C_S_AXI_ADDR_WIDTH = 16,
                         parameter integer C_M_AXI_ADDR_WIDTH = 32,
                         parameter integer BRAM_DATA_WIDTH = 64,
                         parameter integer BRAM_ADDR_WIDTH = 10,
                         parameter integer C_M_AXI_ADDR_OFFSET = 32'h4000_0000,
                         parameter integer MS_RASTER_CLOCK_PERIOD = 1250,
                         parameter integer ADDRESS_LUT_DEPTH = 256)
   (output wire                         bram_porta_clk,
    output wire                         bram_porta_rst,
    output wire [BRAM_ADDR_WIDTH-1:0]   bram_porta_addr,
    input wire [BRAM_DATA_WIDTH-1:0]    bram_porta_rddata,
    output wire [2:0]                   tick,
    output wire [31:0]                  pc,
    output wire [15:0]                  tx_offset,
    output wire [15:0]                  grad_offset,
    output wire [31:0]                  phase_offset,
    output wire                         buffer_select,
    output wire                         m_en,
    output wire [63:0]                  pulse,
    output wire                         timer_enable,
    output wire [3:0]                   ps_interrupts,
    output wire [1:0]			        raster_clk_rstn,
    output wire  [C_S_AXI_DATA_WIDTH-1:0] m_axi_wdata,
    output wire  [C_M_AXI_ADDR_WIDTH-1:0] m_axi_waddr,
    output wire  [3:0]                  m_axi_wstrb,
    output wire                         m_axi_write,
    input wire                          m_axi_write_busy,
    input wire                          m_axi_write_failed,
    output wire                         tr_start,
    output wire                         sequencer_active,
    input wire                          external_trigger, 
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

    localparam NumOfRegRW    = 3;
    localparam NumOfRegRO    = 2;    
    localparam NumOfReg      = NumOfRegRW + NumOfRegRO;    

    // Example-specific design signals
    // local parameter for addressing 32 bit / 64 bit C_S_AXI_DATA_WIDTH
    // ADDR_LSB is used for addressing 32/64 bit registers/memories
    // ADDR_LSB = 2 for 32 bits (n downto 2)
    // ADDR_LSB = 3 for 64 bits (n downto 3)
    localparam integer                   ADDR_LSB          = (C_S_AXI_DATA_WIDTH/32) + 1;
    localparam integer                   OPT_MEM_ADDR_BITS = $clog2(NumOfReg);

    localparam [$clog2(MS_RASTER_CLOCK_PERIOD)-1:0] RasterDuration = MS_RASTER_CLOCK_PERIOD;
    localparam [$clog2(MS_RASTER_CLOCK_PERIOD)-1:0] RasterDurationCnt = MS_RASTER_CLOCK_PERIOD - 1;

    typedef enum {
        Configuration   = 0,    //RW
        Buffer          = 1,    //RW
        AxiWriteMemory  = 2,    //WO
        Status          = 3,    //RO
        OperatingStatus = 4     //RO
    } register_e;

    typedef enum logic [3-1:0] {
        Stop   = 'b000,
        Start  = 'b111
    } seq_state_e;

    wire                                aclk    = S_AXI_ACLK;
    wire                                aresetn = S_AXI_ARESETN;
     
    integer                             i, j, byte_index;
  
    // Memory mapped Registers
    logic [C_S_AXI_DATA_WIDTH-1:0]      slv_reg  [0:NumOfReg-1];
    logic [C_S_AXI_DATA_WIDTH-1:0]      slv_reg_d[0:NumOfRegRW-1];
   
    // Microsequencer Configuration and Status
    logic [2:0]                         seq_state_ctrl;
    logic                               ms_stop;
    logic                               ms_start;
    logic                               abort_seq;
    // Interrupt Configuration
    logic                               ms_interrupt_start;
    logic                               ms_interrupt_end;
    logic                               ms_interrupt_halt;
    logic                               ms_interrupt_paused;
    logic                               en_psirq_trstart;
    logic                               en_psirq_trend;
    logic                               en_psirq_halt;
    logic                               en_psirq_paused;
    logic [7:0]                         num_psirq_cycles;
    logic [7:0]                         psirq_error_code;
    logic [3:0]                         interrupt_pulse;
    // Double Buffer
    logic                               double_buffer_en;
    logic                               buffer_ready;
    logic [BRAM_ADDR_WIDTH-1:0]         buffer_address_offset;
    logic                               current_buffer;
    // Pause
    logic                               unpause_strobe;
    // Microsequencer State Machine Status
    logic [15:0]                        current_instruction_addr;
    logic [7:0]                         current_state;
    logic [7:0]                         current_opcode;
    //AXI4 Memory Mapped Registers
    logic                               axi_write;
    logic [C_S_AXI_ADDR_WIDTH-1 : 0]    axi_write_address;
    logic [(C_S_AXI_DATA_WIDTH/8)-1 : 0]axi_write_strobe;
    logic [C_S_AXI_DATA_WIDTH-1 : 0]    axi_write_data;
    logic                               axi_read;
    logic [C_S_AXI_ADDR_WIDTH-1 : 0]    axi_read_address;
    logic [C_S_AXI_DATA_WIDTH-1 : 0]    axi_read_data;
    //Micro Sequencer Trigger
    logic                               ms_ext_tr_trigger;
    logic                               start_internal_trigger_loop;
    logic                               internal_trigger_loop_enable_q;
    logic [$clog2(MS_RASTER_CLOCK_PERIOD)-1:0] internal_trigger_loop_count;
    logic                               force_trigger;
    //Micro Sequencer AXI Write
    logic [C_S_AXI_ADDR_WIDTH-1:0]      int_lut_data;
    logic [$clog2(ADDRESS_LUT_DEPTH)-1:0]int_lut_addr;
    logic                               int_lut_write;

    //Configuration Assignment
    assign seq_state_ctrl       = slv_reg[Configuration][2:0];
    assign en_psirq_trstart     = slv_reg[Configuration][8];
    assign en_psirq_trend       = slv_reg[Configuration][9];
    assign en_psirq_halt        = slv_reg[Configuration][10];
    assign en_psirq_paused      = slv_reg[Configuration][11];
    assign num_psirq_cycles     = slv_reg[Configuration][23:16];
    assign abort_seq            = slv_reg[Configuration][24];
    assign unpause_strobe       = slv_reg[Configuration][25];
    assign start_internal_trigger_loop = slv_reg[Configuration][26];

    assign double_buffer_en     = slv_reg[Buffer][0];
    assign buffer_address_offset= slv_reg[Buffer][BRAM_ADDR_WIDTH+8-1:8];
    assign buffer_ready         = slv_reg[Buffer][24];

    assign int_lut_data         = slv_reg[AxiWriteMemory][C_S_AXI_ADDR_WIDTH-1:0];
    assign int_lut_addr         = slv_reg[AxiWriteMemory][24+$clog2(ADDRESS_LUT_DEPTH)-1:24];

    assign slv_reg[Status][7:0] = psirq_error_code;
    assign slv_reg[Status][8]   = current_buffer;
    assign slv_reg[Status][C_S_AXI_DATA_WIDTH-1:9] = '0;

    assign slv_reg[OperatingStatus][7:0]   = current_state;
    assign slv_reg[OperatingStatus][15:8]  = current_opcode;
    assign slv_reg[OperatingStatus][31:16] = current_instruction_addr;

    assign interrupt_pulse      = { ms_interrupt_paused & en_psirq_paused,
                                    ms_interrupt_halt & en_psirq_halt,
                                    ms_interrupt_end  & en_psirq_trend  ,
                                    ms_interrupt_start& en_psirq_trstart};

    //Output
    assign tick                 = '0;
    assign pc                   = '0;
    assign m_en                 = '0;
    assign buffer_select        = current_buffer;
    //Modules

    //Microsequencer
    micro_sequencer_core #(
        .C_S_AXI_DATA_WIDTH (C_S_AXI_DATA_WIDTH     ),
        .C_S_AXI_ADDR_WIDTH (C_S_AXI_ADDR_WIDTH     ),
        .BRAM_DATA_WIDTH    (BRAM_DATA_WIDTH        ),
        .BRAM_ADDR_WIDTH    (BRAM_ADDR_WIDTH        ),
        .ADDRESS_LUT_DEPTH  (ADDRESS_LUT_DEPTH      )
    ) micro_sequencer_inst (
        .bram_porta_clk     (bram_porta_clk         ),
        .bram_porta_rst     (bram_porta_rst         ),
        .bram_porta_addr_o  (bram_porta_addr        ),
        .bram_porta_rddata_i(bram_porta_rddata      ),

        .tx_offset_o        (tx_offset              ),
        .grad_offset_o      (grad_offset            ),
        .phase_offset_o     (phase_offset           ),
        .pulse_o            (pulse                  ),
        .timer_enable_o     (timer_enable           ),

        .interrupt_start_o  (ms_interrupt_start     ),
        .interrupt_end_o    (ms_interrupt_end       ),
        .interrupt_error_o  (ms_interrupt_halt      ),
        .interrupt_paused_o (ms_interrupt_paused    ),
        .error_code_o       (psirq_error_code       ),
        .current_buffer_o   (current_buffer         ),

	    .raster_clk_rstn_o  (raster_clk_rstn	    ),

        .axi_wdata_o        (m_axi_wdata            ),
        .axi_waddr_o        (m_axi_waddr            ),
        .axi_wstrb_o        (m_axi_wstrb            ),
        .axi_write_o        (m_axi_write            ),
        .axi_write_busy_i   (m_axi_write_busy       ),
        .axi_write_failed_i (m_axi_write_failed     ),
        .int_lut_data_i     (int_lut_data           ),
        .int_lut_addr_i     (int_lut_addr           ),
        .int_lut_write_i    (int_lut_write          ),

        .start_i            (ms_start               ),  //Sequence State Control -> 111
        .stop_i             (ms_stop                ),  //Sequence State Control -> 000
        .double_buffer_i    (double_buffer_en       ),  //Double Buffering Mode
        .buffer_ready_i     (buffer_ready           ),  //Next Buffer is Ready
        .abort_seq_i        (abort_seq              ),  //Request to abort as soon as the current sequence block is completed
        .mem_addr_offset_i  (buffer_address_offset  ),  //Address Offset on Double Buffering Mode
        .ms_ext_tr_trigger_i(ms_ext_tr_trigger      ),

        .unpause_strobe_i   (unpause_strobe         ),
        .current_bram_addr_o(current_instruction_addr),
        .current_state_o    (current_state          ),
        .current_opcode_o   (current_opcode         ),
        .active_state_o     (sequencer_active       ),

        .clk                (aclk                   ),
        .rst_n              (aresetn                )
    );

    //Interrupt
    pulse_extender #(
        .Width(8)
    ) pulse_extender_inst [3:0] (
        .pulse_extend_o     (ps_interrupts          ),
        .pulse_i            (interrupt_pulse        ),
        .duration_i         ({4{num_psirq_cycles}}  ),
        .clk                (aclk                   ),
        .rst_n              (aresetn                )
    );

    pulse_extender #(
        .Width($clog2(MS_RASTER_CLOCK_PERIOD))
    ) pulse_extender_tr_start (
        .pulse_extend_o     (tr_start               ),
        .pulse_i            (ms_interrupt_start     ),
        .duration_i         (RasterDuration         ),
        .clk                (aclk                   ),
        .rst_n              (aresetn                )
    );

    //Axi Module and logic
    s_axi4_lite_reg_control #(
        .C_S_AXI_DATA_WIDTH (C_S_AXI_DATA_WIDTH     ),
        .C_S_AXI_ADDR_WIDTH (C_S_AXI_ADDR_WIDTH     )
    ) s_axi_reg_control (
        .S_AXI_ACLK         (S_AXI_ACLK             ),
        .S_AXI_ARESETN      (S_AXI_ARESETN          ),
        .S_AXI_AWADDR       (S_AXI_AWADDR           ),
        .S_AXI_AWPROT       (S_AXI_AWPROT           ),
        .S_AXI_AWVALID      (S_AXI_AWVALID          ),
        .S_AXI_AWREADY      (S_AXI_AWREADY          ),
        .S_AXI_WDATA        (S_AXI_WDATA            ),
        .S_AXI_WSTRB        (S_AXI_WSTRB            ),
        .S_AXI_WVALID       (S_AXI_WVALID           ),
        .S_AXI_WREADY       (S_AXI_WREADY           ),
        .S_AXI_BRESP        (S_AXI_BRESP            ),
        .S_AXI_BVALID       (S_AXI_BVALID           ),
        .S_AXI_BREADY       (S_AXI_BREADY           ),
        .S_AXI_ARADDR       (S_AXI_ARADDR           ),
        .S_AXI_ARPROT       (S_AXI_ARPROT           ),
        .S_AXI_ARVALID      (S_AXI_ARVALID          ),
        .S_AXI_ARREADY      (S_AXI_ARREADY          ),
        .S_AXI_RDATA        (S_AXI_RDATA            ),
        .S_AXI_RRESP        (S_AXI_RRESP            ),
        .S_AXI_RVALID       (S_AXI_RVALID           ),
        .S_AXI_RREADY       (S_AXI_RREADY           ),
    
        .write_o            (axi_write              ),
        .write_address_o    (axi_write_address      ),
        .write_strobe_o     (axi_write_strobe       ),
        .write_data_o       (axi_write_data         ),
        .read_o             (axi_read               ),
        .read_address_o     (axi_read_address       ),
        .read_data_i        (axi_read_data          )
    );

    // Implement memory mapped register select and write logic generation
    // The write data is accepted and written to memory mapped registers when
    // axi_awready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted. Write strobes are used to
    // select byte enables of slave registers while writing.
    // These registers are cleared when reset (active low) is applied.
    // Slave register write enable is asserted when valid address and data are available
    // and the slave is ready to accept the write address and write data.
    //assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;

    //Change in RW Logic: RW Register now can either be modified through the Memory Mapped Write (AXI4-MM) or
    //                    by the internal core logic. The AXI4 write takes higher priority in the event of write collision.
    assign slv_reg_d[Configuration][25-1:0]                 = slv_reg[Configuration][25-1:0];
    assign slv_reg_d[Configuration][25]                     = 1'b0; //Unpause strobe bit is set through AXI4-MM write, and is automatically unset after.
    assign slv_reg_d[Configuration][26]                     = 1'b0; //Force trigger strobe bit is automatically unset
    assign slv_reg_d[Configuration][C_S_AXI_DATA_WIDTH-1:27]= slv_reg[Configuration][C_S_AXI_DATA_WIDTH-1:27];
    assign slv_reg_d[Buffer][24-1:0]                        = slv_reg[Buffer][24-1:0];
    assign slv_reg_d[Buffer][24]                            = ms_interrupt_start ? 1'b0 : slv_reg[Buffer][24];
    assign slv_reg_d[Buffer][C_S_AXI_DATA_WIDTH-1:25]       = slv_reg[Buffer][C_S_AXI_DATA_WIDTH-1:25];
    assign slv_reg_d[AxiWriteMemory][C_S_AXI_DATA_WIDTH-1:0]= slv_reg[AxiWriteMemory][C_S_AXI_DATA_WIDTH-1:0];
    //RW Registers 
    always @(posedge aclk) begin
        if (aresetn == 1'b0) begin
            for (i=0; i<NumOfRegRW; i=i+1)
                slv_reg[i] <= 'h0;
            end
        else begin
            for (i=0; i<NumOfRegRW; i=i+1) begin
                if (axi_write && axi_write_address[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] == i) begin
                    //Update each byte
                    for (byte_index = 0; byte_index < (C_S_AXI_DATA_WIDTH/8); byte_index = byte_index+1) begin
                        slv_reg[i][(byte_index*8) +: 8] <= (axi_write_strobe[byte_index] == 1) ? axi_write_data[(byte_index*8) +: 8] : slv_reg[i][(byte_index*8) +: 8];
                    end
                end
                else
                    slv_reg[i] <= slv_reg_d[i];
            end
        end
    end
   
    logic [C_S_AXI_DATA_WIDTH-1 : 0]    reg_data_out;
    always @(*)
        begin
         // Address decoding for reading registers
        case (axi_read_address[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB]) inside
            [0:NumOfReg-1]:
                reg_data_out  = slv_reg[axi_read_address[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB]];
            default :
                reg_data_out = 0;
        endcase
    end

    // Output register or memory read data
    always @(posedge aclk)
      begin
         if (aresetn == 1'b0)
           begin
              axi_read_data <= 0;
           end
         else
           begin
              // When there is a valid read address (S_AXI_ARVALID) with
              // acceptance of read address by the slave (axi_arready),
              // output the read dada
              if (axi_read)
                begin
                   axi_read_data <= reg_data_out;     // register read data
                end
           end
      end

    //Micro Sequencer Raster Clock and Delayed Ms Start/Stop
    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            ms_stop                 <= 'b1;
            ms_start                <= 'b0;
            internal_trigger_loop_enable_q  <= 'b0;
            internal_trigger_loop_count <= 'b0;
        end
        else begin
            ms_stop                 <= seq_state_ctrl == Stop || !ms_start;
            ms_start                <= (seq_state_ctrl == Start && ms_ext_tr_trigger) ||
                                       (seq_state_ctrl == Start && ms_start);
            internal_trigger_loop_enable_q  <= seq_state_ctrl == Start && (start_internal_trigger_loop || internal_trigger_loop_enable_q);
            internal_trigger_loop_count <= !internal_trigger_loop_enable_q || internal_trigger_loop_count == RasterDurationCnt ? '0 : internal_trigger_loop_count + 1;
        end
    end
    assign force_trigger = internal_trigger_loop_count == RasterDurationCnt;
    assign ms_ext_tr_trigger = external_trigger || force_trigger;

    //Internal AXI Write Memory
    always_ff @(posedge aclk)
        int_lut_write   <= axi_write && axi_write_address[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] == AxiWriteMemory;

endmodule

module s_axi4_lite_reg_control #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 16
    ) (
    // AXI4Lite IOs
    input wire                                  S_AXI_ACLK,
    input wire                                  S_AXI_ARESETN,
    input wire  [C_S_AXI_ADDR_WIDTH-1 : 0]      S_AXI_AWADDR,
    input wire  [2 : 0]                         S_AXI_AWPROT,
    input wire                                  S_AXI_AWVALID,
    output wire                                 S_AXI_AWREADY,
    input wire  [C_S_AXI_DATA_WIDTH-1 : 0]      S_AXI_WDATA,
    input wire  [(C_S_AXI_DATA_WIDTH/8)-1 : 0]  S_AXI_WSTRB,
    input wire                                  S_AXI_WVALID,
    output wire                                 S_AXI_WREADY,
    output wire [1 : 0]                         S_AXI_BRESP,
    output wire                                 S_AXI_BVALID,
    input wire                                  S_AXI_BREADY,
    input wire  [C_S_AXI_ADDR_WIDTH-1 : 0]      S_AXI_ARADDR,
    input wire  [2 : 0]                         S_AXI_ARPROT,
    input wire                                  S_AXI_ARVALID,
    output wire                                 S_AXI_ARREADY,
    output wire [C_S_AXI_DATA_WIDTH-1 : 0]      S_AXI_RDATA,
    output wire [1 : 0]                         S_AXI_RRESP,
    output wire                                 S_AXI_RVALID,
    input wire                                  S_AXI_RREADY,
    // To Microsequencer Memory Mapped Register
    output                                      write_o,
    output      [C_S_AXI_ADDR_WIDTH-1 : 0]      write_address_o,
    output      [(C_S_AXI_DATA_WIDTH/8)-1 : 0]  write_strobe_o,
    output      [C_S_AXI_DATA_WIDTH-1 : 0]      write_data_o,
    output                                      read_o,
    output      [C_S_AXI_ADDR_WIDTH-1 : 0]      read_address_o,
    input       [C_S_AXI_DATA_WIDTH-1 : 0]      read_data_i
    );

    // AXI4LITE signals
    reg     [C_S_AXI_ADDR_WIDTH-1 : 0]          axi_awaddr;
    reg                                         axi_awready;
    reg                                         axi_wready;
    reg     [1 : 0]                             axi_bresp;
    reg                                         axi_bvalid;
    reg     [C_S_AXI_ADDR_WIDTH-1 : 0]          axi_araddr;
    reg                                         axi_arready;
    reg     [1 : 0]                             axi_rresp;
    reg                                         axi_rvalid;

    wire                                        slv_reg_rden;
    wire                                        slv_reg_wren;
    integer                                     byte_index;

    assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;
    assign slv_reg_rden = axi_arready & S_AXI_ARVALID & ~axi_rvalid;

    // I/O Connections assignments
    assign S_AXI_AWREADY    = axi_awready;
    assign S_AXI_WREADY     = axi_wready;
    assign S_AXI_BRESP      = axi_bresp;
    assign S_AXI_BVALID     = axi_bvalid;
    assign S_AXI_ARREADY    = axi_arready;
    assign S_AXI_RDATA      = read_data_i;
    assign S_AXI_RRESP      = axi_rresp;
    assign S_AXI_RVALID     = axi_rvalid;

    // 
    assign write_o          = slv_reg_wren;
    assign write_address_o  = axi_awaddr;
    assign write_strobe_o   = S_AXI_WSTRB;
    assign write_data_o     = S_AXI_WDATA;
    assign read_o           = slv_reg_rden;
    assign read_address_o   = axi_araddr;
    
    // Implement axi_awready generation
    // axi_awready is asserted for one S_AXI_ACLK clock cycle when both
    // S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_awready is
    // de-asserted when reset is low.
    
    always @(posedge S_AXI_ACLK)
      begin
         if (S_AXI_ARESETN == 1'b0)
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
    
    always @(posedge S_AXI_ACLK)
      begin
         if (S_AXI_ARESETN == 1'b0)
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
    
    always @(posedge S_AXI_ACLK)
      begin
         if (S_AXI_ARESETN == 1'b0)
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
    
    // Implement write response logic generation
    // The write response and response valid signals are asserted by the slave
    // when axi_wready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted.
    // This marks the acceptance of address and indicates the status of
    // write transaction.
    
    always @(posedge S_AXI_ACLK)
      begin
         if (S_AXI_ARESETN == 1'b0)
           begin
              axi_bvalid <= 0;
              axi_bresp  <= 2'b0;
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
    
    always @(posedge S_AXI_ACLK)
      begin
         if (S_AXI_ARESETN == 1'b0)
           begin
              axi_arready <= 1'b0;
              axi_araddr  <= '0;
           end
         else
           begin
              if (~axi_arready && S_AXI_ARVALID)
                begin
                   // indicates that the slave has acceped the valid read address
                   axi_arready <= 1'b1;
                   // Read address latching
                   axi_araddr <= S_AXI_ARADDR;
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
    always @(posedge S_AXI_ACLK) begin
       if (S_AXI_ARESETN == 1'b0) begin
          axi_rvalid <= 0;
          axi_rresp  <= 0;
       end
       else begin
          if (axi_arready && S_AXI_ARVALID && ~axi_rvalid) begin
             // Valid read data is available at the read data bus
             axi_rvalid <= 1'b1;
             axi_rresp  <= 2'b0; // 'OKAY' response
          end
          else
            if (axi_rvalid && S_AXI_RREADY) begin
               // Read data is accepted by the master
               axi_rvalid <= 1'b0;
            end
       end
    end
       
endmodule

module pulse_extender #(
    parameter Width = 8
    ) (
    output logic                pulse_extend_o,
    input  logic                pulse_i,
    input  logic [Width-1:0]    duration_i,
    input  wire                 clk,
    input  wire                 rst_n
    );

    logic [Width-1:0]       count;
    logic [Width-1:0]       duration;
    logic                   active;
    logic                   trigger_condition;
   
    assign trigger_condition = pulse_i && duration_i != '0;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            count    <= '0;
            duration <= '0;
            active   <= '0;
        end
        else begin
            count   <=  trigger_condition   ? 'b1         :
                        active              ? count + 'b1 : count;
            duration<=  trigger_condition   ? duration_i  : duration;
            active  <=  trigger_condition || (active && count != duration);
        end
    end
    
    assign pulse_extend_o = active;

endmodule
