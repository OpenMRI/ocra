module ibufds_bufg (
    input clk_p,
    input clk_n,
    output clk
);

    wire clk_ibufds;
    wire clk_bufg;

    IBUFDS
    ibufds_inst (
        .I(clk_p),
        .IB(clk_n),
        .O(clk_ibufds)
    );

    BUFG
    bufg_inst (
        .I(clk_ibufds),
        .O(clk_bufg)
    );

    assign clk = clk_bufg;

endmodule
