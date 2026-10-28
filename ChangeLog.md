# fa-dispatcher-py project changelog

## Version 0.1.0 (unreleased)

Added:
- `fad`: the dispatcher of the deterministic finite automaton diagrams
  (ПРИМС:КА, `type/ fa`): the step table of the automaton with the inherited
  transitions, the run of a tape to its verdict and output, the trace;
- the character classes of a `Classes` component for the texts;
- `fad_tape`: the tape files and the tests files;
- `fa-run`, the command line; `--diagnostics` writes the failures of the
  tests as the findings of the editor;
- `fad_session`: the stream session of the CyberiadaPro editor on stdin and
  stdout (JSON-RPC 2.0), `fa-run --session`;
- the editor plugin `fa-dispatcher`: Run on a Tape (the session) and Test the
  Tapes... (the findings);
- the examples: the parity of a bit string, an e-mail address, the Morse
  decoder and encoder;
- the packages: pip with the plugin as data files, `fa-run
  --install-editor-plugin [DIR]` copying it into the editor's folder, and the
  Debian package `python3-fa-dispatcher` (the plugin in
  `/usr/share/cyberiada-pro/plugins`, the documentation and the examples);
- Windows: the CyberiadaPro installer installs the package and binds the
  plugin (Python 3.10-3.14 on Windows 10+, Python 3.8 on Windows 7 SP1-8.1).
