`timescale 1 ns / 1 ps

module axis_red_pitaya_adc_ddr #(
    parameter integer DDR_DATA_WIDTH = 7
) (
    // System signals
    input wire                         aclk,
    input wire                         aresetn,

    // ADC signals
    input wire [DDR_DATA_WIDTH-1:0]    adc_dat_in_0,
    input wire [DDR_DATA_WIDTH-1:0]    adc_dat_in_1,

    output wire [2*DDR_DATA_WIDTH-1:0] adc_dat_out_0,
    output wire [2*DDR_DATA_WIDTH-1:0] adc_dat_out_1,

    output wire                        test_pattern_valid_0,
    output wire                        test_pattern_valid_1
);
    localparam                   ADC_DATA_WIDTH = DDR_DATA_WIDTH*2;
    wire [  DDR_DATA_WIDTH-1:0]    adc_dat_in  [1:0];
    wire [2*DDR_DATA_WIDTH-1:0]    adc_dat_out [1:0];

    assign adc_dat_in[0] = adc_dat_in_0;
    assign adc_dat_in[1] = adc_dat_in_1;
    assign adc_dat_out_0 = adc_dat_out[0];
    assign adc_dat_out_1 = adc_dat_out[1];

    genvar i,j;
    generate
    for (i = 0; i < 2; i = i + 1) begin
        for (j = 0; j < DDR_DATA_WIDTH; j = j + 1) begin: IDDR_GEN
            IDDR #(
                .DDR_CLK_EDGE("SAME_EDGE_PIPELINED"),
                .SRTYPE("ASYNC")
            ) iddr_inst (
                .Q1 (adc_dat_out[i][2*j    ]), // 1-bit output for positive edge of clock
                .Q2 (adc_dat_out[i][2*j + 1]), // 1-bit output for negative edge of clock
                .C  (aclk                   ), // 1-bit clock input
                .CE (1'b1                   ), // 1-bit clock enable input
                .D  (adc_dat_in [i][j]      ), // 1-bit DDR data input
                .R  (!aresetn               ), // 1-bit reset
                .S  (1'b0                   )  // 1-bit set
            );
        end
    end
    endgenerate

    validate_pattern #(
        .DATA_WIDTH(ADC_DATA_WIDTH)
    ) validate_pattern_inst_0 (
        .aclk   (aclk),
        .resetn (aresetn),
        .data   (adc_dat_out[0]),
        .valid  (test_pattern_valid_0)
    );
    validate_pattern #(
        .DATA_WIDTH(ADC_DATA_WIDTH)
    ) validate_pattern_inst_1 (
        .aclk   (aclk),
        .resetn (aresetn),
        .data   (adc_dat_out[1]),
        .valid  (test_pattern_valid_1)
    );

endmodule
