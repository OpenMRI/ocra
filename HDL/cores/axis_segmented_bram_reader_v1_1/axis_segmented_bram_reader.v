
`timescale 1 ns / 1 ps

module axis_segmented_bram_reader #
(
  parameter integer AXIS_TDATA_WIDTH = 32,
  parameter integer BRAM_DATA_WIDTH = 32,
  parameter integer BRAM_ADDR_WIDTH = 10,
  parameter         CONTINUOUS = "FALSE"
)
(
  // System signals
  input wire 			     aclk,
  input wire 			     aresetn,

  input wire [BRAM_ADDR_WIDTH-1:0]   cfg_data,
  output wire [BRAM_ADDR_WIDTH-1:0]  sts_data,
  input wire [BRAM_ADDR_WIDTH-1:0]   current_offset,
  input wire [BRAM_ADDR_WIDTH-1:0]   buffer_offset,
  input wire                         buffer_select,
 		     
  // Master side
  input wire 			     m_axis_tready,
  output wire [AXIS_TDATA_WIDTH-1:0] m_axis_tdata,
  output wire 			     m_axis_tvalid,
  output wire 			     m_axis_tlast,

  input wire 			     m_axis_config_tready,
  output wire 			     m_axis_config_tvalid,

  // BRAM port
  output wire 			     bram_porta_clk,
  output wire 			     bram_porta_rst,
  output wire [BRAM_ADDR_WIDTH-1:0]  bram_porta_addr,
  input wire [BRAM_DATA_WIDTH-1:0]   bram_porta_rddata
);

  reg [BRAM_ADDR_WIDTH-1:0]   current_offset_q;
  reg [BRAM_ADDR_WIDTH-1:0]   cfg_data_q;

  reg [BRAM_ADDR_WIDTH-1:0] int_addr_reg, int_addr_next;
  reg [BRAM_ADDR_WIDTH-1:0] int_addr_reg_incremented;   //precomputing this value to ease routing
  reg [BRAM_ADDR_WIDTH-1:0] int_data_reg;
  reg [BRAM_ADDR_WIDTH-1:0] buffer_offset_reg;
  reg buffer_select_reg;
  reg update_data_reg;
  wire [BRAM_ADDR_WIDTH-1:0]  bram_addr;
  reg int_enbl_reg, int_enbl_next;
  reg int_conf_reg, int_conf_next;

  wire [BRAM_ADDR_WIDTH-1:0] sum_cntr_wire;
  wire int_comp_wire, int_tlast_wire;

  always @(posedge aclk) begin
    current_offset_q    <= current_offset;
    cfg_data_q          <= cfg_data;
    buffer_offset_reg   <= buffer_select_reg ? buffer_offset : 0;
    buffer_select_reg   <= buffer_select;
  end

  always @(posedge aclk)
    begin
       
    if(~aresetn)
      // since we are using aresetn as trigger, I can initialize the offset here
      begin
	 int_addr_reg <= current_offset_q; //{(BRAM_ADDR_WIDTH){1'b0}};
	 int_addr_reg_incremented <= current_offset_q + {{(BRAM_ADDR_WIDTH-1){1'b0}}, 1'b1};
	 int_data_reg <= {(BRAM_ADDR_WIDTH){1'b0}};
	 int_enbl_reg <= 1'b0;
	 int_conf_reg <= 1'b0;
     update_data_reg <= current_offset_q < cfg_data_q;
      end
    else
      begin
	 int_addr_reg <= int_addr_next;
	 int_addr_reg_incremented <= int_addr_next + {{(BRAM_ADDR_WIDTH-1){1'b0}}, 1'b1};
	 int_data_reg <= update_data_reg ? cfg_data_q : int_data_reg;
	 int_enbl_reg <= int_enbl_next;
	 int_conf_reg <= int_conf_next;
     update_data_reg <= 1'b0;
      end
  end

  assign sum_cntr_wire = int_addr_reg_incremented;
  assign int_comp_wire = int_addr_reg != int_data_reg;
  assign int_tlast_wire = ~int_comp_wire;

  generate
    if(CONTINUOUS == "TRUE")
    begin : GEN_CONTINUOUS
      always @*
      begin
        int_addr_next = int_addr_reg;
        int_enbl_next = int_enbl_reg;

        if(~int_enbl_reg & update_data_reg)
        begin
          int_enbl_next = 1'b1;
        end

        if(m_axis_tready & int_enbl_reg & int_comp_wire)
        begin
          int_addr_next = sum_cntr_wire;
        end

        if(m_axis_tready & int_enbl_reg & int_tlast_wire)
        begin
           int_addr_next = current_offset_q; //{(BRAM_ADDR_WIDTH){1'b0}};
        end
      end
    end
    else
    begin : GEN_STOP
      always @*
      begin
        int_addr_next = int_addr_reg;
        int_enbl_next = int_enbl_reg;
        int_conf_next = int_conf_reg;

        if(~int_enbl_reg & update_data_reg)
        begin
          int_enbl_next = 1'b1;
        end

        if(m_axis_tready & int_enbl_reg & int_comp_wire)
        begin
          int_addr_next = sum_cntr_wire;
        end

        if(m_axis_tready & int_enbl_reg & int_tlast_wire)
        begin
          int_enbl_next = 1'b0;
          int_conf_next = 1'b1;
        end

        if(int_conf_reg & m_axis_config_tready)
        begin
          int_conf_next = 1'b0;
        end
      end
    end
  endgenerate

  assign bram_addr = m_axis_tready & int_enbl_reg ? int_addr_next : int_addr_reg;
  assign sts_data = int_addr_reg;

  assign m_axis_tdata = bram_porta_rddata;
  assign m_axis_tvalid = int_enbl_reg;
  assign m_axis_tlast = int_enbl_reg & int_tlast_wire;

  assign m_axis_config_tvalid = int_conf_reg;

  assign bram_porta_clk = aclk;
  assign bram_porta_rst = ~aresetn;
  assign bram_porta_addr = buffer_offset_reg + bram_addr;

endmodule
