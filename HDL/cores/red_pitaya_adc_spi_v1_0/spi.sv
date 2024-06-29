
`timescale 1 ns / 1 ps

module spi_write #(
    parameter WIDTH = 16
) (
    output  n_cs,
    output  sclk,
    output  sdio,
    output  done,
    input   [WIDTH-1:0] spi_data,
    input   en,
    input   aclk,
    input   aresetn
);
    typedef enum logic [1:0]{
        Idle, Low, High
    } state_e;

    state_e state_q, state_d;
    logic [WIDTH-1:0] spi_data_q, spi_data_d;
    logic n_cs_q, n_cs_d;
    logic sclk_q, sclk_d;
    logic sdio_q, sdio_d;
    logic [1:0] pulse_count_q, pulse_count_d;   //4clk low and 4clk high
    logic [$clog2(WIDTH)-1:0] shift_count_q, shift_count_d;
    logic done_q, done_d;

    assign n_cs = n_cs_q;
    assign sclk = sclk_q;
    assign sdio = sdio_q;
    assign done = done_q;

    always_ff @(posedge aclk) begin
        if (~aresetn) begin
            state_q         <= Idle;
            spi_data_q      <= '0;
            n_cs_q          <= 1'b1;
            sclk_q          <= 1'b1;
            sdio_q          <= 1'b1;
            pulse_count_q   <= '0;
            shift_count_q   <= '0;
            done_q          <= '0;
        end
        else begin
            state_q         <= state_d;
            spi_data_q      <= spi_data_d;
            n_cs_q          <= n_cs_d;
            sclk_q          <= sclk_d;
            sdio_q          <= sdio_d;
            pulse_count_q   <= pulse_count_d;
            shift_count_q   <= shift_count_d;
            done_q          <= done_d;
        end
    end

    always_comb begin
        state_d         = state_q;
        spi_data_d      = spi_data_q;
        n_cs_d          = n_cs_q;
        sclk_d          = sclk_q;
        sdio_d          = sdio_q;
        pulse_count_d   = pulse_count_q;
        shift_count_d   = shift_count_q;
        done_d          = 1'b0;
        case (state_q)
            Idle: begin
                if (en) begin
                    state_d = Low;
                    pulse_count_d = 'd0;
                    shift_count_d = 'd0;
                    spi_data_d = {spi_data[WIDTH-2:0], 1'b0};
                    n_cs_d = 1'b0;
                    sclk_d = 1'b0;
                    sdio_d = spi_data[WIDTH-1];
                end
            end
            Low: begin
                if (pulse_count_q == '1) begin
                    state_d = High;
                    pulse_count_d = 'd0;
                    sclk_d = 1'b1;
                end
                else
                    pulse_count_d = pulse_count_q + 'd1;
            end
            High: begin
                if (pulse_count_q == '1 && (shift_count_d + 'd1 == WIDTH)) begin
                    state_d = Idle;
                    n_cs_d = 1'b1;
                    sclk_d = 1'b1;
                    done_d = 1'b1;
                end
                else if (pulse_count_q == '1) begin
                    state_d = Low;
                    pulse_count_d = 'd0;
                    shift_count_d = shift_count_q + 'd1;
                    spi_data_d = {spi_data_q[WIDTH-2:0], 1'b0};
                    sclk_d = 1'b0;
                    sdio_d = spi_data_q[WIDTH-1];
                end
                else
                    pulse_count_d = pulse_count_q + 'd1;
            end
            default: begin
                state_d = Idle;
                spi_data_d = '0;
                n_cs_d = 1'b1;
                sclk_d = 1'b1;
                sdio_d = 1'b1;
                pulse_count_d = '0;
                shift_count_d = '0;
                done_d = '0;
            end
        endcase
    end

endmodule
