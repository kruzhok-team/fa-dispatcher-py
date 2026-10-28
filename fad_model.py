# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The automaton: the states, the transitions and the table of the steps
#
#  Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3 of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program. If not, see https://www.gnu.org/licenses/
#
#  -----------------------------------------------------------------------------

"""The automaton of a diagram (docs/ARCHITECTURE.md, The model): no CyberiadaML."""

import re

EOF = 'EOF'
ACCEPTED = 'accepted'
REJECTED = 'rejected'
FIRED = 'fired'

FA_INPUT = 'FA_INPUT'
FA_INPUT_RE = 'FA_INPUT_RE'
FA_OUTPUT = 'FA_OUTPUT'
FA_OUTPUT_RE = 'FA_OUTPUT_RE'
INPUT_NAMES = (FA_INPUT, FA_INPUT_RE)
OUTPUT_NAMES = (FA_OUTPUT, FA_OUTPUT_RE)

# the special characters of the FA 4 patterns, escaped by a backslash
SPECIALS = '.[]-{},?()|\\'
ANY_CHARACTER = '.'


class FAError(Exception):
    """The base of the errors of the dispatcher."""


class DocumentError(FAError):
    """The document is no FA diagram, the library refused it, or the classes are wrong."""


class TapeError(FAError):
    """A line of a tape file or of a tests file is wrong."""

    def __init__(self, line, message):
        super().__init__('line {}: {}'.format(line, message))
        self.line = line
        self.message = message


class StoppedError(FAError):
    """feed() or end() without a running run."""


class State:
    """A simple or a composite state."""

    def __init__(self, ident, name, parent, composite=False, output=None):
        self.id = ident
        self.name = name
        self.parent = parent
        self.composite = composite
        self.output = output


class Transition:
    """A transition; symbol is None for the one of an initial pseudostate."""

    def __init__(self, ident, source, target, symbol, output):
        self.id = ident
        self.source = source
        self.target = target
        self.symbol = symbol
        self.output = output


class Edge:
    """The step of a simple state by a symbol: state is the simple state reached."""

    def __init__(self, transition, exited, entered, output, fired, state):
        self.transition = transition
        self.exited = exited
        self.entered = entered
        self.output = output
        self.fired = fired
        self.state = state


def class_pattern(text):
    """The regular expression of a one-character class pattern (docs/API.md,
    Character classes); ValueError for a wrong one."""
    if text == ANY_CHARACTER:
        return re.compile('.', re.DOTALL)
    if len(text) == 1 and text not in SPECIALS:
        return re.compile(re.escape(text))
    if len(text) == 2 and text[0] == '\\' and text[1] in SPECIALS:
        return re.compile(re.escape(text[1]))
    if len(text) < 3 or text[0] != '[' or text[-1] != ']':
        raise ValueError("'{}' is no one-character pattern".format(text))
    body = text[1:-1]
    position = 0

    def character():
        nonlocal position
        c = body[position]
        if c == '\\':
            if position + 1 >= len(body) or body[position + 1] not in SPECIALS:
                raise ValueError("a backslash before no special character in '{}'".format(text))
            position += 2
            return body[position - 1]
        if c in '[]-':
            raise ValueError("'{}' unescaped in '{}'".format(c, text))
        position += 1
        return c

    parts = []
    while position < len(body):
        first = character()
        if position < len(body) and body[position] == '-':
            position += 1
            if position >= len(body):
                raise ValueError("a range without its end in '{}'".format(text))
            last = character()
            if last < first:
                raise ValueError("the range {}-{} is reversed in '{}'".format(first, last, text))
            parts.append('{}-{}'.format(re.escape(first), re.escape(last)))
        else:
            parts.append(re.escape(first))
    return re.compile('[' + ''.join(parts) + ']')


class Automaton:
    """The states, the transitions, the alphabets, the classes and the step table."""

    def __init__(self, name=''):
        self.name = name
        self.states = {}           # id -> State
        self.initials = {}         # the id of an initial pseudostate -> the id of its state, None on the top level
        self.initial = None
        self.final = None
        self.transitions = []
        self.input_alphabet = None
        self.output_alphabet = None
        self.classes = []          # (symbol, pattern)
        self.accepting = set()
        self.start_edge = None
        self.table = {}            # (state, symbol) -> Edge
        self._matchers = []
        self._own = {}             # state -> [(symbol, Transition)] in the document order
        self._starts = {}          # the id of an initial pseudostate -> its Transition

    # ------------------------------------------------------------------------
    # the queries

    def label(self, ident):
        """The name of the element, or its id."""
        state = self.states.get(ident)
        return state.name if state is not None and state.name else ident

    def chain(self, ident):
        """The state and the composite states around it, the outermost first."""
        result = []
        while ident is not None:
            result.append(ident)
            ident = self.states[ident].parent if ident in self.states else None
        return list(reversed(result))

    def edge(self, state, symbol):
        """The Edge of the step, or None."""
        return self.table.get((state, symbol))

    def symbols(self, state):
        """The symbols the state reads, its own first, then the inherited ones."""
        result = []
        for ident in reversed(self.chain(state)):
            for symbol, _ in self._own.get(ident, ()):
                if symbol != EOF and symbol not in result:
                    result.append(symbol)
        return result

    def input_symbols(self):
        """The symbols of a declared FA_INPUT list, else None."""
        alphabet = self.input_alphabet
        # pylint: disable-next=unsubscriptable-object
        return list(alphabet[1]) if alphabet is not None and alphabet[0] == FA_INPUT else None

    def events(self):
        """The input symbols: the FA_INPUT list, or those of the transitions."""
        declared = self.input_symbols()
        if declared is not None:
            return declared
        result = []
        for transition in self.transitions:
            if transition.symbol not in (None, EOF) and transition.symbol not in result:
                result.append(transition.symbol)
        return result

    def classify(self, text):
        """The characters of a text through the classes."""
        result = []
        for c in text:
            for symbol, matcher in self._matchers:
                if matcher.fullmatch(c):
                    result.append(symbol)
                    break
            else:
                result.append(c)
        return result

    # ------------------------------------------------------------------------
    # the table

    def _compile_classes(self):
        declared = self.input_symbols()
        self._matchers = []
        for symbol, pattern in self.classes:
            try:
                self._matchers.append((symbol, class_pattern(pattern)))
            except ValueError as e:
                raise DocumentError("the class '{}': {}".format(symbol, e)) from None
            if declared is not None and symbol not in declared:
                raise DocumentError("the class '{}' is not in {}".format(symbol, FA_INPUT))

    def compute(self):
        """Check the classes and compute the start and the step table."""
        self._compile_classes()
        if self.initial is None:
            raise DocumentError('no initial pseudostate on the top level')
        self._own = {}
        self._starts = {}
        for transition in self.transitions:
            if transition.source in self.initials:
                self._starts[transition.source] = transition
            elif transition.source in self.states:
                self._own.setdefault(transition.source, []).append((transition.symbol, transition))
        self.start_edge = self._entry(None, self.initial, [])
        self.table = {}
        self.accepting = set()
        symbols = []
        for transition in self.transitions:
            if transition.symbol is not None and transition.symbol not in symbols:
                symbols.append(transition.symbol)
        for state in self.states.values():
            if state.composite:
                continue
            for symbol in symbols:
                transition = self._select(state.id, symbol)
                if transition is None:
                    continue
                self.table[(state.id, symbol)] = self._step(state.id, transition)
                if symbol == EOF and transition.target == self.final:
                    self.accepting.add(state.id)

    def _select(self, state, symbol):
        """The transition of the state by the symbol, or of the nearest enclosing state."""
        for ident in reversed(self.chain(state)):
            for own, transition in self._own.get(ident, ()):
                if own == symbol:
                    return transition
        return None

    def _owner(self, source, target):
        """The nearest common ancestor; a transition between a composite state and
        its substate keeps the composite state (PNST 1044, 6.3.2), as in hsmd."""
        if source == target:
            return self.states[source].parent
        ancestors = self.chain(source)
        if target in ancestors:
            return target
        for ident in reversed(self.chain(target)):
            if ident in ancestors:
                return ident
        return None

    def _step(self, state, transition):
        owner = self._owner(transition.source, transition.target)
        exited = []
        for ident in reversed(self.chain(state)):
            if ident == owner:
                break
            exited.append(ident)
        edge = self._entry(owner, transition.target, [transition.id])
        edge.transition = transition.id
        edge.exited = exited
        if transition.output:
            edge.output.insert(0, transition.output)
        return edge

    def _entry(self, owner, target, fired):
        """Enter from the owner down to the target and on along the initials."""
        entered = []
        if target in self.initials:
            fired.append(target)
            transition = self._starts.get(target)
            if transition is None:
                raise DocumentError("the initial pseudostate '{}' has no transition".format(target))
            fired.append(transition.id)
            target = transition.target
        if target == self.final:
            path = [target]
        else:
            path = self.chain(target)
            if owner is not None:
                path = path[path.index(owner) + 1:] if owner in path else path
        entered.extend(path)
        while target in self.states and self.states[target].composite:
            initial = next((i for i, s in self.initials.items() if s == target), None)
            if initial is None:
                raise DocumentError("the composite state '{}' is entered but has no initial "
                                    "pseudostate".format(target))
            transition = self._starts.get(initial)
            if transition is None:
                raise DocumentError("the initial pseudostate '{}' has no transition".format(initial))
            fired.extend([initial, transition.id])
            path = self.chain(transition.target)
            entered.extend(path[path.index(target) + 1:])
            target = transition.target
        output = []
        if target in self.states and self.states[target].output:
            output.append(self.states[target].output)
        return Edge(None, [], entered, output, fired, target)
