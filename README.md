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

* The interface - `API.md` (`API-ru.md` in Russian): for the authors of the
  programs and the diagrams - a diagram of an automaton, the `Dispatcher`, the
  automaton, the character classes, the tapes and the tests files, the
  command line, the errors and the session of the editor
* The architecture - `ARCHITECTURE.md`: the usage requirements, the
  references to the FA extension of PNST 984-2024 and to PNST 1044-2025, the
  model, the run, the tapes, the character classes, the session of the editor
  and the examples

The examples - the parity of a bit string, an e-mail address, the Morse
decoder and encoder - are in `examples` with their tests and the Morse
table (`examples/README.md`, `README-ru.md` in Russian).

## Installation

The dispatcher needs the `CyberiadaML` module: the binding of
`libcyberiadamlpp-py` with its libraries (version 1.1.0+, the FA rules),
each installed by its own README, or, when it is not installed, the
pure-Python interface of `cyberiadaml-py` 1.8+.

The Debian package - the modules, `fa-run`, the editor plugin in
`/usr/share/cyberiada-pro/plugins/fa-dispatcher`, the documentation and the
examples in `/usr/share/doc/python3-fa-dispatcher`:

    cmake -B build && cd build && ctest && cpack -G DEB
    sudo apt install ./python3-fa-dispatcher_0.1.0_all.deb

`ctest` runs the tests with the Python CMake finds
(`-DPython3_EXECUTABLE=...` selects another one). The package depends on
`python3-libcyberiadamlpp` or `python3-cyberiadaml`.

With pip (a virtual environment, the user site, Windows, macOS) nothing is
built: pip installs cyberiadaml-py with the dispatcher, which uses the
binding only when it is installed (on Windows before Python 3.10 pip does not
install cyberiadaml-py, which needs pydantic there; that case takes the
binding):

    python3 -m venv --system-site-packages venv && . venv/bin/activate
    pip install /path/to/fa-dispatcher-py
    fa-run --install-editor-plugin

Check with `fa-run --help`. The package `fad` is in the root of the
repository, so the directory of the repository on the Python path works as
well: `python3 -m fad` is `fa-run`.

On Windows the CyberiadaPro installer (the editor's
`packaging/build-windows-installer.sh`) installs the package with its Python
plugins component - into a Python 3.10-3.14 on Windows 10 and newer, a Python
3.8 on Windows 7 SP1-8.1 - and binds the plugin to that Python.

## Usage

    fa-run examples/parity-mealy.graphml 1 0 1 1
    fa-run examples/email.graphml --text 'j.doe@mail.ru'
    fa-run examples/morse-encoder.graphml --text JA | fa-run examples/morse-decoder.graphml --text - --join
    fa-run examples/email.graphml --test examples/email.tests

The output symbols go to stdout, the verdict to stderr; the exit code is 0
for an accepted tape, 1 for a rejected one, 2 for an error.

```python
import fad

dispatcher = fad.Dispatcher('examples/parity-mealy.graphml')
result = dispatcher.run(['1', '0', '1', '1'])
print(result.verdict, result.output)          # accepted ['ODD']
```

## The editor plugin

`editor-plugin` is the plugin of the CyberiadaPro editor, Plugins > Finite
Automata: Run on a Tape - the automaton step by step on a tape, the editor
marking the active state and showing the verdict and the output - and Test
the Tapes... - a tests file, a finding per failing tape. Both need a valid
automaton: an editor with the plugin conditions greys them out on another
diagram and on a draft breaking EXT-FA, naming its first violation.

* The Debian package installs it into the system plugin folder; the plugin
  runs `python3 -m fad` with the packaged modules.
* `fa-run --install-editor-plugin [DIR]` copies the plugin of a pip
  installation or of this source tree into the user plugin folder of the
  editor (`~/.local/share/Cyberiada/CyberiadaPro/plugins` on Linux,
  `%APPDATA%` on Windows) or into DIR. The copy runs the Python that
  installed it; from a source tree it also puts the tree on `PYTHONPATH`.
* `CyberiadaPro --plugin-path /path/to/fa-dispatcher-py` finds it in the
  source tree without a copy; then `python3` needs the modules and the
  `CyberiadaML` module.

## Tests

    cd test
    python3 run.py                  # with the binding, or cyberiadaml-py without it
    FAD_BACKEND=cml python3 run.py  # on cyberiadaml-py beside an installed binding

The tests run the tests files of the examples and of the compat-tests FA
diagrams (when `cyberiadaml-compat-tests` is found beside this repository),
check that its `X-FA` negatives are refused, and run the same tapes on
`hsm-dispatcher-py` as an oracle when it is found. `session_test.py` drives
the editor session with a script, `plugin_test.py` runs the plugin in the
batch mode of CyberiadaPro (skipped without it). `cmake -B build && cd build
&& ctest` runs them all on both backends. `pylint.sh` runs the linter.

## Requirements

* python3 (version 3.8+)
* the `CyberiadaML` module with the FA rules: libcyberiadamlpp-py (version
  1.1.0+, with its dependencies) or, when it is not installed, cyberiadaml-py
  (version 1.8.0+), its pure-Python interface
* hsm-dispatcher-py - optional, the oracle of the tests
* cmake (version 3.16+) - for the Debian package
