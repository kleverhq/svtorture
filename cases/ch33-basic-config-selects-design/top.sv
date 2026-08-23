module top;
  leaf u();

  initial begin
    if (u.VALUE != 1)
      $fatal(1, "value=%0d expected=1", u.VALUE);
    $display("SVTORTURE_PASS:ch33-basic-config-selects-design");
    $finish;
  end
endmodule

config cfg;
  design work.top;
  default liblist liba;
endconfig
