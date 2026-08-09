module top;
  logic clk = 0;
  logic value;

  covergroup cg @(posedge clk);
    option.per_instance = 1;
    cp: coverpoint value {
      bins zero = {0};
      bins one = {1};
    }
  endgroup
  cg cov = new;

  initial begin
    value = 0;
    clk = 1;
    clk = 0;
    value = 1;
    clk = 1;
    #1;
    if (cov.get_inst_coverage() != 100.0)
      $fatal(1, "coverage=%f", cov.get_inst_coverage());
    $display("SVTORTURE_PASS:ch19-clocking-event-automatic-sample");
    $finish;
  end
endmodule
