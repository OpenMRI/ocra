module sync_external_pulse (
    input aresetn,
    input aclk,
    input external_input,
    output pulse_detected
);

    //sync, debounce, and generate a pulse
    reg [3:0] input_sync;
    reg [15:0] counter;
    reg zero_q,  zero_2q, pulse_detected_q, pulse_detected_2q;

    always @(posedge aclk) begin
        if(!aresetn) begin
            input_sync          <= 4'h0;
            counter             <= 16'b0;
            zero_q              <= 1'b0;
            zero_2q             <= 1'b0;
            pulse_detected_q    <= 1'b0;
            pulse_detected_2q   <= 1'b0;
        end
        else begin
            input_sync          <= {input_sync[2:0], external_input};
            counter             <= (input_sync[3] == 1'b1) ? 16'd1 :
                                   (counter != 16'b0) ? counter + 16'd1 : 16'b0;
            zero_q              <= (counter == 16'b0) ? 1'b1 : 1'b0;
            zero_2q             <= zero_q;
            pulse_detected_q    <= (zero_q == 1'b1 && zero_2q == 1'b0) ? 1'b1 : 1'b0;
            pulse_detected_2q   <= pulse_detected_q;
        end
    end
    assign pulse_detected = pulse_detected_q || pulse_detected_2q;

endmodule