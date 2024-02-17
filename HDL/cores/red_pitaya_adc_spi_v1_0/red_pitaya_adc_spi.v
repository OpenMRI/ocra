
`timescale 1 ns / 1 ps

module red_pitaya_adc_spi
(
    output  n_cs,
    output  sclk,
    output  sdio,
    input   aclk,
    input   aresetn
);
    localparam ADDR1 = 16'h0100; //Power Down Register - 00 for Normal Operation
    localparam ADDR2 = 16'h0201; //Timing Register - Normal polarity, No clk delay, stabilizer on.
    localparam ADDR3 = 16'h0302; //Output Mode Register - Output on, DDR CMOS
    localparam ADDR4 = 16'h0400; //Data Format Register - Offset Binary Format
    localparam IDLE = 2'b00;
    localparam SEND = 2'b01;
    localparam SPACE = 2'b10;
    localparam DONE = 2'b11;

    reg [1:0] state_q, state_d;
    reg [4*16-1:0] wrdata_q, wrdata_d;
    reg [1:0] cnt_q, cnt_d;
    reg [6:0] cnt_sleep_q, cnt_sleep_d;
    reg en_q, en_d;
    wire done;

    spi_write spi_writer_inst(
        .n_cs   (n_cs),
        .sclk   (sclk),
        .sdio   (sdio),
        .done   (done),
        .spi_data(wrdata_q[15:0]),
        .en     (en_q),
        .aclk   (aclk),
        .aresetn(aresetn)
    );

    always @(posedge aclk) begin
        if (~aresetn) begin
            state_q <= IDLE;
            wrdata_q <= {ADDR4, ADDR3, ADDR2, ADDR1};
            cnt_q <= 2'd0;
            en_q <= 1'b0;
            cnt_sleep_q <= 7'b0;
        end
        else begin
            state_q <= state_d;
            wrdata_q <= wrdata_d;
            cnt_q <= cnt_d;
            en_q <= en_d;
            cnt_sleep_q <= cnt_sleep_d;
        end
    end

    always@ (*) begin
        state_d = state_q;
        wrdata_d = wrdata_q;
        cnt_d = cnt_q;
        en_d = 1'b0;
        cnt_sleep_d = cnt_sleep_q;
        case(state_q)
            IDLE: begin
                state_d = SEND;
                en_d = 1'b1;
            end
            SEND: begin
                if(done && (&cnt_q)) begin
                    state_d = DONE;
                end
                else if(done) begin
                    state_d = SPACE;
                    cnt_sleep_d = 7'd0;
                end
            end
            SPACE: begin
                if(&cnt_sleep_q) begin
                    state_d = SEND;
                    en_d = 1'b1;
                    wrdata_d = {16'h0, wrdata_q[4*16-1:16]};
                    cnt_d = cnt_q + 2'd1;
                end
                else
                    cnt_sleep_d = cnt_sleep_q + 7'd1;
            end
            DONE:
                state_d = DONE; //here forever...
            default: begin
                state_d = IDLE;
                wrdata_d = {ADDR4, ADDR3, ADDR2, ADDR1};
                cnt_d = 2'd0;
                en_d = 1'b0;
            end
        endcase
    end

endmodule
