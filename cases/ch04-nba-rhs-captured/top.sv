module top;
  int source = 5;
  int target = 0;

  initial begin
    target <= source;
    source = 17;
    #1;
    if (target != 5)
      $fatal(1, "target=%0d expected captured value 5", target);
    $display("SVTORTURE_PASS:ch04-nba-rhs-captured");
    $finish;
  end
endmodule

