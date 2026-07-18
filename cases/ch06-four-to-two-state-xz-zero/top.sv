module top;
  logic [3:0] four_state = 4'b1xz1;
  bit [3:0] two_state;

  initial begin
    two_state = four_state;
    if (two_state !== 4'b1001)
      $fatal(1, "two_state=%b expected=1001", two_state);
    $display("SVTORTURE_PASS:ch06-four-to-two-state-xz-zero");
    $finish;
  end
endmodule

