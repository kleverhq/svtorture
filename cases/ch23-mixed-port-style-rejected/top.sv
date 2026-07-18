module leaf(input logic first, input logic second);
endmodule

module top;
  leaf u(1'b0, .second(1'b1)); // SVTORTURE_DIAG_ANCHOR:ch23-mixed-port-style-rejected
endmodule

