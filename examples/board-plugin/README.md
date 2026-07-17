# Example board plugin

Copy this directory to a separate repository, rename `clavis-example` and the
`clavis_example` package, then implement the hardware methods in `board.py`.
Methods deliberately raise `NotImplementedError` until implemented; the
template must not report successful hardware operations by default.
