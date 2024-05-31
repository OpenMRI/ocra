
`timescale 1 ns / 1 ps

module axi_lite_master_core #
(
    parameter integer AXI_DATA_WIDTH = 32,
    parameter integer AXI_ADDR_WIDTH = 32
)
(
    // System signals
    input wire 			                    aclk,
    input wire 			                    aresetn,
      		       
    // Master side
    // Write - Address
    output wire  [AXI_ADDR_WIDTH-1 : 0]     M_AXI_AWADDR,
    output wire  [2 : 0]                    M_AXI_AWPROT,
    output wire                             M_AXI_AWVALID,
    input  wire                             M_AXI_AWREADY,
    // Write - Data
    output wire  [AXI_DATA_WIDTH-1 : 0]     M_AXI_WDATA,
    output wire  [(AXI_DATA_WIDTH/8)-1 : 0] M_AXI_WSTRB,
    output wire                             M_AXI_WVALID,
    input  wire                             M_AXI_WREADY,
    // Write - Response
    input  wire  [1 : 0]                    M_AXI_BRESP,
    input  wire                             M_AXI_BVALID,
    output wire                             M_AXI_BREADY,
    // Read - Address
    output wire  [AXI_ADDR_WIDTH-1 : 0]     M_AXI_ARADDR,
    output wire  [2 : 0]                    M_AXI_ARPROT,
    output wire                             M_AXI_ARVALID,
    input  wire                             M_AXI_ARREADY,
    // Read - Data
    input  wire  [AXI_DATA_WIDTH-1 : 0]     M_AXI_RDATA,
    input  wire  [1 : 0]                    M_AXI_RRESP,
    input  wire                             M_AXI_RVALID,
    output wire                             M_AXI_RREADY,

    //
    input  wire  [AXI_DATA_WIDTH-1 : 0]     wdata_i,
    input  wire  [AXI_ADDR_WIDTH-1 : 0]     waddr_i,
    input  wire  [(AXI_DATA_WIDTH/8)-1 : 0] wstrb_i,
    input  wire                             write_i,
    output wire                             busy_o,
    output wire                             write_failure_o
);

    typedef enum logic [1:0] {
        Idle, Handshake, WriteResponse
    } state_e;

    state_e state_q, state_d;

    // handshake_*_q means "handshake has occured sometime in the past"
    // handshake_* means "handshake is happening in this clock cycle"
    logic   handshake_addr_q, handshake_addr_d, handshake_addr;
    logic   handshake_data_q, handshake_data_d, handshake_data;
    logic   handshake_resp_q, handshake_resp_d, handshake_resp;

    logic   [AXI_DATA_WIDTH-1 : 0]      wdata_q, wdata_d;
    logic   [AXI_ADDR_WIDTH-1 : 0]      waddr_q, waddr_d;
    logic   [(AXI_DATA_WIDTH/8)-1 : 0]  wstrb_q, wstrb_d;
    logic                               addr_valid_q, addr_valid_d;
    logic                               data_valid_q, data_valid_d;
    logic                               resp_ready_q, resp_ready_d;
    logic                               write_failure_q, write_failure_d;

    //
    assign  handshake_addr  = addr_valid_q && M_AXI_AWREADY;
    assign  handshake_data  = data_valid_q && M_AXI_WREADY;
    assign  handshake_resp  = resp_ready_q && M_AXI_BVALID;

    assign  write_failure_d = (write_i && state_q != Idle) || (state_q == WriteResponse && M_AXI_BVALID && M_AXI_BRESP[1] == 1'b1);

    always_comb begin
        state_d             = state_q;
        handshake_addr_d    = handshake_addr_q;
        handshake_data_d    = handshake_data_q;
        wdata_d             = wdata_q;
        waddr_d             = waddr_q;
        wstrb_d             = wstrb_q;
        addr_valid_d        = addr_valid_q;
        data_valid_d        = data_valid_q;
        resp_ready_d        = resp_ready_q;
        case (state_q)
            //Idle
            Idle: begin
                if (write_i) begin
                    state_d          = Handshake;
                    handshake_addr_d = 'b0;
                    handshake_data_d = 'b0;
                    wdata_d          = wdata_i;
                    waddr_d          = waddr_i;
                    wstrb_d          = wstrb_i;
                    addr_valid_d     = 'b1;
                    data_valid_d     = 'b1;
                    resp_ready_d     = 'b0;
                end
            end

            //Handshake
            Handshake: begin
                if ((handshake_addr || handshake_addr_q) && (handshake_data || handshake_data_q)) begin
                    state_d          = WriteResponse;
                    handshake_addr_d = 'b0;
                    handshake_data_d = 'b0;
                    addr_valid_d     = 'b0;
                    data_valid_d     = 'b0;
                    resp_ready_d     = 'b1;
                end
                else begin
                    handshake_addr_d = handshake_addr_q || handshake_addr;
                    handshake_data_d = handshake_data_q || handshake_data;
                    addr_valid_d     = !(handshake_addr_q || handshake_addr);
                    data_valid_d     = !(handshake_data_q || handshake_data);
                end
            end

            WriteResponse: begin
                if (handshake_resp) begin
                    state_d          = Idle;
                    resp_ready_d     = 'b0;
                end
            end

            default: begin
                state_d              = Idle;
                handshake_addr_d     = 'b0;
                handshake_data_d     = 'b0;
                wdata_d              = 'b0;
                waddr_d              = 'b0;
                wstrb_d              = 'b0;
                addr_valid_d         = 'b0;
                data_valid_d         = 'b0;
                resp_ready_d         = 'b0;
            end
        endcase
    end

    always_ff @(posedge aclk) begin
        if(!aresetn) begin
            state_q             <= Idle;
            handshake_addr_q    <= 'b0;
            handshake_data_q    <= 'b0;
            wdata_q             <= 'b0;
            waddr_q             <= 'b0;
            wstrb_q             <= 'b0;
            addr_valid_q        <= 'b0;
            data_valid_q        <= 'b0;
            resp_ready_q        <= 'b0;
            write_failure_q     <= 'b0;
        end
        else begin
            state_q             <= state_d;
            handshake_addr_q    <= handshake_addr_d;
            handshake_data_q    <= handshake_data_d;
            wdata_q             <= wdata_d;
            waddr_q             <= waddr_d;
            wstrb_q             <= wstrb_d;
            addr_valid_q        <= addr_valid_d;
            data_valid_q        <= data_valid_d;
            resp_ready_q        <= resp_ready_d;
            write_failure_q     <= write_failure_d;
        end
    end

    //Output Assignment
    // Write - Address
    assign M_AXI_AWADDR    = waddr_q;
    assign M_AXI_AWPROT    = 'b0;
    assign M_AXI_AWVALID   = addr_valid_q;
    // Write - Data
    assign M_AXI_WDATA     = wdata_q;
    assign M_AXI_WSTRB     = wstrb_q;
    assign M_AXI_WVALID    = data_valid_q;
    // Write - Response
    assign M_AXI_BREADY    = resp_ready_q;
    // Read - Address
    assign M_AXI_ARADDR    = 'b0;
    assign M_AXI_ARPROT    = 'b0;
    assign M_AXI_ARVALID   = 'b0;
    // Read - Data
    assign M_AXI_RREADY    = 'b0;
    //
    assign busy_o          = state_q != Idle;
    assign write_failure_o = write_failure_q;

endmodule
