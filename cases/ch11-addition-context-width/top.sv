module top;
  logic [15:0] left = 16'hffff;
  logic [15:0] right = 16'h0001;
  logic [16:0] result;

  initial begin
    result = left + right;
    if (result !== 17'h1_0000)
      $fatal(1, "result=%h expected=10000", result);
    $display("SVTORTURE_PASS:ch11-addition-context-width");
    $finish;
  end
endmodule

