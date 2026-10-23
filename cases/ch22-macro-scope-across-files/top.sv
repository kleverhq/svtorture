module top;
  initial begin
    if (`CROSS_FILE_VALUE != 29)
      $fatal(1, "cross-file macro expansion failed");
    $display("SVTORTURE_PASS:ch22-macro-scope-across-files");
    $finish;
  end
endmodule
