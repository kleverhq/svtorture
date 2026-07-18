module top;
  initial begin
    // Make every incorrect semantic result call $fatal.
    if (1'b0) $fatal(1, "replace with the boundary check");
    $display("SVTORTURE_PASS:<case-id>");
    $finish;
  end
endmodule
