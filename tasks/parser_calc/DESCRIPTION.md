# Task: parser_calc (L5, parser / algorithm)

Implement `evaluate(expr)` in `src/calc.py` — a small arithmetic evaluator:
- supports `+ - * /` and parentheses `( )`, with normal precedence and
  left-associativity (e.g. `20 - 5 - 5 == 10`, `20 / 2 / 5 == 2`);
- whitespace is tolerated anywhere;
- division produces floats (e.g. `10 / 4 == 2.5`);
- invalid expressions (empty, trailing operator, unbalanced parens, bad
  characters) must raise `ValueError`;
- division by zero must raise `ValueError`.

The hidden test suite covers these rules — make all tests pass before finishing.
