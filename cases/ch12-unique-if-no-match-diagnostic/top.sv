module top;
  initial begin
    unique if (1'b0) begin end // SVTORTURE_DIAG_ANCHOR:ch12-unique-if-no-match-diagnostic
    $display("SVTORTURE_PASS:ch12-unique-if-no-match-diagnostic");
    $finish;
  end
endmodule

