module complex_mul #(
    parameter WIDTH = 16
)(
    input  logic                 clk,
    input  logic                 rst_n,

    input  logic signed [WIDTH-1:0] a_real,
    input  logic signed [WIDTH-1:0] a_imag,
    input  logic signed [WIDTH-1:0] b_real,
    input  logic signed [WIDTH-1:0] b_imag,
    input  logic                 valid_in,

    output logic signed [2*WIDTH-1:0] result_real,
    output logic signed [2*WIDTH-1:0] result_imag,
    output logic                 valid_out
);

    // Stage 1: Multiply — request DSP inference
    (* use_dsp = "yes" *) logic signed [2*WIDTH-1:0] ac, bd, ad, bc;
    logic                      v1;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ac <= 0; bd <= 0; ad <= 0; bc <= 0;
            v1 <= 0;
        end else begin
            ac <= a_real * b_real;
            bd <= a_imag * b_imag;
            ad <= a_real * b_imag;
            bc <= a_imag * b_real;
            v1 <= valid_in;
        end
    end

    // Stage 2: Add/Sub
    logic signed [2*WIDTH-1:0] real_tmp, imag_tmp;
    logic                      v2;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            real_tmp <= 0;
            imag_tmp <= 0;
            v2 <= 0;
        end else begin
            real_tmp <= ac - bd;
            imag_tmp <= ad + bc;
            v2 <= v1;
        end
    end

    // Stage 3: Output register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result_real <= 0;
            result_imag <= 0;
            valid_out   <= 0;
        end else begin
            result_real <= real_tmp;
            result_imag <= imag_tmp;
            valid_out   <= v2;
        end
    end

endmodule

