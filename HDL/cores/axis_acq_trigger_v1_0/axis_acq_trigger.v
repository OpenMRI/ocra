`timescale 1ns / 1ps
module axis_acq_trigger #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 16,
    parameter integer C_AXIS_TDATA_WIDTH = 64
)
(
    input wire                                   aclk,
    input wire                                   aresetn,

    //Received Stream
    input       [C_AXIS_TDATA_WIDTH-1:0]         s_axis_tdata,
    input                                        s_axis_tvalid,
    output                                       s_axis_tready,
    //Output Stream
    output      [C_AXIS_TDATA_WIDTH-1:0]         m_axis_tdata,
    output                                       m_axis_tvalid,
    input                                        m_axis_tready,

    input                                        gate,
    output                                       resetn_out,
    output                                       gate_out,
    output      [19:0]                           acq_len_out,

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
    localparam integer           REG_TOTAL = 10;
    localparam                   WR_ACCESS = 10'b01_1111_1111;
    localparam                   MAX_WINDOW_COUNT = 4;
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
    localparam IDLE         = 2'd0;
    localparam DATA_OFF     = 2'd1;
    localparam DATA_ON      = 2'd2;
    localparam ERROR        = 2'd3;
    /*
      Register Map:
      0 - 0x00: Acquisition Width 0
        - [31:0] - Acquisition Width 0
      1 - 0x04: Acquisition Delay 0
        - [31:0] - Acquisition Delay 0
      2 - 0x08: Acquisition Width 1
        - [31:0] - Acquisition Width 1
      3 - 0x0C: Acquisition Delay 1
        - [31:0] - Acquisition Delay 2
      4 - 0x10: Acquisition Width 2
        - [31:0] - Acquisition Width 2
      5 - 0x14: Acquisition Delay 2
        - [31:0] - Acquisition Delay
      6 - 0x18: Acquisition Width 3
        - [31:0] - Acquisition Width 3
      7 - 0x1C: Acquisition Delay 3
        - [31:0] - Acquisition Delay 3
      8 - 0x20: Soft Reset
        - [0] - Soft Reset
    */

    // State machine logic
    reg [1:0] state_q, state_d;
    reg [1:0] cnt_q, cnt_d;
    wire      tvalid_en = state_q == DATA_ON || state_q == ERROR; // tvalid is active when error is detected to ensure the existing transfer is completed
    // Soft Reset
    wire soft_reset = slv_reg[8][0];
    // Acquisition
    wire [31:0] acq    [0:MAX_WINDOW_COUNT-1];
    wire [31:0] drop   [0:MAX_WINDOW_COUNT-1];
    reg  [31:0] acq_q  [0:MAX_WINDOW_COUNT-1];
    reg  [31:0] drop_q [0:MAX_WINDOW_COUNT-1];
    reg  [31:0] sample_count_q, sample_count_d;
    reg  [31:0] max_len_q, max_len_d;
    reg  [31:0] acq_len_out_q, acq_len_out_d;
    reg         gate_out_q, gate_out_d;
    reg         overflow_q;
    wire        overflow_d = m_axis_tvalid && !m_axis_tready;
    genvar i;
    generate
        for(i=0; i<MAX_WINDOW_COUNT; i=i+1) begin
            assign acq[i]  = slv_reg[i*2];
            assign drop[i] = slv_reg[i*2+1];
            always @(posedge aclk) begin
                if (aresetn == 1'b0 || soft_reset) begin
                    acq_q [i] <= 32'h0;
                    drop_q[i] <= 32'h0;
                end else begin
                    acq_q [i] <= gate && state_q == IDLE ? acq [i]: acq_q [i];
                    drop_q[i] <= gate && state_q == IDLE ? drop[i]: drop_q[i];
                end
            end
        end
    endgenerate
    
    always @(posedge aclk) begin
        if (aresetn == 1'b0 || soft_reset) begin
            state_q         <= IDLE;
            cnt_q           <= 2'd0;
            sample_count_q  <= 32'h0;
            max_len_q       <= 32'h0;
            acq_len_out_q   <= 32'h0;
            gate_out_q      <= 1'b0;
            overflow_q      <= 1'b0;
        end else begin
            state_q         <= state_d;
            cnt_q           <= cnt_d;
            sample_count_q  <= sample_count_d;
            max_len_q       <= max_len_d;
            acq_len_out_q   <= acq_len_out_d;
            gate_out_q      <= gate_out_d;
            overflow_q      <= overflow_d;
        end
    end

    // RO Registers
    always @(*) begin
      slv_reg[9][7:0]       = {7'b0, overflow_q};
      slv_reg[9][15:8]      = {6'b0, state_q};
      slv_reg[9][31:16]     = 16'b0;
    end
    // Status Registers Write from Logic. In the event of write collision, the AXI4-Lite interface takes precedence.
    always @(*) begin
      //Default
      for(j = 0; j < REG_TOTAL; j = j+1) begin
        slv_reg_d[j] = slv_reg[j];
      end
    end

    always @(*) begin
      state_d         = state_q;
      cnt_d           = cnt_q;
      sample_count_d  = sample_count_q;
      max_len_d       = max_len_q;
      acq_len_out_d   = acq_len_out_q;
      gate_out_d      = 1'b0;
      case(state_q)
        //IDLE
        IDLE: begin
          if (gate == 1'b1 && acq[0] != 32'h0) begin
            state_d       = DATA_OFF;
            cnt_d         = 2'd0;
            max_len_d     = drop[0] - 32'd1;
            sample_count_d = 32'd0;
            acq_len_out_d = acq[0];
            gate_out_d    = 1'b1;
          end else begin
            state_d       = IDLE;
          end
        end

        //DATA OFF
        DATA_OFF: begin
          if ((s_axis_tvalid == 1'b1 && sample_count_q == max_len_q) || drop_q[cnt_q] == 32'h0) begin
            state_d    = DATA_ON;
            max_len_d  = acq_q[cnt_q] - 32'd1;
            sample_count_d = 32'd0;
            cnt_d      = cnt_q + 2'd1;
          end else if (s_axis_tvalid == 1'b1) begin
            sample_count_d = sample_count_q + 32'd1;
          end
        end

        //DATA ON
        DATA_ON: begin
          if (s_axis_tvalid && !m_axis_tready) begin
            state_d = ERROR;
          end
          else if (s_axis_tvalid == 1'b1 && sample_count_q == max_len_q) begin
            //If next window of acquisition is empty, or if this is the last window, then go to IDLE
            if (cnt_q == 2'b00 || acq_q[cnt_q] == 32'h0) begin
                state_d = IDLE;
                cnt_d   = 2'd0;
            end else begin
                state_d = DATA_OFF;
                max_len_d = drop_q[cnt_q] - 32'd1;
                sample_count_d = 32'd0;
                acq_len_out_d = acq_q[cnt_q];
                gate_out_d    = 1'b1;
            end
          end else if (s_axis_tvalid == 1'b1) begin
            sample_count_d = sample_count_q + 32'd1;
          end
        end

        ERROR: state_d = ERROR;

        default: begin
          state_d = IDLE;
          cnt_d   = 2'd0;
        end
      endcase
    end

  // Output Assignment
  assign s_axis_tready          = 1'b1;
  assign m_axis_tvalid          = tvalid_en & s_axis_tvalid;
  assign m_axis_tdata           = s_axis_tdata;
  assign resetn_out             = aresetn && !soft_reset;
  assign gate_out               = gate_out_q;
  assign acq_len_out            = acq_len_out_q;
endmodule
