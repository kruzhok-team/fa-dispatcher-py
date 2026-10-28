# The Python FA Dispatcher Architecture

Document version: 0.4 (2026-10-28)

The dispatcher executes the diagrams of deterministic finite automata (FA) at
run time. The diagrams follow ПРИМС:КА, the FA extension of PNST 984-2024
(`cyberiadaml-compat-tests/docs/FA-extension.md` 0.3), and are stored in the
CyberiadaML-GraphML format (CGML, PNST 1044-2025) with `type/ fa` in the
metadata. The dispatcher reads a tape, one symbol per step, sends `EOF` after
the last one and gives the verdict - the tape is accepted or rejected - and
the output symbols.

The dispatcher is a sibling of `hsm-dispatcher-py` (hsmd), not a mode of it:
an FA has no event queue, no clock and no components with code, and its
actions are output symbols, not Python. It depends on the `CyberiadaML`
module and on the Python 3 standard library only. The module is the binding
of `libcyberiadamlpp-py` when it is installed, else the pure-Python interface
of `cyberiadaml-py` (`cyberiadaml_py.cml`), chosen as in `hsmd_reader.py`.

## Usage requirements

| No | Requirement | Section |
|---|---|---|
| R1 | Load a CGML document of one FA; a document that breaks the FA rules is refused when it is loaded. | The model |
| R2 | Run a tape: one symbol per step, `EOF` after the last one; give the verdict and the output symbols. | The run |
| R3 | Be embedded: the application feeds the symbols one by one or gives the whole tape; the dispatcher never blocks. | Interface |
| R4 | Read a tape of symbols and a tape of text; the characters of a text become symbols by the classes of the diagram. | Tapes, Character classes |
| R5 | Report every step - the transition, the states left and entered, the output - in a trace and as the element ids of the document. | Steps and the trace |
| R6 | Answer the queries: the active state, the symbols it reads, the position on the tape, the accepting states. | Interface |
| R7 | Check a tests file: tapes with the expected verdict and output. | Tests files |
| R8 | Serve the stream session of the CyberiadaPro editor. | Sessions |
| R9 | Run from the command line and as an editor plugin. | The command line, The plugin |
| R10 | Give the same results on the binding and on cyberiadaml-py. | Testing |

## Standards

| Clause | Subject |
|---|---|
| FA 2.4 | the semantics: one active state; the transition of the active state by the symbol or, without one, of the nearest enclosing state; the output of the transition, then the output of the state entered; no transition - the tape is rejected and the run stops; `EOF` after the last symbol; the tape is accepted when `EOF` leads to a final state |
| FA 2.3 | the outputs on the transitions (Mealy) and on the states (Moore) in one automaton |
| FA 3.1, 3.1.1 | the output of a state is its `entry/`; a composite state has one region and no `entry/`; an inner transition replaces the enclosing one by the same symbol |
| FA 3.2 | the transition of the initial pseudostate is no step and has no output; the output of the initial state is its `entry/` |
| FA 3.3, 3.4 | a final state is reached by `EOF` only; one symbol per transition, at most one output symbol |
| FA 4 | the alphabets `FA_INPUT[_RE]` and `FA_OUTPUT[_RE]`; an alphabet formed by the executor from the components of the diagram |
| FA 5 | `type/ fa`, one state machine, `eventPropagation` absent or `block` |
| PNST 984, 7.4.6.4, 7.4.6.5 | the priority of the inner state, the selection from the innermost state outwards |
| PNST 1044, 6.3.2 | a transition between a composite state and its substate does not leave the composite state |

The library checks the FA rules when it opens the document (the
`FAException` of the binding, the `CGML-FA-*` rules of cyberiadaml-py), so
the dispatcher repeats none of them. It fixes the points the standard leaves
open:

| Point | Rule of the dispatcher |
|---|---|
| a symbol outside a declared `FA_INPUT` list | rejected at its position, like a symbol without a transition; the reason names the alphabet (an `FA_INPUT_RE` one is not matched: the reason is the missing transition) |
| the tape after a rejection | not read; `EOF` is not sent |
| the outputs of one step | the output of the transition first, then the `entry/` output of the simple state entered |
| the start | the initial transitions are followed before the first symbol; the `entry/` output of the initial state opens the output |
| an empty tape | `EOF` only |
| a step after the verdict | an error; `start()` begins a new run |

## Structure

```
   fad_reader.py                 fad_model.py
 +----------------+   model    +----------------+
 |     Reader     | ---------> |   Automaton    |
 |  CyberiadaML,  |            |  the states,   |
 |  the classes   |            | the step table |
 +----------------+            +----------------+
                                        | edges
                                        v
   fad_tape.py                   fad.py
 +----------------+  symbols   +----------------+  verdict, output
 |     Tapes      | ---------> |   Dispatcher   | -----------------> the application,
 |  symbol, text, |            |  start, feed,  | <----------------- fa-run
 |  tests files   |            |    end, run    |      symbols
 +----------------+            +----------------+
                                   ^          |
                           control |          | steps
                                   |          v
                               +----------------+
       the editor <-- JSON --> |    Session     |
                               +----------------+
                                 fad_session.py
```

The modules are plain files in the repository root, as in hsmd.

| Module | Role |
|---|---|
| `fad.py` | The `Dispatcher`: the run, the queries, the trace; the exports. The only module an application imports. |
| `fad_model.py` | The `Automaton`: the states and their parents, the initials, the accepting states, the table of the steps. No CyberiadaML. |
| `fad_reader.py` | Opens the document with the `CyberiadaML` module and builds the automaton; reads the `Classes` component. |
| `fad_tape.py` | The tapes: the symbols, the texts, the tape file and the tests file. |
| `fad_session.py` | The editor session: the stream logic over stdin and stdout. |
| `fad_cli.py` | `fa-run`, the command line. |

## The model

The reader walks the state machine as `hsmd_reader.py` does
(`get_children()`, `get_actions()`, `get_transitions()`) and builds:

* the simple and the composite states with their parents, the `entry/`
  output of a simple state;
* the initial pseudostates, the final state and the transitions: the source,
  the target, the symbol or `EOF`, the output;
* the alphabets - the symbols of `FA_INPUT`, the patterns of `FA_INPUT_RE`,
  the same for the output - kept for the reasons of the rejections;
* the classes of the `Classes` component.

The binding refuses a broken FA document on every open. cyberiadaml-py
1.8.0 refuses it in its strict mode only, so on that route the reader opens
a `type/ fa` document with `strict=True`.

From the elements the model computes the table of the steps: for every
simple state and every symbol read by a transition, the edge the step takes.

```
 (state, symbol) -> edge: the transition, the states exited, the states
                          entered, the outputs, the fired element ids
```

* The transition is the state's own one by the symbol or that of the nearest
  enclosing state (FA 2.4).
* The states exited run from the state up to, not including, the owner of
  the transition - the nearest common ancestor of its source and its target;
  a transition between a composite state and its substate keeps the
  composite state (PNST 1044, 6.3.2).
* The states entered run from the owner down to the target and on along the
  initial pseudostates to a simple state.
* The outputs are the symbol of the transition, then the `entry/` of the
  simple state reached: none, one or two symbols.
* The accepting states are those with an `EOF` edge (FA 3.3).

A row of `F-FA-NESTED` (compat-tests `fixtures/fa`): `(c2, EOF)` takes the
transition `c0-fin` of the composite state `C`, exits `c2` and `C`, enters
the final state, writes nothing.

## The run

| Call | What happens |
|---|---|
| `start()` | the initial transitions to a simple state; the `entry/` output of that state |
| `feed(symbol)` | the edge of `(active, symbol)`: fired; no edge: rejected, the run stops |
| `end()` | the `EOF` edge of the active state: accepted; no edge: rejected |
| `run(tape)` | `start()`, `feed()` for every symbol, `end()`; the result |

```
            start()                 end(): an EOF edge
 (idle) -----------> running -----------------------------> accepted
                     |    ^
                     +----+  feed(): an edge
                     |
                     +---------------------------------> rejected
                        feed() or end() without an edge
```

## Tapes

| Form | Example | Items |
|---|---|---|
| symbols: the command line, a tests file | `1 0 1 1` | the words between the spaces |
| a tape file | one symbol per line, `#` comments | one item per line: the untimed form of the hsmd stream (`hsmd_stream`) |
| a text | `"j.doe@mail.ru"` | one item per character, through the classes |

A line of a tape file in double quotes is a text: `"j.doe@mail.ru"` gives
13 items. A symbol with a space inside can be written in a tape file only.

## Character classes

A text reaches the automaton through the classes of a `Classes` component:
FA 4 lets the executor form the input alphabet from the components of the
diagram. The diagram stays small, and the symbols stay the identifiers the
CGML action grammar reads (`cyb_regexps.c`: `@`, `.`, `-` are no triggers).

```
CGML_COMPONENT chars              FA_INPUT
type/ Classes                     letter
                                  digit
letter/ [a-zA-Zа-яА-ЯёЁ]          dot
                                  sep
digit/ [0-9]                      at

dot/ \.

sep/ [_\-]

at/ @
```

* A parameter `<symbol>/ <pattern>` is a class; `type` is the component's.
* A pattern is one character: a literal one, a special one of FA 4 escaped
  (`\.`, `\-`, `\\`, ...), `.` for any character, or a bracket expression
  with ranges (`[a-z]`, `[_\-]`, `[ ]` for a space). The counts, the groups
  and the alternatives of FA 4 have no use for one character.
* A character of a text becomes the symbol of the first class that matches
  it, in the document order, or stays itself: `j doe` gives `letter`, ` `,
  `letter`, ... and the space is rejected unless a transition reads it.
* With an `FA_INPUT` list declared, every class symbol is in it.
* A document has at most one `Classes` component. Without one, a character
  of a text is a symbol of its own (`"1011"` is `1 0 1 1`).

The dispatcher translates the patterns itself: on the binding route
cyberiadaml-py and its `core.alphabet` may be absent.

## Steps and the trace

A `Step` has the `symbol`, the `position` on the tape, the `status` (fired or
rejected), the `transition`, the states `exited` and `entered`, the `output`
and `fired` - the element ids for the editor: the transition, the initial
pseudostates passed and their transitions. A rejected step has the `reason`.

The `Result` of `run()` has the `verdict`, the `output`, the `position` (the
items read), the `reason` and the `steps`.

| Reason | Example |
|---|---|
| no transition | `rejected at 3: R has no DASH` |
| outside the alphabet | `rejected at 2: 2 is not in FA_INPUT` |
| not accepting | `rejected at EOF: T1 is not accepting` |

The trace is a function of the application, called with a record - a tuple,
the kind first:

| Record | When |
|---|---|
| `start`, state | the initial state is entered |
| `symbol`, symbol, position | a symbol is read; `EOF` has the position of the end |
| `fire`, transition | a transition is executed |
| `exit`, state | a state is left |
| `enter`, state | a state is entered |
| `output`, symbol | an output symbol is written |
| `rejected`, position, reason | the run stops |
| `accepted` | `EOF` has reached the final state |

## Errors

| Error | When |
|---|---|
| `DocumentError` | the document is no `type/ fa`, the library refused it (with its message), the `Classes` component is wrong |
| `TapeError` | a line of a tape file or a tests file is wrong; with the line number |
| `StoppedError` | `feed()` or `end()` without a running run: before `start()` or after the verdict |

## Interface

The interface is specified for the authors of the programs and the diagrams
in `API.md` (`API-ru.md` in Russian). Its outline:

```python
import fad

dispatcher = fad.Dispatcher('examples/parity-mealy.graphml')
result = dispatcher.run(['1', '0', '1', '1'])  # the whole tape, EOF at the end
print(result.verdict, result.output)           # accepted ['ODD']

dispatcher.start()                             # step by step
step = dispatcher.feed('1')
step = dispatcher.end()                        # EOF

dispatcher.classify('j.doe@mail.ru')           # ['letter', 'dot', ...]
dispatcher.state()                             # the active state
dispatcher.symbols()                           # the symbols it reads
```

`fad` exports `Dispatcher`, `Automaton`, `read`, `Step`, `Result`, the
`ACCEPTED`, `REJECTED`, `FIRED` and `EOF` constants and the errors.

## The command line

```
fa-run DIAGRAM [SYMBOL ...]     a tape of symbols
fa-run DIAGRAM --text TEXT      a text; "-" reads stdin, the last newline dropped
fa-run DIAGRAM --tape FILE      a tape file; "-" reads stdin
fa-run DIAGRAM --test FILE      a tests file
fa-run DIAGRAM --session        the editor session over stdin and stdout
       --diagnostics FILE       with --test: the failures as the findings of the editor
       --join                   the output without the spaces between the symbols
       --trace                  the steps on stderr
```

The output symbols go to stdout, on one line, the verdict to stderr, so one
automaton pipes into another. The exit code is 0 when the tape is accepted
(every test passed), 1 when it is rejected (a test failed) and 2 for a wrong
document, tape or tests file.

## Tests files

```
# a line per tape: + accepted, - rejected, => the expected output
+ 1 0 1 1 => ODD
+ => EVEN
- 1 1 1
- "j..doe@mail.ru"
+ "JA" => .--- .-
```

A failing line is reported with its number, the expected and the actual
verdict and output, and the state where the run stopped.

## Sessions

The editor runs the automaton step by step through a session (the editor's
`PLUGINS.md`, Level 2, and the Sessions chapter of `PLUGIN-API.md`, the
`stream` logic). `fad_session.py` serves the protocol over stdin and stdout,
as `hsmd_session.py` does for an HSM; the line framing is the same, the code
is not shared, so that the dependency stays one way.

```json
{"kind": "driven", "logic": "stream", "steps": ["input"],
 "controls": ["step", "run", "restart"], "events": ["DOT", "DASH", "GAP", "WORD"],
 "end": "EOF", "stream": true, "save": true, "verdict": true, "output": true}
```

| The editor | The session |
|---|---|
| Step (`input`) | the next item of the tape; after the last one, `EOF` |
| Run | the items up to the verdict |
| Restart | `start()`; the tape from its first item |
| the event line, the end button | `feed(symbol)`, `end()` with the origin `user` |
| Load Stream..., Edit Stream... (`input`) | the tape file text: symbols and texts; the reply lists the items |
| Save Log... (`save`) | the items handled, as a tape file |
| `state` | `active` (the state and the composite states around it), `fired`, `position`, `verdict`, `output`, `events` (the symbols the active state reads); `finished` after the verdict |
| `history` | a row per item: the symbol, the origin `input` or `user`, the outcome `fired` or `rejected`, the fired ids |

## The plugin

```
 Plugins
   Finite Automata  >  Test the Tapes...    a tests file: a finding per failing line,
                                            on the state where the run stopped
                       Run on a Tape        the session: Plugins > Session F10, F5, F6
                       (later) Determinize, Minimize, Export the Table...
```

| Action | Kind | Runs |
|---|---|---|
| `test` "Test the Tapes..." | one-shot, `diagnostics`, `exit_ok` 0 and 1 | `python3 -m fad_cli ${document} --test ${param:tests} --diagnostics ${diagnostics}`; the parameter `tests` (a file, per document) starts at `<document>.tests` |
| `tape` "Run on a Tape" | session | `python3 -m fad_cli ${document} --session` |

The plugin lives in `editor-plugin/` (`plugin.json`, the icons, the Russian
translation) and is installed into the plugin directory of the editor as
`fa-dispatcher`, as the hsm-to-python one. A plugin needs a one-shot action,
so Test the Tapes is that. There is no action to check the automaton: the
editor opens and saves an FA document through the same library, which
refuses a broken one.

A run has no clock: Run goes to the verdict at once, and the session offers
no Pause.

## Examples

`examples/` holds a diagram, its tapes and a tests file for each use case;
the tests run every one. `examples/README.md` (`README-ru.md`) describes them
with the Morse table.

### Parity of a bit string

```
FA_INPUT: 0 1                         0 loops on Even and on Odd
(init) -> [Even] --1--> [Odd] --1--> [Even]
 a) recognizer  Even --EOF--> (final)                       an even number of ones
 b) Mealy       Even --EOF/ EVEN--> (final)  Odd --EOF/ ODD--> (final)
 c) Moore       Even entry/ 0  Odd entry/ 1  both --EOF--> (final)
```

| Diagram | Tape | Output | Verdict |
|---|---|---|---|
| a | `1 0 1` | | accepted |
| a | `1 1 1` | | rejected at EOF: Odd |
| b | `1 0 0 0 0 0 1` ('A' in UART 7E1) | `EVEN`: the parity bit is 0 | accepted |
| b | `1 0 1 1`, `"1011"` | `ODD` | accepted |
| b | the empty tape | `EVEN` | accepted |
| b | `1 0 2` | | rejected at 2: `2` is not in FA_INPUT |
| c | `1 0 1 1` | `0 1 1 0 1`: the initial state, then one per bit | accepted |

### E-mail address

`[a-z0-9]+([._-][a-z0-9]+)*@[a-z0-9]+(\.[a-z0-9]+)*\.[a-z]{2,}`, with the
letters of both cases and the Cyrillic ones, read through the classes
`letter`, `digit`, `dot`, `sep` (`[_\-]`) and `at`:

```
(init) -> [Start] -letter,digit-> [Local] -dot,sep-> [LocalSep] -letter,digit-> [Local]
          [Local] loops letter,digit;  [Local] -at-> [At] -letter,digit-> [Label]

 +---------------------- Domain ----------------------+
 | [Label] loops letter,digit                         |
 | [T1] -letter-> [T2]      T1, T2 -digit-> [Mid]     | --dot--> [Dot] -letter-> [T1]
 | [T2] loops letter        [Mid] loops letter,digit  |          [Dot] -digit-> [Mid]
 +----------------------------------------------------+
          [T2] --EOF--> (final)
```

9 states, 24 transitions; the one `dot` of `Domain` serves Label, T1, T2 and
Mid, and Dot, outside it, rejects a second dot.

| Tape | The path, the reason | Verdict |
|---|---|---|
| `"j.doe@mail.ru"` | Local, LocalSep, Local, At, Label, Dot, T1, T2, EOF | accepted |
| `"user_1@mail2.example.com"` | `mail2` passes Mid | accepted |
| `"иван@почта.рф"` | Cyrillic letters are `letter` | accepted |
| `"j..doe@mail.ru"` | at 2: LocalSep has no `dot` | rejected |
| `"john@localhost"` | at EOF: Label is not accepting | rejected |
| `"a@b.c"` | at EOF: T1, the last label has one letter | rejected |
| `"j doe@mail.ru"` | at 1: a space is in no class | rejected |

### The Morse decoder and encoder

Morse text has a space between the letters and ` / ` between the words. The
pair translates text into text and pipes:

```
fa-run examples/morse-decoder.graphml --text '.--- .-' --join      JA
fa-run examples/morse-encoder.graphml --text 'JA'                  .--- .-
fa-run examples/morse-encoder.graphml --text JA |
    fa-run examples/morse-decoder.graphml --text - --join          JA
```

The decoder is the Morse tree: a state remembers the code read so far.

```
CGML_COMPONENT chars: type/ Classes  DOT/ \.  DASH/ \-  GAP/ [ ]  WORD/ /
FA_INPUT: DOT DASH GAP WORD          FA_OUTPUT_RE: [A-Z]  /

Ready                       26 transitions DOT/ (".") and DASH/ ("-"), no output
├── . E                          .
│   ├── . I                      ..
│   │   ├── . S                  ...
│   │   │   ├── . H              ....
│   │   │   └── - V              ...-
│   │   └── - U                  ..-
│   │       └── . F              ..-.
│   └── - A                      .-
│       ├── . R                  .-.
│       │   └── . L              .-..
│       └── - W                  .--
│           ├── . P              .--.
│           └── - J              .---
└── - T                          -
    ├── . N                      -.
    │   ├── . D                  -..
    │   │   ├── . B              -...
    │   │   └── - X              -..-
    │   └── - K                  -.-
    │       ├── . C              -.-.
    │       └── - Y              -.--
    └── - M                      --
        ├── . G                  --.
        │   ├── . Z              --..
        │   └── - Q              --.-
        └── - O                  ---

Back from every letter state, e.g. J:  J --GAP/ J--> Ready    J --EOF/ J--> (final)
At the root:  Ready --WORD/ /--> Ready   Ready --GAP--> Ready   Ready --EOF--> (final)
```

27 states, 82 transitions: 26 of the tree, 26 `GAP` and 26 `EOF` returns,
each writing its own letter, and 4 at the root. The `EOF` returns write the
last letter, as a Morse text ends without a space. The codes without a letter
(`..--`, `.-.-`, `---.`, `----`) have no transition and are rejected.

| Tape | Steps | Output |
|---|---|---|
| `".--- .-"` | Ready, E, A, W, J; `GAP/ J`; E, A; `EOF/ A` | `J A`, accepted |
| `"... --- ... / .... . .-.. .--."` | | `S O S / H E L P`, accepted |
| `".-.- .--"` | Ready, E, A, R: R has no DASH | rejected at 3 |
| `"....."` | H has no DOT: `5` is a digit | rejected at 4 |

The encoder is one state with a loop per row of the Morse table:

```
CGML_COMPONENT chars: type/ Classes  WORD/ [ /]      a space or a slash
FA_INPUT_RE: [A-Z]  WORD             FA_OUTPUT_RE: (\.|\-){1,4}  /

(init) --> [ Ready ] --EOF--> (final)
             |    ^
             +----+   A/ .-   B/ -...   C/ -.-.   ...   Z/ --..   WORD/ /
```

1 state, 29 transitions. The encoder is no tree: it reads `J` in one step
and must write `.---` in that step - one input symbol and at most one output
symbol per transition, no transition without a symbol (FA 3.4) - so it has
no prefix to remember. Spaces are not checked: a double space is encoded as
it comes.

| Tape | Output | Verdict |
|---|---|---|
| `"JA"` | `.--- .-` | accepted |
| `"SOS HELP"`, `"SOS/HELP"` | `... --- ... / .... . .-.. .--.` | accepted |
| `"SOS  HELP"` | `... --- ... / / .... . .-.. .--.` | accepted |
| `"sos"` | | rejected at 0: `s` is no symbol |
| `"SOS!"` | | rejected at 3: `!` is in no class |

The tests of the pair: `decode(encode(w)) == w` for a word and
`encode(decode(m)) == m` for a Morse text. The pair meets an HSM in the
Arduino course: the button machine (a Timer: a short press `.`, a long one
`-`, a pause a space) writes the Morse text, and the decoder reads it.

libcyberiadaml 1.1.0 takes such an output symbol: one line of any
characters, as in cyberiadaml-py and as FA 4 escapes `.` and `-` for them;
the input symbols keep the shape of an event name.

### The conformance diagrams

The FA diagrams of compat-tests (`fixtures/fa`) run with tapes of their own:

| Diagram | Tape | Output | Verdict |
|---|---|---|---|
| F-FA-MEALY | `1 0 1` | `0 1 0` | accepted |
| F-FA-MOORE | `1 0 0` | `0 1 1` | accepted |
| F-FA-MOORE | the empty tape | | rejected at EOF |
| F-FA-NESTED | `a b`: the `b` of c1 replaces the `b` of C, the `EOF` of C serves c2 | | accepted |

The `X-FA-*` negatives are refused when they are loaded.

## Testing

`test/run.py` runs the tests files of `examples/` and of `test/compat/`
against their diagrams (the compat-tests FA diagrams when that repository is
found beside this one), the refusal of its negatives, the parts and
`fa-run`; `FAD_BACKEND=cml` runs them on cyberiadaml-py beside an installed
binding, as `HSMD_BACKEND` does for hsmd. `ctest` runs both, the second
skipped without cyberiadaml-py.

hsmd is the oracle of the semantics. When it is found (installed or beside
this repository), every diagram is built
as an `hsmd.Machine` (`hsmd_build.py`) from the elements the reader read - the
outputs as functions that append the symbol to a list - and runs the same
tapes: `dropped` is a rejection, `finished` after `EOF` an acceptance. The
verdicts and the outputs must agree with the dispatcher's, whose step table
is computed on its own.

`test/session_test.py` drives `fad_session.py` with a scripted editor, and
`test/plugin_test.py` runs the plugin in the editor's batch mode: the
session script `test/session/decoder.session` (`--session-script`,
`expect-verdict`) and Test the Tapes (`--dump-plugin`); it is skipped
without a CyberiadaPro binary.

## Stages

| Stage | Contents |
|---|---|
| 0 (done) | this document, `API.md` and `API-ru.md`: the interface, the tapes, the tests files, the classes |
| 1 (done) | the reader, the model, the run, the classes, the tapes, `fa-run`, the examples, the tests and the oracle; the output symbols of `libcyberiadaml` for the encoder |
| 2 (done) | the session, the plugin's Run on a Tape and Test the Tapes, with the editor test |
| 3 | the packages: pip, Debian, the plugin installed |
| 4 | Determinize, Minimize, Export the Table (a `replace` output laid out by the editor); the Windows installer |

## Open questions

* cyberiadaml-py refuses a broken FA document in its lenient mode too, as
  the binding does, so that the reader needs no strict open on that route;
* the position of the rejection in a tests file (`- 1 0 2 @ 2`);
* the digits of the Morse tree (five symbols; `..--`, `---.` and `----`
  become states without a `GAP` output).
