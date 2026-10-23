module top;
  import "DPI-C" function int c_increment(input int value);

  initial begin
    int result = c_increment(41);
    if (result != 42)
      $fatal(1, "result=%0d expected=42", result);
    $display("SVTORTURE_PASS:ch35-c-source-import");
    $finish;
  end
endmodule
