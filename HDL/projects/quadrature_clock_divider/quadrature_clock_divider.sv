// this divider uses the counts per quarter cycle to ensure the division is always valid
// the application for this simple module is the generation of quadrature clocks that are
// divided from a fast input clock.
// The bit-width of the division factor is configurable for this module and refers to the
// number of bits in the quarter cycle count 
// Common applications are SPI buses for example.
module quadrature_clock_divider #(
    parameter DIVIDER_WIDTH = 8
)(
    input wire clk_in,                 // Fast input clock
    input wire reset_n,                // Reset signal
    input wire [DIVIDER_WIDTH-1:0] div_factor_4,     // Division factor as multiplier to 4
                                       // or "counts per quarter cycle"
    output reg sck_0,                  // 0-degree phase clock
    output reg sck_90                  // 90-degree phase-shifted clock
);

    reg [DIVIDER_WIDTH+1:0] counter;                 // Counter for clock division
    reg [DIVIDER_WIDTH+1:0] half_cycle;              // Half-cycle count for 50% duty cycle
    reg [DIVIDER_WIDTH+1:0] quarter_cycle;           // Quarter-cycle count for 90-degree shift
    reg [DIVIDER_WIDTH+1:0] zero;

    always @(posedge clk_in or negedge reset_n) begin
        if (~reset_n) begin
            counter <= 0;
            sck_0 <= 0;
            sck_90 <= 0;
            zero <= 0;
            half_cycle <= {1'b0, div_factor_4, 1'b0};          // 50% duty cycle
            quarter_cycle <= {2'b00, div_factor_4};            // 90-degree phase shift
        end else begin
            // Calculate half and quarter cycles based on the division factor
            half_cycle <= {1'b0, div_factor_4, 1'b0};          // 50% duty cycle
            quarter_cycle <= {2'b00, div_factor_4};            // 90-degree phase shift

            // Counter logic to generate sck_0 and sck_90
            if (counter >= {div_factor_4, 2'b00} - 1) begin
                counter <= 0;  // Reset counter at the end of the cycle
            end else begin
                counter <= counter + 1;
            end

            // Generate sck_0 and sck_90 based on counter values
            if (counter >= zero && counter < half_cycle) begin
                sck_0 <= 1;
            end else  begin
                sck_0 <= 0;
            end

            if (counter >= quarter_cycle && counter < half_cycle + quarter_cycle) begin
                sck_90 <= 1;
            end else begin
                sck_90 <= 0;
            end
        end
    end
endmodule

