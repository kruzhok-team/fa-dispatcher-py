# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The dispatcher: the run of a tape and the public interface
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

"""The FA dispatcher (docs/API.md): a deterministic finite automaton diagram of
CyberiadaML-GraphML (type/ fa) runs a tape of symbols to its verdict and output."""

from fad.model import (EOF, ACCEPTED, REJECTED, FIRED, FA_INPUT, FAError, DocumentError,
                       TapeError, StoppedError, Automaton)

__all__ = ['Dispatcher', 'Automaton', 'read', 'Step', 'Result', 'ACCEPTED', 'REJECTED',
           'FIRED', 'EOF', 'FAError', 'DocumentError', 'TapeError', 'StoppedError']


def _shown(symbol):
    """A symbol in a reason: quoted when it is empty or has a space."""
    return "'{}'".format(symbol) if not symbol or any(c.isspace() for c in symbol) else symbol


def read(path):
    """The Automaton of a CyberiadaML document."""
    from fad import reader  # pylint: disable=import-outside-toplevel
    return reader.read(path)


class Step:
    """A step of a run: the start (symbol None), a symbol, or EOF."""

    def __init__(self, symbol, position, status=FIRED, transition=None, exited=(), entered=(),
                 output=(), fired=(), reason=None, verdict=None):
        self.symbol = symbol
        self.position = position
        self.status = status
        self.transition = transition
        self.exited = list(exited)
        self.entered = list(entered)
        self.output = list(output)
        self.fired = list(fired)
        self.reason = reason
        self.verdict = verdict


class Result:
    """The result of run()."""

    def __init__(self, verdict, output, position, state, reason, steps):
        self.verdict = verdict
        self.output = output
        self.position = position
        self.state = state
        self.reason = reason
        self.steps = steps

    @property
    def message(self):
        if self.verdict == ACCEPTED:
            return ACCEPTED
        last = self.steps[-1] if self.steps else None
        where = EOF if last is not None and last.symbol == EOF else str(self.position)
        return '{} at {}: {}'.format(REJECTED, where, self.reason)


class Dispatcher:
    """Runs the automaton of a document (a path) or an Automaton."""

    def __init__(self, source, trace=None):
        self.automaton = source if isinstance(source, Automaton) else read(source)
        self.trace = trace
        self.position = 0
        self.output = []
        self.verdict = None
        self.running = False
        self._state = None

    def _record(self, *record):
        if self.trace is not None:
            self.trace(record)

    def _apply(self, edge):
        for ident in edge.exited:
            self._record('exit', ident)
        if edge.transition is not None:
            self._record('fire', edge.transition)
        for ident in edge.entered:
            self._record('enter', ident)
        for symbol in edge.output:
            self._record('output', symbol)
        self.output.extend(edge.output)
        self._state = edge.state

    def _reject(self, symbol, reason):
        self.verdict = REJECTED
        self.running = False
        self._record('rejected', self.position, reason)
        return Step(symbol, self.position, REJECTED, reason=reason, verdict=REJECTED)

    def _check(self):
        if not self.running:
            raise StoppedError('no running run: ' + ('the verdict is given' if self.verdict
                                                     else 'start() first'))

    # ------------------------------------------------------------------------
    # the run

    def start(self):
        """A new run: the initial transitions and the output of the initial state."""
        edge = self.automaton.start_edge
        self.position = 0
        self.output = []
        self.verdict = None
        self.running = True
        self._record('start', edge.state)
        self._apply(edge)
        return Step(None, 0, FIRED, None, [], edge.entered, edge.output, edge.fired)

    def feed(self, symbol):
        """Read one symbol; feed(EOF) is end()."""
        if symbol == EOF:
            return self.end()
        self._check()
        self._record('symbol', symbol, self.position)
        edge = self.automaton.edge(self._state, symbol)
        if edge is None:
            declared = self.automaton.input_symbols()
            if declared is not None and symbol not in declared:
                reason = '{} is not in {}'.format(_shown(symbol), FA_INPUT)
            else:
                reason = '{} has no {}'.format(self.automaton.label(self._state), _shown(symbol))
            return self._reject(symbol, reason)
        position = self.position
        self._apply(edge)
        self.position += 1
        return Step(symbol, position, FIRED, edge.transition, edge.exited, edge.entered,
                    edge.output, edge.fired)

    def end(self):
        """The end of the tape: EOF to the final state accepts."""
        self._check()
        self._record('symbol', EOF, self.position)
        edge = self.automaton.edge(self._state, EOF)
        if edge is None or edge.state != self.automaton.final:
            return self._reject(EOF, '{} is not accepting'.format(
                self.automaton.label(self._state)))
        self._apply(edge)
        self.verdict = ACCEPTED
        self.running = False
        self._record('accepted')
        return Step(EOF, self.position, FIRED, edge.transition, edge.exited, edge.entered,
                    edge.output, edge.fired, verdict=ACCEPTED)

    def run(self, tape):
        """start(), feed() for every symbol up to a rejection, end(): the Result."""
        steps = [self.start()]
        for symbol in tape:
            steps.append(self.feed(symbol))
            if not self.running:
                break
        if self.running:
            steps.append(self.end())
        return Result(self.verdict, list(self.output), self.position, self._state,
                      steps[-1].reason, steps)

    # ------------------------------------------------------------------------
    # the queries

    def classify(self, text):
        """The characters of a text through the classes of the diagram."""
        return self.automaton.classify(text)

    def state(self):
        """The active simple state; after the verdict, where the run stopped."""
        return self._state

    def states(self):
        """The active state and the composite states around it, the outermost first."""
        return self.automaton.chain(self._state) if self._state is not None else []

    def symbols(self):
        """The symbols the active state reads, EOF aside."""
        return self.automaton.symbols(self._state) if self._state is not None else []

    def accepting(self):
        """Whether end() would accept now."""
        return self.running and self._state in self.automaton.accepting
