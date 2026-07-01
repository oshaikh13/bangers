# Bug
05_q_to_b ==> milliseconds bug 
Context builder includes log events up until banger_timestamp + 0.001 (inclusive of last millisecond) so these are labeled H but fails on validator bc validator sees that some "H" are some ms after the banger_timestamp strict cutoff
Fix (line 130 qa validation)
    boundary_ts = cutoff_ts + 0.001
    if answer_basis == "H" and verify_at_ts >= boundary_ts:
        ...
    if answer_basis in {"F", "H+F"} and verify_at_ts < boundary_ts:
        ...
Note: "missing context events" due to failue of this validation^^

