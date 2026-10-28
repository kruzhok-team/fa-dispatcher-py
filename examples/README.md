# The Examples

Each example is a diagram (`.graphml`), a tests file (`.tests`) with its
tapes, and sometimes a tape file (`.tape`). `build.py` writes and lays out
the diagrams; the tests of the repository run every tests file.

    fa-run parity-mealy.graphml 1 0 1 1          ODD, accepted
    fa-run email.graphml --text 'a@b.c'          rejected at EOF: T1 is not accepting
    fa-run morse-decoder.graphml --test morse-decoder.tests

| Example | The automaton |
|---|---|
| `parity-recognizer` | accepts a bit string with an even number of ones |
| `parity-mealy` | writes `EVEN` or `ODD` at the end: the parity bit of UART 7E1 |
| `parity-moore` | writes the running parity: the initial state, then one symbol per bit |
| `email` | checks an e-mail address, read through the character classes |
| `morse-decoder` | Morse text to letters: `.--- .-` is `J A` |
| `morse-encoder` | letters to Morse text: `JA` is `.--- .-` |

## Parity

Two states, `Even` and `Odd`; `0` keeps the state, `1` changes it. The three
diagrams differ in the outputs only: none, on the `EOF` transitions (Mealy),
on the states (Moore).

## E-mail address

`[a-z0-9]+([._-][a-z0-9]+)*@[a-z0-9]+(\.[a-z0-9]+)*\.[a-z]{2,}` with the
letters of both cases and the Cyrillic ones. A transition reads one symbol,
so the characters come through the classes of the `CGML_COMPONENT chars`
comment: `letter`, `digit`, `dot`, `sep` (`_` and `-`) and `at`. The one
`dot` transition of the composite state `Domain` serves `Label`, `T1`, `T2`
and `Mid`; `Dot`, outside it, rejects a second dot. `T2` - two letters after
the last dot - is the only accepting state.

## Morse

A Morse text has a space between the letters and ` / ` between the words.
The decoder and the encoder translate one into the other and pipe:

    fa-run morse-encoder.graphml --text JA | fa-run morse-decoder.graphml --text - --join

The table of the letters both diagrams are built from (`.` is DOT, `-` is
DASH):

| Letter | Code | Letter | Code | Letter | Code | Letter | Code |
|---|---|---|---|---|---|---|---|
| A | `.-` | H | `....` | O | `---` | V | `...-` |
| B | `-...` | I | `..` | P | `.--.` | W | `.--` |
| C | `-.-.` | J | `.---` | Q | `--.-` | X | `-..-` |
| D | `-..` | K | `-.-` | R | `.-.` | Y | `-.--` |
| E | `.` | L | `.-..` | S | `...` | Z | `--..` |
| F | `..-.` | M | `--` | T | `-` | | |
| G | `--.` | N | `-.` | U | `..-` | | |

### The decoder

The decoder is the Morse tree: a state remembers the code read so far, `.`
leads to the left child, `-` to the right one.

```
Ready
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
```

Every letter state writes its letter twice over: `GAP/ J` back to `Ready`
on a space, `EOF/ J` to the final state at the end of the text, which has no
space after its last letter. `Ready` reads `WORD/ /` and the spaces around
it. 27 states, 82 transitions; the 52 return arrows are what makes the
drawing dense. The codes without a letter (`..--`, `.-.-`, `---.`, `----`)
have no transition, so `.-.- .--` is rejected at 3: `R` has no DASH.

**An exercise:** the digits are five symbols long (`1` is `.----`, `0` is
`-----`). They need the codes `..--`, `---.` and `----` as states of their
own, without a `GAP` output, between the letters and the digits.

### The encoder

The encoder is one state with a loop per row of the table: `J/ .---`. It
is no tree, because it reads `J` in one step and must write `.---` in that
step: a transition reads one input symbol and writes at most one output
symbol, and there is no transition without a symbol (FA 3.4). A code is
therefore one output symbol, and the output alphabet
`(\.|\-){1,4}` gives the 30 codes of one to four marks. A space or a slash is
`WORD`, written as `/`.

### With an HSM

The pair meets a state machine of the Arduino course: the button machine
measures the presses with a Timer and writes `.` for a short one, `-` for a
long one and a space for a pause; the decoder reads that text. The machine
controls the device, the automaton reads the string.
