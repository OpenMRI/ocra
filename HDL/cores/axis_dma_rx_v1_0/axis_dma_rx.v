`timescale 1ns / 1ps
module axis_dma_rx #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 16,
    parameter integer C_AXIS_TDATA_WIDTH = 64,
    parameter EXTERNAL_FRAMING_LOGIC = 0
)
(
    input wire                                   aclk,
    input wire                                   aresetn,

    //Received Stream
    input       [C_AXIS_TDATA_WIDTH-1:0]         s_axis_tdata,
    input                                        s_axis_tvalid,
    output                                       s_axis_tready,

    input                                        gate,
    input       [19:0]                           acq_len_in,
    output                                       acq_len_rd_en,
    input                                        s2mm_err,
    output                                       i_rq,
    output                                       busy,

    //Snooping the BRESP interface
    input       [1:0]                            axi_mm_bresp,
    input                                        axi_mm_bvalid,
    input                                        axi_mm_bready,

    //Data Mover Interfaces
    //Command
    output                                       m_axis_s2mm_cmd_tvalid,
    input                                        m_axis_s2mm_cmd_tready,
    output      [71 : 0]                         m_axis_s2mm_cmd_tdata,
    //Status
    input                                        s_axis_s2mm_sts_tvalid,
    output                                       s_axis_s2mm_sts_tready,
    input       [31: 0]                          s_axis_s2mm_sts_tdata,
    input       [3 : 0]                          s_axis_s2mm_sts_tkeep,
    input                                        s_axis_s2mm_sts_tlast,
    //Output Stream to Memory
    output      [C_AXIS_TDATA_WIDTH-1: 0]        m_axis_s2mm_tdata,
    output      [(C_AXIS_TDATA_WIDTH/8)-1 : 0]   m_axis_s2mm_tkeep,
    output                                       m_axis_s2mm_tlast,
    output                                       m_axis_s2mm_tvalid,
    input                                        m_axis_s2mm_tready,

    //AXI4-Lite Interface
    input       [C_S_AXI_ADDR_WIDTH-1 : 0]       S_AXI_AWADDR,
    input       [2 : 0]                          S_AXI_AWPROT,
    input                                        S_AXI_AWVALID,
    output                                       S_AXI_AWREADY,
    input       [C_S_AXI_DATA_WIDTH-1 : 0]       S_AXI_WDATA,
    input       [(C_S_AXI_DATA_WIDTH/8)-1 : 0]   S_AXI_WSTRB,
    input                                        S_AXI_WVALID,
    output                                       S_AXI_WREADY,
    output      [1 : 0]                          S_AXI_BRESP,
    output                                       S_AXI_BVALID,
    input                                        S_AXI_BREADY,
    input       [C_S_AXI_ADDR_WIDTH-1 : 0]       S_AXI_ARADDR,
    input       [2 : 0]                          S_AXI_ARPROT,
    input                                        S_AXI_ARVALID,
    output                                       S_AXI_ARREADY,
    output      [C_S_AXI_DATA_WIDTH-1 : 0]       S_AXI_RDATA,
    output      [1 : 0]                          S_AXI_RRESP,
    output                                       S_AXI_RVALID,
    input                                        S_AXI_RREADY
);

    //Xilinx AXI-4 Lite Interface.
    //    
    // AXI4LITE signals
    reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_awaddr;
    reg                   axi_awready;
    reg                   axi_wready;
    reg [1 : 0]               axi_bresp;
    reg                   axi_bvalid;
    reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_araddr;
    reg                   axi_arready;
    reg [C_S_AXI_DATA_WIDTH-1 : 0] axi_rdata;
    reg [1 : 0]               axi_rresp;
    reg                   axi_rvalid;
   
    // Example-specific design signals
    // local parameter for addressing 32 bit / 64 bit C_S_AXI_DATA_WIDTH
    // ADDR_LSB is used for addressing 32/64 bit registers/memories
    // ADDR_LSB = 2 for 32 bits (n downto 2)
    // ADDR_LSB = 3 for 64 bits (n downto 3)
    localparam integer           ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1;
    localparam integer           OPT_MEM_ADDR_BITS = 4;
    localparam integer           REG_TOTAL = 16;
    localparam                   WR_ACCESS = 16'b1111_1111_0110_0011;
    //----------------------------------------------
    //-- Signals for user logic register space example
    //------------------------------------------------
    //-- Number of Slave Registers 16
    reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg [0:REG_TOTAL-1];
    reg [C_S_AXI_DATA_WIDTH-1:0]   slv_reg_d [0:REG_TOTAL-1];

    wire               slv_reg_rden;
    wire               slv_reg_wren;
    reg [C_S_AXI_DATA_WIDTH-1:0]   reg_data_out;
    integer               j, byte_index;
   
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
    // axi_awready is asserted for one aclk clock cycle when both
    // S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_awready is
    // de-asserted when reset is low.
   
    always @( posedge aclk ) begin
      if ( aresetn == 1'b0 )
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
    always @( posedge aclk ) begin
      if ( aresetn == 1'b0 )
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
    // axi_wready is asserted for one aclk clock cycle when both
    // S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_wready is 
    // de-asserted when reset is low. 
   
    always @( posedge aclk )
    begin
     if ( aresetn == 1'b0 )
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

    genvar k;
    generate
      for(k=0; k<REG_TOTAL; k=k+1) begin
        if (WR_ACCESS[k] == 1) begin
          always @( posedge aclk ) begin
            if ( aresetn == 1'b0 ) begin
              slv_reg[k] <= 0;
            end
            else if (slv_reg_wren && axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] == k) begin
              for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 ) begin
                if ( S_AXI_WSTRB[byte_index] == 1 ) begin
                  slv_reg[k][(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                end
              end
            end
            else begin
              slv_reg[k] <= slv_reg_d[k];
            end
          end
        end
      end
    endgenerate
    
    // Implement write response logic generation
    // The write response and response valid signals are asserted by the slave 
    // when axi_wready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted.  
    // This marks the acceptance of address and indicates the status of 
    // write transaction.
   
    always @( posedge aclk )
      begin
     if ( aresetn == 1'b0 )
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
    // axi_arready is asserted for one aclk clock cycle when
    // S_AXI_ARVALID is asserted. axi_awready is 
    // de-asserted when reset (active low) is asserted. 
    // The read address is also latched when S_AXI_ARVALID is 
    // asserted. axi_araddr is reset to zero on reset assertion.
   
    always @( posedge aclk )
      begin
     if ( aresetn == 1'b0 )
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
    // axi_rvalid is asserted for one aclk clock cycle when both 
    // S_AXI_ARVALID and axi_arready are asserted. The slave registers 
    // data are available on the axi_rdata bus at this instance. The 
    // assertion of axi_rvalid marks the validity of read data on the 
    // bus and axi_rresp indicates the status of read transaction.axi_rvalid 
    // is deasserted on reset (active low). axi_rresp and axi_rdata are 
    // cleared to zero on reset (active low).  
    always @( posedge aclk )
      begin
     if ( aresetn == 1'b0 )
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
          4'h0   : reg_data_out <= slv_reg[0];
          4'h1   : reg_data_out <= slv_reg[1];
          4'h2   : reg_data_out <= slv_reg[2];
          4'h3   : reg_data_out <= slv_reg[3];
          4'h4   : reg_data_out <= slv_reg[4];
          4'h5   : reg_data_out <= slv_reg[5];
          4'h6   : reg_data_out <= slv_reg[6];
          4'h7   : reg_data_out <= slv_reg[7];
          4'h8   : reg_data_out <= slv_reg[8];
          4'h9   : reg_data_out <= slv_reg[9];
          4'hA   : reg_data_out <= slv_reg[10];
          4'hB   : reg_data_out <= slv_reg[11];
          4'hC   : reg_data_out <= slv_reg[12];
          4'hD   : reg_data_out <= slv_reg[13];
          4'hE   : reg_data_out <= slv_reg[14];
          4'hF   : reg_data_out <= slv_reg[15];
          default : reg_data_out <= 0;
     endcase
      end
   
    // Output register or memory read data
    always @( posedge aclk )
      begin
     if ( aresetn == 1'b0 )
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

    localparam IDLE         = 3'd0;
    localparam LOAD_COMMAND = 3'd1;
    localparam SEND_SAMPLE  = 3'd2;
    localparam STATUS       = 3'd3;
    localparam ERROR        = 3'd4;
    localparam MAX_BTT      = 23'h7FFFFF;
    localparam MAX_TRANSFER_SIZE = 20'd4095; //in words
    localparam ADDRESS_INCREMENT = (MAX_TRANSFER_SIZE+20'd1)<<3; // in bytes
    /*
      Register Map:
      0 - 0x00: RW
        - [0] - Soft Reset
      1 - 0x04: RW
        - [7:0] - Buffer Written Flags.
                  1 indicates that the buffer has been written to.
                  SW should clear this bit.
      2 - 0x08: RO - Error Status Bits - This should be read by the interrupt handler. If a non-zero value was read, the state machine should be reset.
        - [7:0] - TLAST flags
                  1 indicates that the buffer was not terminated by TLAST. This means that the transfer was ended prematurely.
        - [15:8]- Size mismatch flags
                  1 indicates that the transferred data was not equal to the expected size.
        - [23:16] - Data Mover Transfer Error
                  1 indicates that the datamover reported a failure during the data transfer. Register 0x1C should be read to determine the cause.
        - [31:24] - Invalid BRESP
                  1 indicates that an invalid BRESP code was detected outside of datamover's reported status.
      3 - 0x0C: RO - Status Interface - https://docs.xilinx.com/r/en-US/pg022_axi_datamover/Status-Interface.
        - [3:0] - Buffer 0
        - [7:4] - Buffer 1
        ...
        - [31:28] - Buffer 7
      4 - 0x10: RO - More status bits. This should also be read by the interrupt handler. Nonzero is error.
        - [0]  - S2MM Error
                  1 indicates that the datamover IP core has detected an error. This requires a hard reset.
        - [4]  - Error State
                  1 indicates that the state machine is in an error state.
      5 - 0x14: RW
        - [19:0] - Acquisition Length
        - [24] - Use Acquisition Length Value from Register. 1 - Use the value from the register. 0 - Use input value.
      6 - 0x18: RW
        - [3:0] - Number of Buffers to be used 
      7 - 0x1C: RO - Transfer Counter. This counter can be polled in place of the interrupt.
      8 - 0x20: RW - Buffer 0 Address
      9 - 0x24: RW - Buffer 1 Address
      ...
      15 - 0x3C: RW - Buffer 7 Address
    */

    // State machine logic
    reg [2:0] state_q, state_d;
    reg [2:0] buffer_idx_q, buffer_idx_d;

    // Soft Reset
    wire soft_reset = slv_reg[0][0];

    // Data
    wire [3:0]  buffer_count    = slv_reg[6][3:0];
    wire [19:0] reg_acq_len     = slv_reg[5][19:0];
    wire        use_reg_acq_len = slv_reg[5][24];
    reg  [19:0] acq_len_q, acq_len_d;
    wire [19:0] acq_len = use_reg_acq_len ? reg_acq_len : acq_len_in;
    reg  acq_len_rd_en_q, acq_len_rd_en_d;
    reg  [19:0] sample_count_q, sample_count_d;
    reg buffer_done_q, buffer_done_d;
    reg busy_q;

    // Command
    //wire [22:0] expected_btt = {acq_len_q, 3'b000};
    reg [22:0] expected_btt_q, expected_btt_d;
    wire [31:0] cmd_address_sel = buffer_idx_q == 3'd0 ? slv_reg[8] :
                              buffer_idx_q == 3'd1 ? slv_reg[9] :
                              buffer_idx_q == 3'd2 ? slv_reg[10] :
                              buffer_idx_q == 3'd3 ? slv_reg[11] :
                              buffer_idx_q == 3'd4 ? slv_reg[12] :
                              buffer_idx_q == 3'd5 ? slv_reg[13] :
                              buffer_idx_q == 3'd6 ? slv_reg[14] : slv_reg[15];
    reg [31:0] cmd_address_q, cmd_address_d;
    reg cmd_tvalid_q, cmd_tvalid_d;

    // Status
    reg status_tready_q, status_tready_d;

    // 
    reg update_status_register;
    reg interrupt_q, interrupt_d, interrupt_2q;
    reg [1:0] s2mm_bresp_q;
    wire [7:0] index_bit_select = buffer_idx_q == 3'd0 ? 8'b1 :
                                  buffer_idx_q == 3'd1 ? 8'b10 :
                                  buffer_idx_q == 3'd2 ? 8'b100 :
                                  buffer_idx_q == 3'd3 ? 8'b1000 :
                                  buffer_idx_q == 3'd4 ? 8'b10000 :
                                  buffer_idx_q == 3'd5 ? 8'b100000 :
                                  buffer_idx_q == 3'd6 ? 8'b1000000 : 8'b10000000;
    wire status_okay_n  = s_axis_s2mm_sts_tdata[7:4]  != 4'h8;          //Status Bits
    wire btt_mismatch   = s_axis_s2mm_sts_tdata[30:8] != expected_btt_q;  //Length of data transferred
    wire tlast_n        = s_axis_s2mm_sts_tdata[31]   != 1'b1;          //Terminated not by TLAST - overflow. This should never happen.
    wire bresp_detected = s2mm_bresp_q[1] == 1'b1 && !status_okay_n;    //BRESP detected but datamover is not reporting an error;

    reg [7:0] tlast_error_q;
    reg [7:0] size_mismatch_q;
    reg [7:0] datamover_error_q;
    reg [7:0] bresp_error_q;
    reg [31:0] cmd_status_q;

    reg [31:0] trf_cnt_q, trf_cnt_d;

    // Output Stream to Data Mover
    reg data_tvalid_en_q, data_tvalid_en_d;
    wire data_tvalid = data_tvalid_en_q & s_axis_tvalid;
    wire last_sample_of_acquisition = sample_count_q == (acq_len_q-20'd1);
    wire last_sample_of_current_transfer = sample_count_q == MAX_TRANSFER_SIZE;
    wire data_tlast  = last_sample_of_acquisition || last_sample_of_current_transfer; 

    always @(posedge aclk) begin
        if (aresetn == 1'b0 || soft_reset) begin
            state_q         <= IDLE;
            buffer_idx_q    <= 3'd0;
            sample_count_q  <= 20'd0;
            cmd_tvalid_q    <= 1'b0;
            status_tready_q <= 1'b0;
            data_tvalid_en_q <= 1'b0;
            interrupt_q     <= 1'b0;
            interrupt_2q    <= 1'b0;
            s2mm_bresp_q    <= 2'b0;
            trf_cnt_q       <= 32'h0;
            acq_len_q       <= 20'd0;
            acq_len_rd_en_q <= 1'b0;
            cmd_address_q   <= 32'h0;
            expected_btt_q  <= 23'h0;
            buffer_done_q   <= 1'b0;
            busy_q          <= 1'b0;
        end else begin
            state_q         <= state_d;
            buffer_idx_q    <= buffer_idx_d;
            sample_count_q  <= sample_count_d;
            cmd_tvalid_q    <= cmd_tvalid_d;
            status_tready_q <= status_tready_d;
            data_tvalid_en_q <= data_tvalid_en_d;
            interrupt_q     <= interrupt_d;
            interrupt_2q    <= interrupt_q;
            s2mm_bresp_q    <= axi_mm_bready && axi_mm_bready ? axi_mm_bresp : s2mm_bresp_q;
            trf_cnt_q       <= trf_cnt_d;
            //acq_len_q       <= gate ? acq_len : acq_len_q;
            acq_len_q       <= acq_len_d;
            acq_len_rd_en_q <= acq_len_rd_en_d;
            cmd_address_q   <= cmd_address_d;
            expected_btt_q  <= expected_btt_d;
            buffer_done_q   <= buffer_done_d;
            busy_q          <= state_q != IDLE;
        end
    end

    // Status Register
    genvar i;
    generate
      for(i=0; i<8; i=i+1) begin
        always @(posedge aclk) begin
          if (aresetn == 1'b0 || soft_reset) begin
            cmd_status_q[i*4+:4] <= 4'd0;
            tlast_error_q[i] <= 1'b0;
            size_mismatch_q[i] <= 1'b0;
            datamover_error_q[i] <= 1'b0;
            bresp_error_q[i] <= 1'b0;
          end else if(update_status_register && i == buffer_idx_q) begin
            cmd_status_q[i*4+:4] <= s_axis_s2mm_sts_tdata[7:4];
            tlast_error_q[i] <= tlast_n;
            size_mismatch_q[i] <= btt_mismatch;
            datamover_error_q[i] <= status_okay_n;
            bresp_error_q[i] <= bresp_detected;
          end else begin
            cmd_status_q[i*4+:4] <= cmd_status_q[i*4+:4];
            tlast_error_q[i] <= tlast_error_q[i];
            size_mismatch_q[i] <= size_mismatch_q[i];
            datamover_error_q[i] <= datamover_error_q[i];
            bresp_error_q[i] <= bresp_error_q[i];
          end
        end
      end
    endgenerate
    // RO Registers
    always @(*) begin
      slv_reg[2][7:0]   = tlast_error_q;
      slv_reg[2][15:8]  = size_mismatch_q;
      slv_reg[2][23:16] = datamover_error_q;
      slv_reg[2][31:24] = bresp_error_q;
      slv_reg[3][3:0]   = cmd_status_q[0*4+:4];
      slv_reg[3][7:4]   = cmd_status_q[1*4+:4];
      slv_reg[3][11:8]  = cmd_status_q[2*4+:4];
      slv_reg[3][15:12] = cmd_status_q[3*4+:4];
      slv_reg[3][19:16] = cmd_status_q[4*4+:4];
      slv_reg[3][23:20] = cmd_status_q[5*4+:4];
      slv_reg[3][27:24] = cmd_status_q[6*4+:4];
      slv_reg[3][31:28] = cmd_status_q[7*4+:4];
      slv_reg[4][3:0]   = {3'b0, s2mm_err};
      slv_reg[4][7:4]   = {1'b0, state_q};
      slv_reg[4][31:8]  = 24'h0;
      slv_reg[7]        = trf_cnt_q;
    end
    // Status Registers Write from Logic. In the event of write collision, the AXI4-Lite interface takes precedence.
    always @(*) begin
      //Default
      for(j = 0; j < REG_TOTAL; j = j+1) begin
        slv_reg_d[j] = slv_reg[j];
      end
      slv_reg_d[1] = update_status_register? {slv_reg[1][31:8], slv_reg[1][7:0] | index_bit_select} : slv_reg[1];
    end


    always @(*) begin
      state_d         = state_q;
      buffer_idx_d    = buffer_idx_q;
      sample_count_d  = sample_count_q;
      cmd_tvalid_d    = cmd_tvalid_q;
      status_tready_d = status_tready_q;
      data_tvalid_en_d= data_tvalid_en_q;
      interrupt_d     = 1'b0;
      update_status_register = 1'b0;
      trf_cnt_d       = trf_cnt_q;
      acq_len_rd_en_d = 1'b0;
      acq_len_d       = acq_len_q;
      cmd_address_d   = cmd_address_q;
      expected_btt_d  = expected_btt_q;
      buffer_done_d   = buffer_done_q;
      case(state_q)
        //IDLE
        IDLE: begin
          if (gate == 1'b1 && buffer_count != 4'd0 && acq_len != 20'd0) begin
            state_d       = LOAD_COMMAND;
            cmd_tvalid_d  = 1'b1;
            acq_len_rd_en_d = 1'b1;
            acq_len_d = acq_len;
            cmd_address_d = cmd_address_sel;
          end else if(s2mm_err) begin
            state_d       = ERROR;
            interrupt_d   = 1'b1;
          end else begin
            state_d       = IDLE;
          end
        end

        //LOAD_COMMAND
        LOAD_COMMAND: begin
          if (m_axis_s2mm_cmd_tready == 1'b1) begin
            state_d    = SEND_SAMPLE;
            cmd_tvalid_d  = 1'b0;
            data_tvalid_en_d = 1'b1;
          end else begin
            state_d = LOAD_COMMAND;
          end
        end

        //SEND_SAMPLE
        SEND_SAMPLE: begin
          if (m_axis_s2mm_tready && s_axis_tvalid) begin
            if(data_tlast) begin
              state_d = STATUS;
              data_tvalid_en_d = 1'b0;
              status_tready_d = 1'b1;
              sample_count_d = 20'd0;
              cmd_address_d = cmd_address_q + {12'b0, ADDRESS_INCREMENT};
              if (!last_sample_of_acquisition) begin
                buffer_done_d = 1'b0;
                expected_btt_d = {3'b0, ADDRESS_INCREMENT};
                acq_len_d = acq_len_q - (MAX_TRANSFER_SIZE+20'd1);
              end
              else begin
                buffer_done_d = 1'b1;
                expected_btt_d = {acq_len_q, 3'b000};
              end
            end
            else begin
              state_d = SEND_SAMPLE;
              sample_count_d = sample_count_q + 20'd1;
            end
          end else begin
            state_d = SEND_SAMPLE;
          end
        end

        //STATUS
        STATUS: begin
          if (s_axis_s2mm_sts_tvalid == 1'b1) begin
            status_tready_d = 1'b0;
            //Check for potential error conditions
            if (status_okay_n || btt_mismatch || tlast_n || bresp_detected) begin
              state_d = ERROR;
              update_status_register = 1'b1;
              interrupt_d   = 1'b1;
            end else if (buffer_done_q) begin
              state_d = IDLE;
              buffer_idx_d = ({1'b0, buffer_idx_q} + 4'd1) == buffer_count ? 3'd0 : buffer_idx_q + 3'd1;
              interrupt_d   = 1'b1;
              trf_cnt_d = trf_cnt_q + 32'b1;
              update_status_register = 1'b1;
            end else begin
              state_d = LOAD_COMMAND;
              cmd_tvalid_d = 1'b1;
            end
          end else begin
            state_d = STATUS;
          end
        end

        //ERROR
        ERROR: begin
          if (soft_reset) begin
            state_d = IDLE;
          end else begin
            state_d = ERROR;
          end
        end

        default: begin
          state_d = IDLE;
        end
      endcase
    end

  // Output Assignment
  // Received Data
  generate
      if(EXTERNAL_FRAMING_LOGIC == 1)
          assign s_axis_tready          = m_axis_s2mm_tready && state_q == SEND_SAMPLE;
      else
          assign s_axis_tready          = 1'b1;
  endgenerate
  // Command
  //                               USER&CACHE   RSVD     TAG                   ADDR         FLAGS        INCR  BTT
  assign m_axis_s2mm_cmd_tdata  = {8'b00000000, 4'b0000, {1'b0, buffer_idx_q}, cmd_address_q, 8'b00000000, 1'b1, MAX_BTT};
  assign m_axis_s2mm_cmd_tvalid = cmd_tvalid_q;
  // Status
  assign s_axis_s2mm_sts_tready = status_tready_q;
  // Output Stream to Data Mover
  assign m_axis_s2mm_tdata      = s_axis_tdata;
  assign m_axis_s2mm_tkeep      = {C_AXIS_TDATA_WIDTH/8{1'b1}};
  assign m_axis_s2mm_tlast      = data_tlast;
  assign m_axis_s2mm_tvalid     = data_tvalid;
  // Interrupt
  assign i_rq                   = interrupt_2q | interrupt_q;
  assign acq_len_rd_en          = acq_len_rd_en_q;
  // State check
  assign busy                   = busy_q;
endmodule
