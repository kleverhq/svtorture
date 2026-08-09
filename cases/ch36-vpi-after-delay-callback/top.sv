module top;
  timeunit 1ns;
  timeprecision 1ns;

  bit occupied_seen;
  bit empty_seen;

  initial begin
    $svtorture_vpi;
    #2;
    if (!occupied_seen) $fatal(1, "cbAfterDelay did not precede the time-2 queue");
    #3;
    if (!empty_seen) $fatal(1, "cbAfterDelay did not execute for an empty queue");
    $display("SVTORTURE_PASS:ch36-vpi-after-delay-callback");
    $finish;
  end
endmodule
