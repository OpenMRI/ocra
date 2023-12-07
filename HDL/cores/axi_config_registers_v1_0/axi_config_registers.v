// the code is released to the public domain
 
module axi_config_registers #
  (
   parameter integer AXI_ADDR_WIDTH = 6,
   parameter integer AXI_DATA_WIDTH = 32
   )

   (
    input			   S_AXI_ACLK,
    input			   S_AXI_ARESETN,
   
    input			   S_AXI_ARVALID,
    output			   S_AXI_ARREADY,
    input [AXI_ADDR_WIDTH-1:0]	   S_AXI_ARADDR,
    input [2:0]			   S_AXI_ARPROT,

    output			   S_AXI_RVALID,
    input			   S_AXI_RREADY,
    output [AXI_DATA_WIDTH-1:0]	   S_AXI_RDATA,
    output [1:0]		   S_AXI_RRESP,

    input			   S_AXI_AWVALID,
    output			   S_AXI_AWREADY,
    input [AXI_ADDR_WIDTH-1:0]	   S_AXI_AWADDR,
    input [2:0]			   S_AXI_AWPROT,

    input			   S_AXI_WVALID,
    output			   S_AXI_WREADY,
    input [AXI_DATA_WIDTH-1:0]	   S_AXI_WDATA,
    input [(AXI_DATA_WIDTH/8)-1:0] S_AXI_WSTRB,

    output			   S_AXI_BVALID,
    input			   S_AXI_BREADY,
    output [1:0]		   S_AXI_BRESP,

    output [AXI_DATA_WIDTH-1:0]	   config_0,
    output [AXI_DATA_WIDTH-1:0]	   config_1,
    output [AXI_DATA_WIDTH-1:0]	   config_2,
    output [AXI_DATA_WIDTH-1:0]	   config_3,
    output [AXI_DATA_WIDTH-1:0]	   config_4,
    output [AXI_DATA_WIDTH-1:0]	   config_5,
    output [AXI_DATA_WIDTH-1:0]	   config_6,
    output [AXI_DATA_WIDTH-1:0]	   config_7
    );
   
   localparam			   ADDR_TO_REG_BITS = $clog2(AXI_DATA_WIDTH) - 3;
   
   reg [AXI_DATA_WIDTH-1:0]	   regfile [(1<<(AXI_ADDR_WIDTH-ADDR_TO_REG_BITS))-1:0];
   
   // read state machine
   
   localparam			   
				   s_read_address = 1'b0,
				   s_read_data = 1'b1
				   ;
   
   reg				   read_state;
   
   initial read_state = s_read_address;
   
   assign S_AXI_ARREADY = read_state == s_read_address;
   assign S_AXI_RVALID = read_state == s_read_data;
   assign S_AXI_RDATA = read_data_reg;
   assign S_AXI_RRESP = 2'b0;

   
   assign config_0 = regfile[0];
   assign config_1 = regfile[1];
   assign config_2 = regfile[2];
   assign config_3 = regfile[3];
   assign config_4 = regfile[4];
   assign config_5 = regfile[5];
   assign config_6 = regfile[6];
   assign config_7 = regfile[7];
   reg [AXI_DATA_WIDTH-1:0]	   read_data_reg;
   
   always @(posedge S_AXI_ACLK)
     begin
        if( !S_AXI_ARESETN )
          begin
             read_state <= s_read_address;
          end
        else if( read_state == s_read_address )
          begin
             if( S_AXI_ARVALID )
               begin
                  read_data_reg <= regfile[S_AXI_ARADDR >> ADDR_TO_REG_BITS];
                  read_state <= s_read_data;
               end
          end
        else if( read_state == s_read_data )
          begin
             if( S_AXI_RREADY )
               begin
                  read_state <= s_read_address;
               end
          end
     end
   
   // write state machine
   
   localparam 
              s_write_address = 2'b00,
              s_write_data = 2'b01,
              s_write_resp = 2'b11
              ;
   
   reg [1:0]  write_state;
   
   initial write_state = s_write_address;
   
   assign S_AXI_AWREADY = write_state == s_write_address;
   assign S_AXI_WREADY = write_state == s_write_data;
   assign S_AXI_BVALID = write_state == s_write_resp;
   assign S_AXI_BRESP = 2'b00;
   
   reg [AXI_ADDR_WIDTH-1:0] write_address_reg;
   
   // wstrb handling
   
   genvar		    i;
   generate
      for(i=0; i<AXI_DATA_WIDTH/8; i=i+1)
        begin
           always @(posedge S_AXI_ACLK)
             begin
                if( S_AXI_ARESETN && write_state == s_write_data && S_AXI_WVALID && S_AXI_WSTRB[i])
                  begin
                     regfile[write_address_reg >> ADDR_TO_REG_BITS][(i+1)*8-1:i*8] = S_AXI_WDATA[(i+1)*8-1:i*8];
                  end
             end
        end
   endgenerate
   
   always @(posedge S_AXI_ACLK)
     begin
        if( !S_AXI_ARESETN )
          begin
             write_state <= s_write_address;
          end
        else if( write_state == s_write_address )
          begin
             if( S_AXI_AWVALID )
               begin
                  write_address_reg <= S_AXI_AWADDR;
                  write_state <= s_write_data;
               end
          end
        else if( write_state == s_write_data )
          begin
             if( S_AXI_WVALID )
               begin
                  write_state <= s_write_resp;
               end
          end
        else if( write_state == s_write_resp )
          begin
             if( S_AXI_BREADY )
               begin
                  write_state <= s_write_address;
               end
          end
     end
   
endmodule
