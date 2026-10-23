`timescale 1ns/1ps
module delay_cell(input wire a, output wire y);
  assign y = a;
  specify
    (a => y) = (1, 1);
  endspecify
endmodule

module top;
  logic a = 1'b0;
  wire y;
  delay_cell u(.a(a), .y(y));

  initial begin
    $sdf_annotate("test.sdf");
    #20;
    if (y !== 1'b0)
      $fatal(1, "initial y=%b", y);
    a = 1'b1;
    #2;
    if (y !== 1'b0)
      $fatal(1, "transition was not delayed: y=%b", y);
    #3;
    if (y !== 1'b1)
      $fatal(1, "annotated transition missing: y=%b", y);
    $display("SVTORTURE_PASS:ch32-iopath-rise-annotates-path");
    $finish;
  end
endmodule
