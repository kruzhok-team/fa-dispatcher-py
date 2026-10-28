# The Python Finite Automata Dispatcher

The run-time interpreter of the Cyberiada project that executes deterministic
finite automaton diagrams (ПРИМС:КА, `type/ fa`) stored in the
CyberiadaML-GraphML format. The dispatcher reads a tape of symbols or of
text, gives the verdict - accepted or rejected - and the output symbols, and
serves the step-by-step runs of the CyberiadaPro editor. It is written in
pure Python 3 and generates no code.

The code is distributed under the Lesser GNU Public License (version 3), the
documentation -- under the GNU Free Documentation License (version 1.3).

## Documentation

The documentation is located in the `docs` directory and contains:

* The architecture - `ARCHITECTURE.md`: the usage requirements, the
  references to the FA extension of PNST 984-2024 and to PNST 1044-2025, the
  model, the run, the tapes, the character classes, the session of the editor
  and the examples

## Requirements

* python3 (version 3.8+)
* the `CyberiadaML` module with the FA rules: libcyberiadamlpp-py (version
  1.1.0+, with its dependencies) or, when it is not installed, cyberiadaml-py
  (version 1.8.0+), its pure-Python interface
