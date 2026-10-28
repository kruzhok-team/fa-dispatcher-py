# The Python FA Dispatcher Interface Specification

Document version: 0.1 (2026-10-28)

This document is for the authors of the programs that run finite automata on
the dispatcher and of the diagrams those programs run. It specifies
everything they use: a diagram of an automaton, the `Dispatcher`, the
automaton read from a document, the character classes, the tapes and the
tests files, the command line, the errors and the session that serves an
automaton to the editor step by step. The execution rules and their reasons
are in `ARCHITECTURE.md`.

```
 the program                          fad                           the diagram
 ───────────                          ───                           ───────────
 Dispatcher(source, trace)  ────────▶ the automaton ◀──── a document (CyberiadaML),
 start() feed() end() run()           the step table       type/ fa, the classes
 state() symbols() classify()             │
      ▲                                   │
      └──── steps, results, trace ◀───────┘
 fad_tape: tapes, tests files     fad_session: the editor     fa-run: the command line
```

Everything is imported from one module: `import fad`; `fad_tape` and
`fad_session` are imported on their own.

## Conventions

* A **symbol** is a string: a symbol of the input alphabet on a transition,
  a symbol of the output alphabet as an output. The dispatcher compares the
  symbols as written.
* A **tape** is a sequence of symbols. The dispatcher reads it one symbol
  per step and sends `EOF` after the last one.
* A **text** is a string whose characters become symbols through the
  classes of the diagram (see Character classes).
* The **verdict** of a run is `accepted` or `rejected`. A run without a
  transition for a symbol is rejected at once and reads no more.
* The **output** is the list of the output symbols written by the run, in
  their order.
* A **position** counts the symbols read before it, from 0. `EOF` has the
  position of the end of the tape.
* The elements are named by the ids of the document: the states, the
  pseudostates and the transitions.

## A diagram of an automaton

A diagram is a CGML document (PNST 1044-2025) of one state machine, with the
parameter `type/ fa` in `CGML_META` (`FA-extension.md`, 5). The elements:

| Element | In the diagram | Example |
|---|---|---|
| a state | a simple state; its output symbol, if any, is its `entry/` | `entry/` `1` |
| a composite state | one region, no `entry/`; an initial pseudostate inside when a transition leads to the composite state itself | |
| the initial pseudostate | one on the top level; its transition has no text | |
| the final state | on the top level, reached by `EOF` only | |
| a transition | an input symbol or `EOF`, then `/`, then at most one output symbol | `1/`, `1/ 0`, `EOF/ ODD`, `J/ .---` |
| the alphabets | the formal comments `FA_INPUT` or `FA_INPUT_RE`, `FA_OUTPUT` or `FA_OUTPUT_RE` on the top level: a symbol or a pattern per line | `FA_OUTPUT_RE`: `[A-Z]` |
| the classes | the formal comment `CGML_COMPONENT <id>` with `type/ Classes` | see Character classes |

* A state reached by a symbol writes the output of the transition first,
  then its own output.
* A symbol is read by the transition of the active state or, without one, by
  that of the nearest enclosing state; an inner transition replaces the
  enclosing one by the same symbol.
* A state is **accepting** when its `EOF` transition, or that of an
  enclosing state, leads to the final state.
* A symbol is no reserved word: `do`, `else`, `entry`, `exit`, `propagate`,
  `block`, `defer`, `ANY`, `UNKNOWN`, `EOF`.
* An input symbol has the shape of an event name: letters, digits and `_`,
  with spaces and dots inside (`DOOR_OPEN`, `0`, `letter`). Other characters
  reach the automaton through the classes.
* An output symbol is one line without spaces. Until libcyberiadaml takes
  the other shapes, it has the shape of an event name too (`.---` waits for
  that change).

The library checks these rules when it opens the document; a broken
document is a `DocumentError`.

## The dispatcher

```python
import fad

dispatcher = fad.Dispatcher('parity-mealy.graphml')
result = dispatcher.run(['1', '0', '1', '1'])
print(result.verdict, result.output)          # accepted ['ODD']

dispatcher.start()                            # step by step
for symbol in dispatcher.classify('1011'):
    step = dispatcher.feed(symbol)
    if dispatcher.verdict:                    # rejected
        break
else:
    step = dispatcher.end()
print(dispatcher.verdict, dispatcher.output)
```

### `Dispatcher(source, trace=None)`

| Parameter | Meaning |
|---|---|
| `source` | the path of a CyberiadaML document, or an `fad.Automaton` |
| `trace` | a function called with each trace record (a tuple); no trace without it |

The constructor reads the document and computes the step table; a problem
is a `DocumentError`. Nothing runs before `start()` or `run()`.

### Members

| Member | Returns | Does |
|---|---|---|
| `start()` | the `Step` of the start | begins a new run: follows the initial transitions to a simple state and writes its output |
| `feed(symbol)` | a `Step` | reads one symbol; without a transition the run is rejected |
| `end()` | the `Step` of `EOF` | ends the tape: accepted when `EOF` reaches the final state, else rejected |
| `run(tape)` | a `Result` | `start()`, `feed()` for every symbol up to a rejection, `end()` |
| `classify(text)` | a list of symbols | the characters of the text through the classes |
| `state()` | a state id | the active simple state; after the verdict, the state where the run stopped |
| `states()` | a list of state ids | the active state and the composite states around it, the outermost first |
| `symbols()` | a list of symbols | the symbols the active state reads, its own and the inherited ones, in the document order, `EOF` aside |
| `accepting()` | `bool` | whether `end()` would accept now |
| `position` | `int` | the symbols read by the run |
| `output` | a list of symbols | the output of the run so far |
| `verdict` | `fad.ACCEPTED`, `fad.REJECTED` or `None` | `None` while the run goes on |
| `running` | `bool` | the run is started and has no verdict |
| `automaton` | the `Automaton` | |

`feed()` and `end()` without a running run - before `start()` or after the
verdict - raise `StoppedError`; `start()` begins again at any time.

### `Step` and `Result`

`Step`:

| Field | Meaning |
|---|---|
| `symbol` | the symbol; `None` for the start, `fad.EOF` for the end |
| `position` | the position of the symbol |
| `status` | `fad.FIRED`, or `fad.REJECTED` when no transition reads the symbol |
| `transition` | the id of the transition, `None` for the start and a rejection |
| `exited`, `entered` | the ids of the states left and entered, in their order |
| `output` | the output symbols of the step: none, one or two |
| `fired` | the ids for the editor: the transition, the initial pseudostates passed and their transitions |
| `reason` | why the symbol was rejected: `R has no DASH` |
| `verdict` | the verdict when this step gives it, else `None` |

`Result`: `verdict`, `output`, `position` (the symbols read), `state` (where
the run stopped), `reason`, `steps` (the start included) and `message`:

| Verdict | `message` |
|---|---|
| accepted | `accepted` |
| a symbol without a transition | `rejected at 3: R has no DASH` |
| a symbol outside a declared `FA_INPUT` list | `rejected at 2: 2 is not in FA_INPUT` |
| `EOF` in a state that is not accepting | `rejected at EOF: T1 is not accepting` |

The reasons name the states by their names, by their ids when they have
none.

### The trace

The dispatcher calls the trace function with a record, a tuple whose first
item is the kind:

| Record | When |
|---|---|
| `('start', state)` | a run begins in the simple state |
| `('symbol', symbol, position)` | a symbol is read; `EOF` too |
| `('fire', transition)` | a transition is executed |
| `('exit', state)` | a state is left |
| `('enter', state)` | a state is entered |
| `('output', symbol)` | an output symbol is written |
| `('rejected', position, reason)` | the run stops |
| `('accepted',)` | `EOF` has reached the final state |

## The automaton

`fad.read(path)` reads a document into an `Automaton`, which a `Dispatcher`
takes as its source; several dispatchers share one automaton.

| Member | Meaning |
|---|---|
| `name` | the name of the state machine |
| `states` | a dictionary: id -> `State` with `id`, `name`, `parent` (an id, `None` on the top level), `composite`, `output` (the `entry/` symbol or `None`) |
| `transitions` | a list of `Transition` with `id`, `source`, `target`, `symbol` (`None` for an initial one), `output` |
| `initial`, `final` | the ids of the top-level initial pseudostate and of the final state |
| `input_alphabet`, `output_alphabet` | `(name, lines)` of the alphabet comment, or `None` |
| `classes` | a list of `(symbol, pattern)` in the document order |
| `accepting` | the set of the accepting states |
| `edge(state, symbol)` | the `Edge` of the step, or `None`: `transition`, `exited`, `entered`, `output`, `fired` |
| `symbols(state)` | the symbols the state reads, its own and the inherited ones |
| `classify(text)` | as `Dispatcher.classify()` |
| `label(id)` | the name of the element, or its id |

## Character classes

A text reaches the automaton through a `Classes` component, so the diagram
reads a few symbols instead of every character:

```
CGML_COMPONENT chars
type/ Classes

letter/ [a-zA-Zа-яА-ЯёЁ]

digit/ [0-9]

dot/ \.

sep/ [_\-]

at/ @
```

* Each parameter `<symbol>/ <pattern>` is a class; `type` is the
  component's. The parameters are separated by empty lines (PNST 1044,
  10.3.1).
* A pattern matches one character:

  | Pattern | Matches |
  |---|---|
  | `a`, `@`, `я` | the character |
  | `\.`, `\-`, `\\` | a special character: `.` `[` `]` `-` `{` `}` `,` `?` `(` `)` `\|` `\` |
  | `.` | any character |
  | `[a-z0-9_]`, `[ ]`, `[_\-]` | a character of the set: the characters, the ranges `a-z`, the escaped specials; `[ ]` is the space |

* A character becomes the symbol of the first class that matches it, in
  the document order, or stays itself.
* With `FA_INPUT` or `FA_INPUT_RE` declared, every class symbol is in it.
* A document has one `Classes` component at most; without one, a character
  is a symbol of its own.
* The classes apply to texts only; a tape of symbols is read as it is.

## Tapes and tests files

`fad_tape` reads and writes the tape files and the tests files.

A tape file:

```
# the tape of a Morse decoder
DOT
DASH
".--- .-"
```

* A line is a symbol, the whole line without the spaces around it; `#`
  starts a comment line; empty lines are skipped.
* A line in double quotes is a text: a symbol per character.

A tests file:

```
# + accepted, - rejected, => the expected output
+ 1 0 1 1 => ODD
+ => EVEN
- 1 1 1
- "j..doe@mail.ru"
+ "JA" => .--- .-
```

* A line is a tape: `+` or `-`, then the symbols separated by spaces or one
  text in double quotes, then optionally `=>` and the expected output, the
  symbols separated by spaces. `+ => EVEN` is the empty tape; without `=>`
  the output is not checked.
* A text is the characters between the first and the last double quote of
  the line.
* A symbol with a space inside can be written in a tape file only.

| Member | Meaning |
|---|---|
| `read(text)` | the items of a tape file: `Item` with `kind` (`'symbol'` or `'text'`), `value`, `line`; a bad line is a `TapeError` with `line` |
| `write(items)` | the text of a tape file |
| `symbols(items, classify)` | the symbols of the items; a text through `classify` |
| `read_tests(text)` | the tests: `Test` with `line`, `verdict` (expected), `items`, `output` (a list, or `None`: not checked) |
| `check(dispatcher, tests)` | the failures: `Failure` with `test`, `result`, `message` |

## The command line

```
fa-run DIAGRAM [SYMBOL ...]     a tape of symbols
fa-run DIAGRAM --text TEXT      a text; "-" reads stdin, without its last newline
fa-run DIAGRAM --tape FILE      a tape file; "-" reads stdin
fa-run DIAGRAM --test FILE      a tests file
fa-run DIAGRAM --session        the editor session over stdin and stdout
       --join                   the output without spaces between the symbols
       --trace                  the trace records on stderr
```

* stdout gets the output on one line, the symbols separated by spaces (with
  `--join` without them); the line is empty without output. stderr gets the
  `message` of the result, so one automaton pipes into another:

  ```
  $ fa-run morse-encoder.graphml --text JA | fa-run morse-decoder.graphml --text - --join
  accepted
  accepted
  JA
  ```

* `--test` writes a line per failure to stderr,
  `email.tests:4: expected accepted, got rejected at 2: LocalSep has no dot`,
  and then `7 passed` or `6 passed, 1 failed`.
* The exit code is 0 when the tape is accepted or every test passed, 1 when
  it is rejected or a test failed, 2 for a wrong document, tape or tests
  file.

## Errors

| Error | When |
|---|---|
| `fad.DocumentError` | the document is no `type/ fa`, the library refused it (its message), the classes are wrong; raised by `read()` and the constructor |
| `fad.TapeError` | a line of a tape file or a tests file is wrong; `line` is its number |
| `fad.StoppedError` | `feed()` or `end()` without a running run |

They are subclasses of `fad.FAError`.

## Sessions

`fad_session` serves an automaton to the CyberiadaPro editor. The editor
marks the active state and the fired transition on the diagram, and the
user steps through a tape, runs it, types symbols and saves the run. The
protocol is the Sessions chapter of the editor's `PLUGIN-API.md`; this is a
driven session with the stream logic.

```
 CyberiadaPro               fad_session                     fad
 ────────────               ───────────                     ───
 control, event, ──stdin──▶ the tape, the position ───────▶ a Dispatcher:
 input, save                the symbols typed               start() feed() end()
 marks, history, ◀─stdout── state, history ◀──────── steps  states() symbols()
 verdict, output
```

| Member | Meaning |
|---|---|
| `serve(dispatcher, reader=sys.stdin, writer=sys.stdout)` | runs the session until `shutdown` or the end of the input; returns the exit code, 0 |

`fa-run DIAGRAM --session` serves a document. The answer to `initialize`:

```json
{"kind": "driven", "logic": "stream", "steps": ["input"],
 "controls": ["step", "run", "restart"], "events": ["DOT", "DASH", "GAP", "WORD"],
 "end": "EOF", "stream": true, "save": true, "verdict": true, "output": true}
```

`events` are the symbols of `FA_INPUT`, or of the transitions without it.

| Unit, message | The session does |
|---|---|
| step `input` | the next symbol of the tape, a character of a text counted as one; after the last one `end()`; after the verdict the status is `finished` |
| `run` | the steps up to the verdict; the speed does not matter, there is no clock |
| `restart` | `start()`; the tape from its first symbol |
| `event` | `feed(name)`, or `end()` for `EOF`, with the origin `user` |
| `input` | reads a tape file and restarts with it; the reply lists a symbol per item, a character of a text as its class symbol with `params: {"text": "j"}` |
| `save` | writes the symbols handled, the typed ones included, as a tape file |

* After every step the session sends `state`: `status` (`paused`, or
  `finished` after the verdict), `active` (`states()`), `fired`, `position`,
  `events` (`symbols()`), `output`, and `verdict` with the `message` in
  `text` once the run has one.
* Every symbol is a `history` message: the symbol (`EOF` for the end), the
  character of a text in `params`, the position, the origin (`input` or
  `user`), the outcome (`fired` or `rejected`) and the fired ids.
* The start is no history row: its marks and its output come with the first
  `state`.
