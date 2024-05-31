`timescale 1 ns / 1 ps

module axis_red_pitaya_adc_2ch #
(
    parameter integer ADC_DATA_WIDTH = 14,
    parameter integer AXIS_TDATA_WIDTH = 32
)
(
    // System signals
    input wire                          aclk,

    // ADC signals
    output wire                         adc_csn,
    input wire [ADC_DATA_WIDTH-1:0]     adc_dat_a,
    input wire [ADC_DATA_WIDTH-1:0]     adc_dat_b,

    // Master side
    output wire                         m0_axis_tvalid,
    output wire [AXIS_TDATA_WIDTH-1:0]  m0_axis_tdata,
    output wire                         m1_axis_tvalid,
    output wire [AXIS_TDATA_WIDTH-1:0]  m1_axis_tdata
);
    localparam PADDING_WIDTH = AXIS_TDATA_WIDTH/2 - ADC_DATA_WIDTH;
    
    reg [ADC_DATA_WIDTH-1:0]            data_a;
    reg [ADC_DATA_WIDTH-1:0]            data_b;
    wire                                sign_a, sign_b;
    wire [ADC_DATA_WIDTH-1:0]           channel_a;
    wire [ADC_DATA_WIDTH-1:0]           channel_b;

    assign channel_a = {~data_a[ADC_DATA_WIDTH-1], data_a[ADC_DATA_WIDTH-2:0]};
    assign channel_b = {~data_b[ADC_DATA_WIDTH-1], data_b[ADC_DATA_WIDTH-2:0]};
    assign sign_a = ~data_a[ADC_DATA_WIDTH-1];
    assign sign_b = ~data_b[ADC_DATA_WIDTH-1];

    always @(posedge aclk) begin
        data_a <= adc_dat_a;
        data_b <= adc_dat_b;
    end

    assign adc_csn = 1'b1;
    assign m0_axis_tvalid = 1'b1;
    assign m1_axis_tvalid = 1'b1;
    assign m0_axis_tdata = -{{PADDING_WIDTH{sign_a}},channel_a};
    assign m1_axis_tdata = -{{PADDING_WIDTH{sign_b}},channel_b};
    
endmodule
