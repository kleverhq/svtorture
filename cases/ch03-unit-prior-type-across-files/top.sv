module top;
  shared_byte_t observed;

  initial begin
    observed = $unit::unit_value;
    if (observed !== 8'h2a)
      $fatal(1, "observed=%h expected=2a", observed);
    $display("SVTORTURE_PASS:ch03-unit-prior-type-across-files");
    $finish;
  end
endmodule
