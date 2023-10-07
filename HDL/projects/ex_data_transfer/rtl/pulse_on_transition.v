module pulse_on_transition (
    input aclk,
    input aresetn,
    input edge_transition_in,
    output pulse_out
);

    reg q1, q2, pulse;

    always @(posedge aclk) begin
        q1 <= !aresetn? 1'b0 : edge_transition_in;
        q2 <= !aresetn? 1'b0 : q1;
        pulse <= !aresetn? 1'b0 : q1 ^ q2;
    end
    assign pulse_out = pulse;
endmodule
