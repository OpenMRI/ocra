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
//      - Assumptions:
//
//      - Limitations:
//////////////////////////////////////////////////////////////////////////////////

    // C0 register name
`define PC C0R[0]   // Program Counter
`define EPC C0R[1]  // exception PC value
`define PCD C0R_d[0]   // Program Counter
`define EPCD C0R_d[1]  // exception PC value
  
module micro_sequencer_core #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 16,
    parameter integer C_M_AXI_ADDR_WIDTH = 32,
    parameter integer BRAM_DATA_WIDTH = 64,
    parameter integer BRAM_ADDR_WIDTH = 10,
    parameter integer C_M_AXI_ADDR_OFFSET = 32'h4000_0000,
    parameter integer ADDRESS_LUT_DEPTH = 256   //Maximum of 256 entries
    ) (
    output wire                                 bram_porta_clk,
    output wire                                 bram_porta_rst,
    output wire [BRAM_ADDR_WIDTH-1:0]           bram_porta_addr_o,
    input  wire [BRAM_DATA_WIDTH-1:0]           bram_porta_rddata_i,

    output logic  [15:0]                        tx_offset_o,
    output logic  [15:0]                        grad_offset_o,
    output logic  [31:0]                        phase_offset_o,
    output logic  [63:0]                        pulse_o,
    output logic                                timer_enable_o,

    output logic                                interrupt_start_o,
    output logic                                interrupt_end_o,
    output logic                                interrupt_error_o,
    output logic                                interrupt_paused_o,
    output logic  [7:0]                         error_code_o,
    output logic                                current_buffer_o,

    output logic  [1:0]                         raster_clk_rstn_o,

    output logic  [C_S_AXI_DATA_WIDTH-1:0]      axi_wdata_o,
    output logic  [C_M_AXI_ADDR_WIDTH-1:0]      axi_waddr_o,
    output logic  [3:0]                         axi_wstrb_o,
    output logic                                axi_write_o,
    input  logic                                axi_write_busy_i,
    input  logic                                axi_write_failed_i,
    input  logic  [C_S_AXI_ADDR_WIDTH-1:0]      int_lut_data_i,
    input  logic  [$clog2(ADDRESS_LUT_DEPTH)-1:0]int_lut_addr_i,
    input  logic                                int_lut_write_i,

    input  logic                                start_i,            //Sequence State Control -> 111
    input  logic                                stop_i,             //Sequence State Control -> 000
    input  logic                                double_buffer_i,    //Double Buffering Mode
    input  logic                                abort_seq_i,        //Request to abort as soon as the current sequence block is completed
    input  logic                                buffer_ready_i,     //Next Buffer is Ready
    input  logic  [BRAM_ADDR_WIDTH-1:0]         mem_addr_offset_i,  //Address Offset on Double Buffering Mode
    input  logic                                ms_ext_tr_trigger_i,//Clock Trigger for Double Buffer Transition

    input  logic                                unpause_strobe_i,   //Unpause

    //Status Register for Debug
    output logic  [16-1:0]                      current_bram_addr_o,
    output logic  [8-1:0]                       current_state_o,
    output logic  [8-1:0]                       current_opcode_o,

    //Output
    output logic                                active_state_o,

    input wire                                  clk,
    input wire                                  rst_n
    );

    // Instruction Opcodes for PCP0 are only 6 bit
    parameter [5:0]
    
      DEC =         6'b000001,  // decrement value of register by one
      INC =         6'b000010,  // increment value of regiuster by one
      LITR =        6'b000011,  // "Last Instruction in TR"
      LD64 =        6'b000100,  // load 64 bit value to register
      RASTCSYNC =   6'b000101,  // Resets the Raster Clock
      TMR =         6'b000110,  // Timer Enable Bit
      TXOFFSET =    6'b001000,  // set the txoffset to a 16 bit value in formatA
      GRADOFFSET =  6'b001001,  // set the gradoffset to a 16 bit value in formatA
      AXIWRITE =    6'b001010,  // perform write through the axi-master interface
      PHASEOFFSET=  6'b001011,  // apply a phase offset to the NCO
      JNZ =         6'b010000,  // jump to immeduate address of register is nonzero
      BTR =         6'b010100,  // branch to immediate address if triggered
      J =           6'b010111,  // jump to immediate address
      PAUSE =       6'b011000,  // wait until unpause strobe arrives
      NOP =         6'b011010,  // do nothing for some amount of time
      HALT =        6'b011001,  // halt
      PI =          6'b011100,  // pulse lower 32 bit immediately with up to 23 bit delay
      PR =          6'b011101;  // pulse 64 bit register with up to 40 bit delay
    
    typedef enum logic [7:0] {
      Valid         = 'h0,      // Safe transition to Halted state based on instruction
      InvalidOpcode = 'h1,      // Invalid Opcode
      InvalidState  = 'h2,      // Invalid/Unhandled State
      BufferNotReady= 'h3,      // Buffer Not Ready in time for safe buffer transition
      BufferDisabled= 'h4,      // No buffer transition as Double Buffering is disabled
      AxiWriteBusy  = 'h5,      // Attempting to write before the completion of the previous transaction
      AxiWriteFailed= 'h6,      // Axi Write Failure detected
      AbortSequence = 'h7       // Abort Micro Sequencer
    } error_code_e;

    localparam NumOfRegister = 32;
    localparam NumOfC0Register = 2;

    typedef enum logic [3:0]{
        Reset, Fetch, Decode, Execute, MemAccess, WriteBack, Stall, Halted, Paused, WaitForFetch, WaitForFetch2, MemAccess2, MemAccess3, WaitForRaster
    } state_e;
     
    logic signed [63:0]             R [0:NumOfRegister-1], R_d [0:NumOfRegister-1];
    logic signed [63:0]             C0R [0:NumOfC0Register-1], C0R_d[0:NumOfC0Register-1]; // co-processor 0 register

    // Microsequencer Operation
    state_e                         state_q, state_d;        // execution FSM state
    // 40 bit stall timer stuff
    logic [39:0]                    stall_timer_counter_q, stall_timer_counter_d;

    // Microsequencer Instructions
    logic [5:0]                     op_q, op_d; // TW, for PCP0 I use 6 bits
    logic [BRAM_ADDR_WIDTH-1:0]     direct_address_q, direct_address_d; // we only have 13 bits deep memory
    logic [39:0]                    delay_constant_q, delay_constant_d;
    logic [4:0]                     formatAa_q, formatBa_q, formatAa_d, formatBa_d;
    logic [63:0]                    result_q, result_d;
    logic [BRAM_ADDR_WIDTH-1:0]     next_PC, next_PC_d;
    logic [63:0]                    opA, opB, opA_d, opB_d;
    logic [BRAM_ADDR_WIDTH-1:0]     int_mem_addr, int_mem_addr_d;

    // Registering Configuration
    logic [BRAM_ADDR_WIDTH-1:0]     mem_addr_offset_q, mem_addr_offset_d;
    logic [BRAM_ADDR_WIDTH-1:0]     mem_addr_offset_sel;
    logic [BRAM_ADDR_WIDTH-1:0]     second_buffer_offset_q, second_buffer_offset_d;
    
    // Microsequencer Output
    logic [15:0]                    tx_offset_q, tx_offset_d;
    logic [15:0]                    grad_offset_q, grad_offset_d;
    logic [31:0]                    phase_offset_2q, phase_offset_q, phase_offset_d;
    logic [63:0]                    pulse_q, pulse_d;
    logic                           timer_enable_q, timer_enable_d;
    // Interrupt
    logic                           interrupt_start;
    logic                           interrupt_end;
    logic                           interrupt_error;
    logic                           interrupt_paused;
    error_code_e                    error_code_q, error_code_d;
    
    // Raster Clock Reset Pulse
    logic [1:0]                     raster_clk_rstn_q, raster_clk_rstn_d;

    // AXI Write
    // AXI Write Internal Addressing LUT
    (* ram_style = "distributed" *) logic [C_S_AXI_ADDR_WIDTH-1:0]  mem_axi_addr [0:ADDRESS_LUT_DEPTH-1];
    logic [$clog2(ADDRESS_LUT_DEPTH)-1:0] int_lut_addr_q, int_lut_addr_d;
    logic [C_S_AXI_DATA_WIDTH-1:0]  axi_wdata_q, axi_wdata_d;
    logic [C_M_AXI_ADDR_WIDTH-1:0]  axi_waddr_q;
    logic [3:0]                     axi_wstrb_q, axi_wstrb_d;
    logic                           axi_write_q, axi_write_d;

    //
    logic                           active_state_q, active_state_d;

    // Debugging
    logic signed [31:0]             pc0;
    logic [63:0] 				    cycles;

    integer i,j,m,n;
    logic                           start_buffer;
    logic                           start_new_seq;
    logic                           next_buffer_q, next_buffer_d;
    logic                           current_buffer_q, current_buffer_d;

    // assign the memory interface outputs
    assign bram_porta_addr_o    = int_mem_addr;
    assign bram_porta_clk       = clk;
    assign bram_porta_rst       = '0;
    // assign microsequencer output
    assign tx_offset_o          = tx_offset_q;
    assign grad_offset_o        = grad_offset_q;
    assign phase_offset_o       = phase_offset_2q;
    assign pulse_o              = pulse_q;
    assign timer_enable_o       = timer_enable_q;
    // assign interrupt output
    assign interrupt_start_o    = interrupt_start;
    assign interrupt_end_o      = interrupt_end;
    assign interrupt_error_o    = interrupt_error;
    assign interrupt_paused_o   = interrupt_paused;
    assign error_code_o         = error_code_q;
    // raster clock reset
    assign raster_clk_rstn_o    = raster_clk_rstn_q;
    // current buffer
    assign current_buffer_o     = current_buffer_q;
    // debug
    assign current_bram_addr_o  = {{(16-BRAM_ADDR_WIDTH){1'b0}}, bram_porta_addr_o};
    assign current_state_o      = {4'b0, state_q};
    assign current_opcode_o     = {2'b0, op_q};
    assign active_state_o       = active_state_q;

    // ====================================================================
    //
    // Add user logic here
    //
    // ====================================================================
    //Start new sequence when software triggers it, or if the next buffer is ready
    assign start_new_seq = (state_q == Reset && start_i) || start_buffer;
    assign mem_addr_offset_sel = (next_buffer_q == 'b1) ? second_buffer_offset_q : '0;
    assign active_state_d = !(state_q == Reset || state_q == Halted);

    // Register Assignment
    always_ff @(posedge clk) begin
        if(!rst_n) begin
            for (i=0; i<NumOfRegister; i=i+1)
                R[i] <= 0;
            for (j=0; j<NumOfC0Register; j=j+1)
                C0R[j] <= 0;
        end
        else begin
            for (i=0; i<NumOfRegister; i=i+1)
                R[i] <= R_d[i];
            for (j=0; j<NumOfC0Register; j=j+1)
                C0R[j] <= C0R_d[j];
        end
    end

    // AXI Address Translation
    // Write
    always_ff @(posedge clk) begin
        if (int_lut_write_i)
            mem_axi_addr[int_lut_addr_i] <= int_lut_data_i;
    end
    // Read
    always_ff @(posedge clk) begin
        axi_waddr_q <= C_M_AXI_ADDR_OFFSET + mem_axi_addr[int_lut_addr_q];
    end

    // Microsequencer Operation
    always_ff @(posedge clk) begin
        if(!rst_n) begin
            state_q                 <= Reset;
            stall_timer_counter_q   <= '1;
            op_q                    <= NOP;
            direct_address_q        <= '0;
            delay_constant_q        <= '0;
            formatAa_q              <= '0;
            formatBa_q              <= '0;
            result_q                <= '0;
            next_PC                 <= '0;
            opA                     <= '0;
            opB                     <= '0;
            int_mem_addr            <= '0;
            mem_addr_offset_q       <= '0;
            second_buffer_offset_q  <= '0;
            current_buffer_q        <= '0;
            int_lut_addr_q          <= '0;
            axi_wdata_q             <= '0;
            axi_wstrb_q             <= '0;
            axi_write_q             <= '0;
            active_state_q          <= '0;
        end
        else begin
            state_q                 <= state_d;
            stall_timer_counter_q   <= stall_timer_counter_d;
            op_q                    <= op_d;
            direct_address_q        <= direct_address_d;
            delay_constant_q        <= delay_constant_d;
            formatAa_q              <= formatAa_d;
            formatBa_q              <= formatBa_d;
            result_q                <= result_d;
            next_PC                 <= next_PC_d;
            opA                     <= opA_d;
            opB                     <= opB_d;
            int_mem_addr            <= int_mem_addr_d;
            mem_addr_offset_q       <= mem_addr_offset_d;
            second_buffer_offset_q  <= second_buffer_offset_d;
            current_buffer_q        <= current_buffer_d;
            int_lut_addr_q          <= int_lut_addr_d;
            axi_wdata_q             <= axi_wdata_d;
            axi_wstrb_q             <= axi_wstrb_d;
            axi_write_q             <= axi_write_d;
            active_state_q          <= active_state_d;
        end
    end

    // Output and Interrupt Pulses
    always_ff @(posedge clk) begin
        if(!rst_n) begin
            tx_offset_q             <= '0;
            grad_offset_q           <= '0;
            phase_offset_q          <= '0;
            phase_offset_2q         <= '0;
            pulse_q                 <= 'hFF00;
            timer_enable_q          <= '0;
            interrupt_start         <= '0;
            interrupt_end           <= '0;
            interrupt_error         <= '0;
            interrupt_paused        <= '0;
            error_code_q            <= Valid;
            raster_clk_rstn_q       <= '1;
            next_buffer_q           <= '0;
        end
        else begin
            tx_offset_q             <= tx_offset_d;
            grad_offset_q           <= grad_offset_d;
            phase_offset_q          <= phase_offset_d;
            phase_offset_2q         <= phase_offset_q;
            pulse_q                 <= pulse_d;
            timer_enable_q          <= timer_enable_d;
            interrupt_start         <= start_new_seq;
            interrupt_end           <= state_q == Execute && op_q == LITR && !abort_seq_i;
            interrupt_error         <= state_d == Halted && state_q != Halted;
            interrupt_paused        <= state_d == Paused && state_q != Paused;
            error_code_q            <= error_code_d;
            raster_clk_rstn_q       <= raster_clk_rstn_d;
            next_buffer_q           <= next_buffer_d;
        end
    end
    assign axi_wdata_o = axi_wdata_q;
    assign axi_waddr_o = axi_waddr_q;
    assign axi_wstrb_o = axi_wstrb_q;
    assign axi_write_o = axi_write_q;

    //Debug
    always_ff @(posedge clk) begin
        if(!rst_n) begin
            pc0                     <= '0;
        end
        else begin
            pc0                     <= `PC[31:0];
        end
    end

    //state and sequence assignments
    always_comb begin
        // Default Assignment
        for (m=0; m<NumOfRegister; m=m+1)
            R_d[m] = R[m];
        for (n=0; n<NumOfC0Register; n=n+1)
            C0R_d[n] = C0R[n];
        state_d                 = state_q;
        stall_timer_counter_d   = stall_timer_counter_q;
        op_d                    = op_q;
        direct_address_d        = direct_address_q;
        delay_constant_d        = delay_constant_q;
        formatAa_d              = formatAa_q;
        formatBa_d              = formatBa_q;
        result_d                = result_q;
        next_PC_d               = next_PC;
        opA_d                   = opA;
        opB_d                   = opB;
        int_mem_addr_d          = int_mem_addr;
        mem_addr_offset_d       = mem_addr_offset_q;
        tx_offset_d             = tx_offset_q;
        grad_offset_d           = grad_offset_q;
        phase_offset_d          = phase_offset_q;
        pulse_d                 = pulse_q;
        timer_enable_d          = timer_enable_q;
        error_code_d            = error_code_q;
        raster_clk_rstn_d       = raster_clk_rstn_q;
        start_buffer            = 1'b0;
        next_buffer_d           = next_buffer_q;
        second_buffer_offset_d  = second_buffer_offset_q;
        current_buffer_d        = current_buffer_q;
        int_lut_addr_d          = int_lut_addr_q;
        axi_wdata_d             = axi_wdata_q;
        axi_wstrb_d             = axi_wstrb_q;
        axi_write_d             = 1'b0;

        // Software is directing microsequencer to stop. This overrides the state machine back to Reset state.
        if (stop_i) begin
            state_d             = Reset;
            tx_offset_d         = '0;
            grad_offset_d       = '0;
            phase_offset_d      = '0;
            pulse_d             = 64'hFF00;
            timer_enable_d      = '0;
            next_buffer_d       = '0;
            current_buffer_d    = '0;
        end
        //AXI Write Failure
        else if (start_i && axi_write_failed_i) begin
            state_d             = Halted;
            error_code_d        = AxiWriteFailed;
        end
        // Microsequencer State Machine
        else begin
            case (state_q)
                //Reset State is added in place of the older inExe logic
                Reset: begin
                    tx_offset_d         = '0;
                    grad_offset_d       = '0;
                    pulse_d             = 64'hFF00;
                    raster_clk_rstn_d   = '1;
                    timer_enable_d      = '0;
                    next_buffer_d       = 'b0;
                    if (start_i) begin
                        state_d    = Fetch;
                        `PCD       = '0;
                        mem_addr_offset_d       = double_buffer_i ? mem_addr_offset_sel : '0;
                        next_buffer_d           = double_buffer_i ? ~next_buffer_q : 'b0;
                        second_buffer_offset_d  = double_buffer_i ? mem_addr_offset_i : '0;
                        current_buffer_d        = double_buffer_i ? next_buffer_q : 'b0;
                        error_code_d = Valid;
                        pulse_d      = 64'h0000;
                    end
                    else
                        state_d    = Reset;
                end

                Fetch: begin // Tick 1 : instruction fetch, throw PC to address bus,
                    //$display("%4dns %8x : Fetching 64 bits ", $stime, `PC);
                    int_mem_addr_d      = `PC[BRAM_ADDR_WIDTH-1:0] + mem_addr_offset_q; //PC relative to absolute address translation is applied here
                    next_PC_d           = `PC[BRAM_ADDR_WIDTH-1:0] + 1;
                    state_d             = WaitForFetch;
                end
                
                WaitForFetch: begin
                    state_d             = MemAccess3;
                end
                
                MemAccess3: begin
                    state_d             = WaitForFetch2;
                end
                
                WaitForFetch2: begin
                    state_d             = Decode;
                    op_d                = bram_porta_rddata_i[63:58]; // pcp0 opcode is ALWAYS top 6 bits
                    direct_address_d    = bram_porta_rddata_i[BRAM_ADDR_WIDTH-1:0]; // format A direct address
                    delay_constant_d    = bram_porta_rddata_i[39:0]; // 40 bit constant for format B
                    formatAa_d          = bram_porta_rddata_i[36:32];     // register address for format A
                    formatBa_d          = bram_porta_rddata_i[44:40];     // register address for format B
                    int_lut_addr_d      = bram_porta_rddata_i[40+:$clog2(ADDRESS_LUT_DEPTH)];
                    axi_wdata_d         = bram_porta_rddata_i[31:0];
                    axi_wstrb_d         = bram_porta_rddata_i[35:32];
                end
                
                Decode: begin // Tick 2 : instruction decode, ir = m[PC]
                    state_d             = Execute;
                    opA_d               = R[formatAa_q];
                    opB_d               = R[formatBa_q];
                end
                
                Execute: begin // Tick 3 : instruction execution
                    //$display("%4dns %8x : Executing op code %6b", $stime, pc0, op_q);
                    case (op_q)
                        NOP: begin
                            state_d           = Stall;
                            stall_timer_counter_d = delay_constant_q;
                        end
                        DEC: begin
                            result_d          = opA - 64'b1;
                            state_d           = MemAccess;
                        end
                        INC: begin
                            result_d          = opA + 64'b1;
                            state_d           = MemAccess;
                        end
                        LITR: begin
                            if (abort_seq_i) begin
                                state_d       = Halted;
                                error_code_d  = AbortSequence;
                            end
                            else begin
                                stall_timer_counter_d = delay_constant_q;
                                state_d           = Stall;
                            end
                        end
                        LD64: begin
                            //memReadStart(directAddress, `QUAD); // LD Ra,directAddress; Ra <= [directAddress]
                            int_mem_addr_d    = direct_address_q + mem_addr_offset_q;
                            state_d           = MemAccess;
                        end
                        RASTCSYNC: begin
                            raster_clk_rstn_d = ~delay_constant_q[1:0];
                            state_d	          = MemAccess;
                        end
                        TMR: begin
                            result_d[0]       = delay_constant_q[0];
                            state_d           = MemAccess;
                        end
                        TXOFFSET: begin
                            result_d[15:0]    = delay_constant_q[15:0];
                            state_d           = MemAccess;
                        end
                        GRADOFFSET: begin
                            result_d[15:0]    = delay_constant_q[15:0];
                            state_d           = MemAccess;
                        end
                        AXIWRITE: begin
                            if (axi_write_busy_i) begin
                                state_d       = Halted;
                                error_code_d  = AxiWriteBusy;
                            end
                            else begin
                                state_d       = MemAccess;
                                axi_write_d   = 1'b1;
                            end
                        end
                        PHASEOFFSET: begin
                            result_d[31:0]    = {2'b00, delay_constant_q[29:0]};
                            state_d           = MemAccess;
                        end
                        JNZ: begin
                            if (opA != 64'h0) begin
                                result_d[BRAM_ADDR_WIDTH-1:0] = direct_address_q;
                            end
                            else begin
                                result_d[BRAM_ADDR_WIDTH-1:0] = next_PC;
                            end
                            state_d           = MemAccess;
                        end
                        BTR: begin
                            // Reserved for future improvement. For now, this should behave like NOP
                            state_d           = MemAccess;
                        end
                        J: begin
                            result_d[BRAM_ADDR_WIDTH-1:0] = direct_address_q; // J directAddress
                            state_d           = MemAccess;
                        end
                        PAUSE: begin
                            state_d           = Paused;
                        end
                        HALT: begin
                            //pulse[15:8] <= `PC;
                            state_d           = Halted;
                            error_code_d      = Valid;
                        end // when the HALT command is encountered, end the simulation, needs to be modified later
                        PI: begin
                            state_d           = MemAccess;
                        end
                        PR: begin
                            pulse_d           = opB; //R[formatBa];
                            stall_timer_counter_d = delay_constant_q;
                            state_d           = Stall;
                        end
                        default: begin
                            //Unknown Opcode. Proceed to Halted
                            state_d           = Halted;
                            error_code_d      = InvalidOpcode;
                            //$display("%4dns %8x : OP code %8x not support", $stime, pc0, op_q);
                        end
                    endcase                   
                end // end Execute

                Paused: begin
                    if (unpause_strobe_i) begin
                        state_d = MemAccess;
                        error_code_d = Valid;
                    end
                end
                
                Stall: begin
                    if (stall_timer_counter_q == '0) begin
                        // On LITR, wait for the raster clock pulse
                        if (op_q == LITR) begin
                            state_d         = WaitForRaster;
                        end
                        else
                            state_d         = MemAccess;
                    end
                    //Continue Stalling
                    else begin
                        stall_timer_counter_d = stall_timer_counter_q - 1;
                        state_d         = Stall;
                    end
                end // end Stall
                
                WaitForRaster: begin
                    if (ms_ext_tr_trigger_i) begin
                        // Double Buffer Transition
                        if (double_buffer_i && buffer_ready_i) begin
                            state_d         = Fetch;
                            `PCD            = '0;
                            mem_addr_offset_d = mem_addr_offset_sel;
                            next_buffer_d   = ~next_buffer_q;
                            current_buffer_d= next_buffer_q;
                            error_code_d    = Valid;
                            start_buffer    = 1'b1;
                        end
                        // Double Buffering conditions are not met
                        // Micro Sequencer halts with error message
                        else begin
                            state_d         = Halted;
                            if (double_buffer_i && ~buffer_ready_i)
                                error_code_d    = BufferNotReady;
                            else
                                error_code_d    = BufferDisabled;
                        end
                    end
                    else begin
                        state_d = WaitForRaster;
                    end
                end

                Halted: begin
                    state_d = Halted;
                end // end Halted
                
                MemAccess: begin
                   // we have to wait for the memory again here, because its registered
                   //case (op)
                   //ST, SB, SH : memWriteEnd(); // write memory complete
                   //endcase
                    state_d    = MemAccess2;
                    `PCD       = {{(64-BRAM_ADDR_WIDTH){1'b0}}, next_PC};
                end
                
                MemAccess2: begin
                    state_d    = WriteBack;
                end
                
                WriteBack: begin // Read/Write finish, close memory
                    state_d = Fetch;
                    case (op_d)
                        LD64 : begin
                            R_d[formatAa_q] = bram_porta_rddata_i;
                        end
                        TXOFFSET: begin
                            tx_offset_d   = result_q[15:0];
                        end
                        GRADOFFSET: begin
                            grad_offset_d = result_q[15:0];
                        end
                        PHASEOFFSET: begin
                            phase_offset_d = result_q[31:0];
                        end
                        DEC: begin
                            R_d[formatAa_q] = result_q;
                        end
                        INC: begin
                            R_d[formatAa_q] = result_q;
                        end
                        TMR: begin
                            timer_enable_d = result_q[0]; 
                        end
                        JNZ: begin
                            `PCD          = {{(64-BRAM_ADDR_WIDTH){1'b0}}, result_q[BRAM_ADDR_WIDTH-1:0]};
                        end
                        J: begin
                            `PCD          = {{(64-BRAM_ADDR_WIDTH){1'b0}}, result_q[BRAM_ADDR_WIDTH-1:0]};
                        end
                        default:;
                    endcase // case (op)
                    raster_clk_rstn_d = '1;
                end // WriteBack:

                default: begin
                    state_d       = Halted;
                    error_code_d  = InvalidState;
                end
            endcase
        end
    end

endmodule
