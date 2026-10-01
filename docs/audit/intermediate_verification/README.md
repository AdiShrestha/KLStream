# Intermediate verification history

These records describe intermediate source states, not the final tree. The final
executed receipt is ../second_pass_verification.json with ../second_pass_logs/.

The first full run failed because the bundle fixture used incorrect field nesting.
Subsequent coverage runs exposed an obsolete count expectation and incorrect
module attribution. Selected failure logs are retained here. Historical receipts
contain original hashes and temporary commands; their old second_pass_logs paths
were overwritten by later runs. Do not verify those historical hashes against the
current log directory or infer that every original intermediate log is preserved.
The before_final_training_numeric_repairs receipt passed its exercised checks but
predates the signed-loss/cap/extreme-arithmetic regressions now in the final suite.

Other retained factory logs include the caught test-file edit and restoration.
They explain audit mistakes and evolving fixtures, never research observations.
