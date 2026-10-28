# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The tapes: the tape files and the tests files
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

"""The tape files (a symbol or a quoted text per line) and the tests files (+ or -,
a tape, => the expected output) of docs/API.md, Tapes and tests files."""

from fad_model import ACCEPTED, REJECTED, TapeError

SYMBOL = 'symbol'
TEXT = 'text'
COMMENT = '#'
QUOTE = '"'
ARROW = '=>'
SIGNS = {'+': ACCEPTED, '-': REJECTED}


class Item:
    """An item of a tape: a symbol or a text."""

    def __init__(self, kind, value, line=None):
        self.kind = kind
        self.value = value
        self.line = line


class Test:
    """A line of a tests file; output None is not checked."""

    def __init__(self, line, verdict, items, output):
        self.line = line
        self.verdict = verdict
        self.items = items
        self.output = output


class Failure:
    """A test whose result differs from the expected one."""

    def __init__(self, test, result, message):
        self.test = test
        self.result = result
        self.message = message


def _lines(text):
    for number, line in enumerate(text.split('\n'), 1):
        line = line.strip()
        if line and not line.startswith(COMMENT):
            yield number, line


def read(text):
    """The items of a tape file."""
    items = []
    for number, line in _lines(text):
        if line.startswith(QUOTE):
            if len(line) < 2 or not line.endswith(QUOTE):
                raise TapeError(number, 'a text without its closing quote')
            items.append(Item(TEXT, line[1:-1], number))
        else:
            items.append(Item(SYMBOL, line, number))
    return items


def write(items):
    """The text of a tape file."""
    return ''.join((QUOTE + item.value + QUOTE if item.kind == TEXT else item.value) + '\n'
                   for item in items)


def symbols(items, classify):
    """The symbols of the items; a text through classify."""
    result = []
    for item in items:
        if item.kind == TEXT:
            result.extend(classify(item.value))
        else:
            result.append(item.value)
    return result


def read_tests(text):
    """The tests of a tests file."""
    tests = []
    for number, line in _lines(text):
        if line[0] not in SIGNS:
            raise TapeError(number, 'a test starts with + or -')
        rest = line[1:].strip()
        if rest.startswith(QUOTE):
            close = rest.rfind(QUOTE)
            if close == 0:
                raise TapeError(number, 'a text without its closing quote')
            items = [Item(TEXT, rest[1:close], number)]
            tail = rest[close + 1:].strip()
        else:
            tape, arrow, after = rest.partition(ARROW)
            items = [Item(SYMBOL, symbol, number) for symbol in tape.split()]
            tail = arrow + after
        if tail and not tail.startswith(ARROW):
            raise TapeError(number, "'{}' after the text".format(tail))
        output = tail[len(ARROW):].split() if tail else None
        tests.append(Test(number, SIGNS[line[0]], items, output))
    return tests


def _described(verdict, output):
    return verdict + (' => ' + ' '.join(output) if output is not None else '')


def check(dispatcher, tests):
    """The failures of the tests run on the dispatcher."""
    failures = []
    for test in tests:
        result = dispatcher.run(symbols(test.items, dispatcher.classify))
        if result.verdict != test.verdict or \
                (test.output is not None and result.output != test.output):
            expected = _described(test.verdict, test.output)
            actual = _described(result.message, result.output if test.output is not None else None)
            failures.append(Failure(test, result, 'expected {}, got {}'.format(expected, actual)))
    return failures
