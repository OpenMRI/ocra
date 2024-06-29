/*
    axi4_lite_driver -  Provides control to the AXI4 Lite Slave interface.
                        Current functionalities are Read and Write.
*/
class axi4_lite_driver
    #(parameter AXI_DATA_WIDTH = 32,
                AXI_ADDR_WIDTH = 16);

    virtual axi4_lite_intf #(.AXI_DATA_WIDTH(AXI_DATA_WIDTH), .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH))  vif;
    logic[AXI_DATA_WIDTH-1:0] rddata;

    function new(virtual axi4_lite_intf #(.AXI_DATA_WIDTH(AXI_DATA_WIDTH), .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH)) vif_i);
        this.vif = vif_i;
        this.vif.M_AXI_AWADDR = '0;
        this.vif.M_AXI_AWPROT = '0;
        this.vif.M_AXI_AWVALID = '0;
        this.vif.M_AXI_WDATA = '0;
        this.vif.M_AXI_WSTRB = '0;
        this.vif.M_AXI_WVALID = '0;
        this.vif.M_AXI_BREADY = '0;
        this.vif.M_AXI_ARADDR = '0;
        this.vif.M_AXI_ARPROT = '0;
        this.vif.M_AXI_ARVALID = '0;
        this.vif.M_AXI_RREADY = '0;
    endfunction

    task read (input logic[AXI_ADDR_WIDTH-1:0] read_address, output logic[AXI_DATA_WIDTH-1:0] read_data);
        wait (!this.vif.rst);
        // Start the read process on the next clock cycle.
        @(posedge this.vif.clk);
        this.vif.M_AXI_ARADDR = read_address;
        this.vif.M_AXI_ARVALID = 1'b1;
        this.vif.M_AXI_RREADY = 1'b1;

        //Wait for Slave to set ARREADY - handshake
        wait(this.vif.M_AXI_ARREADY);
        @(posedge this.vif.clk);
        this.vif.M_AXI_ARVALID = 1'b0;

        //Wait for Data
        wait(this.vif.M_AXI_RVALID);
        //log unsuccessful read if RRESP != 0
        if (this.vif.M_AXI_RRESP != 2'b0)
            $error("Unsuccessful Read from AXI Address = %x, Error Code = %b", this.vif.M_AXI_ARADDR, this.vif.M_AXI_RRESP);
        this.rddata = this.vif.M_AXI_RDATA;
        @(posedge this.vif.clk);
        this.vif.M_AXI_RREADY = 1'b0;
        read_data = this.rddata;
    endtask

    task write(logic[AXI_ADDR_WIDTH-1:0] write_address, logic [AXI_DATA_WIDTH-1:0] write_data, logic[(AXI_DATA_WIDTH/8)-1 : 0]  write_strobe);
        //$display("AXI Write: %4dns. Waiting for vif rst to be deasserted", $stime);
        wait (!this.vif.rst);
        // Start the write process on the next clock cycle.
        repeat (1) @(posedge this.vif.clk);
        this.vif.M_AXI_AWADDR = write_address;
        this.vif.M_AXI_WDATA = write_data;
        this.vif.M_AXI_WSTRB = write_strobe;
        this.vif.M_AXI_AWVALID = 1'b1;
        this.vif.M_AXI_WVALID = 1'b1;
        this.vif.M_AXI_BREADY = 1'b1;

        //Wait for Slave to set AWREADY and WREADY - handshake
        //$display("AXI Write: %4dns. Waiting for AWREADY and WREADY", $stime);
        wait(this.vif.M_AXI_AWREADY & this.vif.M_AXI_WREADY);
        repeat (1) @(posedge this.vif.clk);
        this.vif.M_AXI_AWVALID = 1'b0;
        this.vif.M_AXI_WVALID = 1'b0;

        //Wait for Validation
        //$display("AXI Write: %4dns. Waiting for BVALID", $stime);
        wait(this.vif.M_AXI_BVALID);
        //log unsuccessful write if BRESP != 0
        if (this.vif.M_AXI_BRESP != 2'b0)
            $error("Unsuccessful Write to AXI Address = %x, Data = %x, Error Code = %b", this.vif.M_AXI_AWADDR, this.vif.M_AXI_WDATA, this.vif.M_AXI_BRESP);
        repeat (1) @(posedge this.vif.clk);
        this.vif.M_AXI_BREADY = 1'b0;
        //$display("AXI Write: %4dns. Done", $stime);
    endtask

endclass
