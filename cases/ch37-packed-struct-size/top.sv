module top;
  struct packed {
    logic [2:0] first;
    logic second;
  } value;
  bit inspection_ok;

  initial begin
    $svtorture_vpi;
    if (!inspection_ok) $fatal(1, "VPI packed-structure inspection failed");
    $display("SVTORTURE_PASS:ch37-packed-struct-size");
    $finish;
  end
endmodule
