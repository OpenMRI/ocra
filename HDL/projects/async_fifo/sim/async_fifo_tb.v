`timescale 1ns/1ps

module async_fifo_tb;

    localparam DATA_WIDTH = 16;
    localparam ADDR_WIDTH = 5;
    localparam MAX_COUNT = 32;

    reg wr_clk = 0;
    reg wr_rst_n = 0;
    reg wr_en = 0;
    reg [DATA_WIDTH-1:0] wr_data = 0;
    wire full;
    wire almost_full;

    reg rd_clk = 0;
    reg rd_rst_n = 0;
    reg rd_en = 0;
    wire [DATA_WIDTH-1:0] rd_data;
    wire rd_valid;
    wire empty;
    wire almost_empty;

    // Instantiate DUT
    async_fifo #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) dut (
        .wr_clk(wr_clk),
        .wr_rst_n(wr_rst_n),
        .wr_data(wr_data),
        .wr_en(wr_en),
        .full(full),
        .almost_full(almost_full),

        .rd_clk(rd_clk),
        .rd_rst_n(rd_rst_n),
        .rd_data(rd_data),
        .rd_valid(rd_valid),
        .rd_en(rd_en),
        .empty(empty),
        .almost_empty(almost_empty)
    );

    // Clock generation
    always #5 wr_clk = ~wr_clk;   // 100 MHz
    always #6 rd_clk = ~rd_clk;   // ~83 MHz

    // Counters and expected data
    integer wr_count = 0;
    integer rd_count = 0;
    reg [DATA_WIDTH-1:0] expected_data = 0;

    // Reset sequence
    initial begin
        wr_rst_n = 0;
        rd_rst_n = 0;
        #20;
        wr_rst_n = 1;
        rd_rst_n = 1;
    end

    // Write process
    always @(posedge wr_clk) begin
        if (wr_rst_n) begin
            if (wr_count < MAX_COUNT && !full) begin
                wr_en <= 1;
                wr_data <= wr_count[DATA_WIDTH-1:0];
                wr_count <= wr_count + 1;
            end else begin
                wr_en <= 0;
            end
        end
    end

    // Read process
    always @(posedge rd_clk) begin
        if (rd_rst_n) begin
            rd_en <= ~empty;
        end else begin
            rd_en <= 0;
        end
    end

    // Verification
    always @(posedge rd_clk) begin
        if (rd_valid) begin
            if (rd_data !== expected_data) begin
                $display("❌ ERROR: Data mismatch at time %t: expected %0d, got %0d",
                         $time, expected_data, rd_data);
                $fatal;
            end else begin
                $display("✅ Read %0d at time %t", rd_data, $time);
                expected_data <= expected_data + 1;
                rd_count <= rd_count + 1;
            end
        end
    end

    // Monitor flags
    always @(posedge wr_clk) begin
        if (wr_en && full)
            $display("⚠️  WARNING: FIFO full while writing at time %t", $time);
    end

    always @(posedge rd_clk) begin
        if (rd_en && empty)
            $display("⚠️  WARNING: FIFO empty while reading at time %t", $time);
    end

    // Finish condition
    initial begin
        wait (rd_count == MAX_COUNT);
        #20;
        $display("🎉 PASS: All data transferred correctly.");
        $finish;
    end

    // VCD trace
    initial begin
        $dumpfile("fifo_tb.vcd");
        $dumpvars(0, async_fifo_tb);
    end

endmodule
