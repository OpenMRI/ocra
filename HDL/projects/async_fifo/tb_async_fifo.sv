module tb_async_fifo;

    // Parameters
    parameter DATA_WIDTH = 16;
    parameter ADDR_WIDTH = 4; // FIFO depth = 2^ADDR_WIDTH

    // Signals
    reg                    wr_clk;
    reg                    wr_rst_n;
    reg [DATA_WIDTH-1:0]   wr_data;
    reg                    wr_en;
    wire                   full;

    reg                    rd_clk;
    reg                    rd_rst_n;
    wire [DATA_WIDTH-1:0]  rd_data;
    reg                    rd_en;
    wire                   empty;

    integer                write_count;
    integer                read_count;
    reg [DATA_WIDTH-1:0]   expected_data;

    // Instantiate the FIFO
    async_fifo_custom #(
        .DATA_WIDTH(DATA_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) fifo_inst (
        .wr_clk     (wr_clk),
        .wr_rst_n   (wr_rst_n),
        .wr_data    (wr_data),
        .wr_en      (wr_en),
        .full       (full),
        .rd_clk     (rd_clk),
        .rd_rst_n   (rd_rst_n),
        .rd_data    (rd_data),
        .rd_en      (rd_en),
        .empty      (empty)
    );

    // Clock generation
    initial begin
        wr_clk = 0;
        forever #5 wr_clk = ~wr_clk; // 100 MHz clock
    end

    initial begin
        rd_clk = 0;
        forever #7 rd_clk = ~rd_clk; // Approximately 71.4 MHz clock
    end

    // Reset generation
    initial begin
        wr_rst_n = 0;
        rd_rst_n = 0;
        #20;
        wr_rst_n = 1;
        rd_rst_n = 1;
    end

    // Write process
    initial begin
        wr_en = 0;
        wr_data = 0;
        write_count = 0;
        @(posedge wr_rst_n);
        @(posedge wr_clk);

        // Write data until a certain count
        while (write_count < 50) begin
            @(posedge wr_clk);
            if (!full) begin
                wr_en = 1;
                wr_data = write_count;
                write_count = write_count + 1;
            end else begin
                wr_en = 0;
            end
        end
        wr_en = 0;
    end

    // Read process
    initial begin
        rd_en = 0;
        expected_data = 0;
        read_count = 0;
        @(posedge rd_rst_n);
        @(posedge rd_clk);

        // Read data until all written data is read
        while (read_count < 50) begin
            @(posedge rd_clk);
            if (!empty) begin
                rd_en = 1;
            end else begin
                rd_en = 0;
            end
        end
        rd_en = 0;
    end

    // Data integrity check
    always @(posedge rd_clk) begin
        if (rd_en && !empty) begin
            if (rd_data !== expected_data) begin
                $display("ERROR: Data Mismatch at time %t: Expected %0d, Got %0d", $time, expected_data, rd_data);
                $stop;
            end else begin
                expected_data = expected_data + 1;
                read_count = read_count + 1;
            end
        end
    end

    // Monitor full and empty flags
    always @(posedge wr_clk) begin
        if (full && wr_en) begin
            $display("INFO: FIFO is full at time %t", $time);
        end
    end

    always @(posedge rd_clk) begin
        if (empty && rd_en) begin
            $display("INFO: FIFO is empty at time %t", $time);
        end
    end

    // Terminate simulation
    initial begin
        wait (write_count == 50 && read_count == 50);
        #100; // Wait for any remaining activity
        $display("Simulation completed successfully at time %t", $time);
        $stop;
    end

endmodule
