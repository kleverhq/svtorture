module top;
  typedef struct packed {
    logic [2:0] high;
    logic [4:0] low;
  } pair_t;

  pair_t value;
  initial begin
    value.high = 3'b101;
    value.low = 5'b10011;
    if (value !== 8'b101_10011)
      $fatal(1, "packed value=%b expected=10110011", value);
    $display("SVTORTURE_PASS:ch07-packed-struct-first-member-msb");
    $finish;
  end
endmodule

