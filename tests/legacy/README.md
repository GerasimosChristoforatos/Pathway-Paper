# Frozen reference implementations

`Boss_legacy.py` and `MonteCarlo_legacy.py` are verbatim copies of `Boss.py`
and `MonteCarlo.py` at commit a25fbff, the last commit before the
forward model was moved into `engine.py` (item 3). The only edit is one line in
`MonteCarlo_legacy.py`: `import Boss` -> `import Boss_legacy as Boss`.

They are never run by the pipeline. `tests/test_engine_equivalence.py` uses them
to prove that the unified engine reproduces the old results on random draws
(and, with the adopted flags, keeps reproducing them after later changes).
