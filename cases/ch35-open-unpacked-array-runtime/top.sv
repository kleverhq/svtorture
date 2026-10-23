module top;
  import "DPI-C" function int inspect_and_write(inout int values []);

  initial begin
    int values [5:3] = '{10, 20, 30};
    if (inspect_and_write(values) != 1)
      $fatal(1, "foreign range or value check failed");
    if (values[4] != 42)
      $fatal(1, "values[4]=%0d expected=42", values[4]);
    $display("SVTORTURE_PASS:ch35-open-unpacked-array-runtime");
    $finish;
  end
endmodule
