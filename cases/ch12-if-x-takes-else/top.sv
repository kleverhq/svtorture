module top;
  logic [1:0] predicate = 2'bxx;
  int selected = 0;

  initial begin
    if (predicate)
      selected = 1;
    else
      selected = 2;
    if (selected != 2)
      $fatal(1, "selected=%0d expected else branch", selected);
    $display("SVTORTURE_PASS:ch12-if-x-takes-else");
    $finish;
  end
endmodule

