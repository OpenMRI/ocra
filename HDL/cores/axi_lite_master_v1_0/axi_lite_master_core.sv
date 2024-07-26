
`timescale 1 ns / 1 ps

module axi_lite_master_core #
(
    parameter integer AXI_DATA_WIDTH = 32,
    parameter integer AXI_ADDR_WIDTH = 32,
    parameter integer FIFO_DEPTH = 16
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
    output wire                             full_o,
    output wire                             write_failure_o,
    output wire                             timeout_failure_o
);
    localparam FIFO_WIDTH = AXI_DATA_WIDTH+AXI_ADDR_WIDTH+(AXI_DATA_WIDTH/8);

    typedef enum logic [2:0] {
        Idle, Pop, Handshake, WriteResponse, TimeOut
    } state_e;

    state_e state_q, state_d;

    // handshake_*_q means "handshake has occured sometime in the past"
    // handshake_* means "handshake is happening in this clock cycle"
    logic   handshake_addr_q, handshake_addr_d, handshake_addr;
    logic   handshake_data_q, handshake_data_d, handshake_data;
    logic   handshake_resp;

    logic   [AXI_DATA_WIDTH-1 : 0]      wdata_q, wdata_d, rdata_fifo;
    logic   [AXI_ADDR_WIDTH-1 : 0]      waddr_q, waddr_d, raddr_fifo;
    logic   [(AXI_DATA_WIDTH/8)-1 : 0]  wstrb_q, wstrb_d, rstrb_fifo;
    logic                               addr_valid_q, addr_valid_d;
    logic                               data_valid_q, data_valid_d;
    logic                               resp_ready_q, resp_ready_d;
    
    // Failures
    logic                               timeout_failure_q, timeout_failure_d;
    logic                               bresp_failure_q, bresp_failure_d;
    logic [9:0]                         timeout_counter_q, timeout_counter_d;

    // FIFO
    logic   pop, fifo_empty, fifo_full, reset_fifo;

    // FIFO Instance
    fifo #(
        .DEPTH              (FIFO_DEPTH),
        .WIDTH              (FIFO_WIDTH)
    ) inst_fifo (
        .aclk               (aclk),
        .resetn             (aresetn && !reset_fifo),
        .wdata_i            ({wdata_i, waddr_i, wstrb_i}),
        .write_i            (write_i),
        .read_i             (pop),
        .rdata_o            ({rdata_fifo, raddr_fifo, rstrb_fifo}),
        .empty_o            (fifo_empty),
        .full_o             (fifo_full)
    );

    //
    assign  handshake_addr  = addr_valid_q && M_AXI_AWREADY;
    assign  handshake_data  = data_valid_q && M_AXI_WREADY;
    assign  handshake_resp  = resp_ready_q && M_AXI_BVALID;

    assign  timeout_failure_d = state_q == TimeOut;
    assign  bresp_failure_d   = state_q == WriteResponse && M_AXI_BVALID && M_AXI_BRESP[1] == 1'b1;
    assign  reset_fifo        = state_q == TimeOut;

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
        timeout_counter_d   = timeout_counter_q;
        pop                 = 'b0;
        case (state_q)
            //Idle
            Idle: begin
                handshake_addr_d = 'b0;
                handshake_data_d = 'b0;
                wdata_d          = 'b0;
                waddr_d          = 'b0;
                wstrb_d          = 'b0;
                addr_valid_d     = 'b0;
                data_valid_d     = 'b0;
                resp_ready_d     = 'b0;
                timeout_counter_d= 'b0;
                if (!fifo_empty) begin
                    state_d          = Pop;
                    pop              = 'b1;
                end
            end

            //Pop
            Pop: begin
                state_d          = Handshake;
                handshake_addr_d = 'b0;
                handshake_data_d = 'b0;
                wdata_d          = rdata_fifo;
                waddr_d          = raddr_fifo;
                wstrb_d          = rstrb_fifo;
                addr_valid_d     = 'b1;
                data_valid_d     = 'b1;
                resp_ready_d     = 'b0;
            end

            //Handshake
            Handshake: begin
                timeout_counter_d = timeout_counter_q + 1;
                if ((handshake_addr || handshake_addr_q) && (handshake_data || handshake_data_q)) begin
                    state_d          = WriteResponse;
                    handshake_addr_d = 'b0;
                    handshake_data_d = 'b0;
                    addr_valid_d     = 'b0;
                    data_valid_d     = 'b0;
                    resp_ready_d     = 'b1;
                    timeout_counter_d= 'b0;
                end
                else if (timeout_counter_q == '1) begin
                    state_d          = TimeOut;
                end
                else begin
                    handshake_addr_d = handshake_addr_q || handshake_addr;
                    handshake_data_d = handshake_data_q || handshake_data;
                    addr_valid_d     = !(handshake_addr_q || handshake_addr);
                    data_valid_d     = !(handshake_data_q || handshake_data);
                end
            end

            //Write Response
            WriteResponse: begin
                timeout_counter_d = timeout_counter_q + 1;
                if (handshake_resp) begin
                    state_d          = Idle;
                    resp_ready_d     = 'b0;
                end
                else if (timeout_counter_q == '1) begin
                    state_d          = TimeOut;
                end
            end

            //TimeOut
            TimeOut: begin
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
            timeout_counter_q   <= 0;
            bresp_failure_q     <= 'b0;
            timeout_failure_q   <= 'b0;
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
            timeout_counter_q   <= timeout_counter_d;
            bresp_failure_q     <= bresp_failure_d;
            timeout_failure_q   <= timeout_failure_d;
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
    assign full_o          = fifo_full;
    assign write_failure_o = bresp_failure_q;
    assign timeout_failure_o= timeout_failure_q;

endmodule
