module top;
  task automatic produce(output logic [7:0] formal);
    formal = 8'hcb;
  endtask

  initial begin
    logic [3:0] actual = 4'h0;
    produce(actual);
    if (actual !== 4'hb)
      $fatal(1, "actual=%h expected=b after copy-out", actual);
    $display("SVTORTURE_PASS:ch13-output-copyout-width");
    $finish;
  end
endmodule

