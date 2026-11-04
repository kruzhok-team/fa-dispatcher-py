# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The tests: the examples, the compat-tests diagrams, the parts and the oracle
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

"""The tests (docs/ARCHITECTURE.md, Testing). FAD_BACKEND=cml runs them on the
pure-Python interface of cyberiadaml-py beside an installed binding."""

import contextlib
import glob
import io
import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.dirname(TEST_DIR)
sys.path.insert(0, REPOSITORY)

SKIPPED = 77

if os.environ.get('FAD_BACKEND') == 'cml':
    try:
        from cyberiadaml_py import cml  # pylint: disable=wrong-import-position
    except ImportError:
        print('skipped: no cyberiadaml-py')
        sys.exit(SKIPPED)
    sys.modules['CyberiadaML'] = cml

import fad  # pylint: disable=wrong-import-position
import fad_cli  # pylint: disable=wrong-import-position
import fad_model  # pylint: disable=wrong-import-position
import fad_tape  # pylint: disable=wrong-import-position

EXAMPLES_DIR = os.path.join(REPOSITORY, 'examples')
COMPAT_TESTS_DIR = os.path.join(TEST_DIR, 'compat')
COMPAT_DIR = os.path.join(REPOSITORY, '..', 'cyberiadaml-compat-tests', 'fixtures')
HSMD_DIR = os.path.join(REPOSITORY, '..', 'hsm-dispatcher-py')


class Report:
    """The ok and FAIL lines, the count of the failures."""

    def __init__(self):
        self.failed = 0

    def check(self, name, ok, detail=''):
        if ok:
            print('ok   {}'.format(name))
        else:
            self.failed += 1
            print('FAIL {}{}'.format(name, '\n' + detail if detail else ''))


def tests_files():
    """(diagram, tests file) of the examples and of the compat-tests diagrams found."""
    pairs = [(path[:-len('.tests')] + '.graphml', path)
             for path in sorted(glob.glob(os.path.join(EXAMPLES_DIR, '*.tests')))]
    if os.path.isdir(COMPAT_DIR):
        for path in sorted(glob.glob(os.path.join(COMPAT_TESTS_DIR, '*.tests'))):
            name = os.path.basename(path)[:-len('.tests')]
            pairs.append((os.path.join(COMPAT_DIR, 'fa', name + '.graphml'), path))
    return pairs


def run_tests_files(report):
    for diagram, path in tests_files():
        with open(path, encoding='utf-8') as source:
            tests = fad_tape.read_tests(source.read())
        failures = fad_tape.check(fad.Dispatcher(diagram), tests)
        report.check(os.path.relpath(path, REPOSITORY), not failures,
                     '\n'.join('  line {}: {}'.format(f.test.line, f.message) for f in failures))


@contextlib.contextmanager
def quiet_stderr():
    """The C library reports a refused document on the stderr of the process."""
    sys.stderr.flush()
    saved = os.dup(2)
    with open(os.devnull, 'w', encoding='utf-8') as null:
        os.dup2(null.fileno(), 2)
        try:
            yield
        finally:
            os.dup2(saved, 2)
            os.close(saved)


def run_negatives(report):
    if not os.path.isdir(COMPAT_DIR):
        print('skipped the negatives: no cyberiadaml-compat-tests beside this repository')
        return
    accepted = []
    negatives = sorted(glob.glob(os.path.join(COMPAT_DIR, 'negative', 'X-FA-*.graphml')))
    with quiet_stderr():
        for path in negatives:
            try:
                fad.read(path)
                accepted.append(os.path.basename(path))
            except fad.DocumentError:
                pass
    report.check('the {} X-FA negatives are refused'.format(len(negatives)),
                 negatives and not accepted, '  accepted: ' + ' '.join(accepted))


# ----------------------------------------------------------------------------
# the parts


def expect_error(error, operation):
    try:
        operation()
    except error:
        return True
    return False


def run_parts(report):
    good = ['a', '@', 'я', '.', '\\.', '\\-', '\\\\', '[a-z0-9_]', '[ ]', '[_\\-]', '[а-яё]']
    bad = ['ab', '-', '[a-]', '[]', '\\a', '[z-a]', '[a', '[[]']
    wrong = [p for p in good if expect_error(ValueError, lambda p=p: fad_model.class_pattern(p))]
    wrong += [p for p in bad if not expect_error(ValueError, lambda p=p: fad_model.class_pattern(p))]
    report.check('the class patterns', not wrong, '  ' + ' '.join(wrong))
    pattern = fad_model.class_pattern('[_\\-]')
    report.check('a bracket pattern matches its characters',
                 pattern.fullmatch('-') and pattern.fullmatch('_') and not pattern.fullmatch('a'))

    items = fad_tape.read('# a comment\nDOT\n\n  "a b"  \nDASH\n')
    report.check('a tape file', [(i.kind, i.value, i.line) for i in items] ==
                 [('symbol', 'DOT', 2), ('text', 'a b', 4), ('symbol', 'DASH', 5)])
    report.check('a tape file written and read back',
                 [i.value for i in fad_tape.read(fad_tape.write(items))] == ['DOT', 'a b', 'DASH'])
    errors = [text for text in ('"abc', 'x 1', '+ "a" b', '+ "a')
              if not expect_error(fad.TapeError, lambda t=text: fad_tape.read_tests(t)
                                  if not t.startswith('"') else fad_tape.read(t))]
    report.check('the wrong tape and tests lines', not errors, '  ' + ' | '.join(errors))
    tests = fad_tape.read_tests('+ => EVEN\n- 1 0 2\n+ "a b" => x y\n')
    report.check('a tests file', [(t.verdict, [i.value for i in t.items], t.output) for t in tests] ==
                 [('accepted', [], ['EVEN']), ('rejected', ['1', '0', '2'], None),
                  ('accepted', ['a b'], ['x', 'y'])])

    nested = os.path.join(COMPAT_DIR, 'fa', 'F-FA-NESTED.graphml')
    if os.path.isfile(nested):
        trace = []
        d = fad.Dispatcher(nested, trace=trace.append)
        report.check('feed() before start()', expect_error(fad.StoppedError, lambda: d.feed('a')))
        d.start()
        d.feed('a')
        report.check('the active states, the symbols, accepting',
                     d.states() == ['c0', 'c1'] and d.symbols() == ['b'] and d.accepting(),
                     '  {} {} {}'.format(d.states(), d.symbols(), d.accepting()))
        step = d.feed(fad.EOF)
        report.check('feed(EOF) ends the tape', step.verdict == fad.ACCEPTED and d.state() == 'fin')
        report.check('feed() after the verdict', expect_error(fad.StoppedError, lambda: d.feed('a')))
        report.check('the trace', trace == [
            ('start', 'q0'), ('enter', 'q0'), ('symbol', 'a', 0), ('exit', 'q0'), ('fire', 'q0-c0'),
            ('enter', 'c0'), ('enter', 'c1'), ('symbol', 'EOF', 1), ('exit', 'c1'), ('exit', 'c0'),
            ('fire', 'c0-fin'), ('enter', 'fin'), ('accepted',)], '  {}'.format(trace))
        first = d.start()
        report.check('the start step', first.fired == ['init', 'init-q0'] and first.entered == ['q0'])
    with quiet_stderr():
        report.check('a document without type/ fa', expect_error(
            fad.DocumentError, lambda: fad.read(os.path.join(TEST_DIR, 'not-fa.graphml'))))


# ----------------------------------------------------------------------------
# the command line


def cli(argv, stdin=''):
    out, err = io.StringIO(), io.StringIO()
    saved = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = fad_cli.main(argv)
            except SystemExit as e:  # an argparse error is a FAIL with its message
                code = e.code
    finally:
        sys.stdin = saved
    return code, out.getvalue(), err.getvalue()


def run_cli(report):
    def example(name):
        return os.path.join(EXAMPLES_DIR, name + '.graphml')

    result = cli([example('parity-mealy'), '1', '0', '1', '1'])
    report.check('fa-run symbols', result == (0, 'ODD\n', 'accepted\n'), '  {}'.format(result))
    result = cli([example('email'), '--text', 'a@b.c'])
    report.check('fa-run --text rejected', result == (1, '\n', 'rejected at EOF: T1 is not accepting\n'),
                 '  {}'.format(result))
    result = cli([example('morse-decoder'), '--tape', os.path.join(EXAMPLES_DIR, 'sos.tape'),
                  '--join'])
    report.check('fa-run --tape --join', result == (0, 'SOS\n', 'accepted\n'), '  {}'.format(result))
    code, encoded, _ = cli([example('morse-encoder'), '--text', 'JA'])
    result = cli([example('morse-decoder'), '--text', '-', '--join'], encoded)
    report.check('fa-run the encoder piped into the decoder',
                 encoded == '.--- .-\n' and result == (0, 'JA\n', 'accepted\n'),
                 '  {!r} {}'.format(encoded, result))
    result = cli([example('email'), '--test', os.path.join(EXAMPLES_DIR, 'email.tests')])
    report.check('fa-run --test', result[0] == 0 and result[2].endswith('11 passed\n'),
                 '  {}'.format(result))
    result = cli([os.path.join(TEST_DIR, 'not-fa.graphml'), '1'])
    report.check('fa-run a wrong document', result[0] == fad_cli.EXIT_ERROR, '  {}'.format(result))
    code, _, trace = cli([example('parity-recognizer'), '--trace', '1'])
    report.check('fa-run --trace', code == 1 and 'fire Even-Odd' in trace and
                 trace.endswith('rejected at EOF: Odd is not accepting\n'), '  ' + trace)


# ----------------------------------------------------------------------------
# the oracle: the same automata on hsmd, the outputs as functions


def find_hsmd():
    try:
        import hsmd  # pylint: disable=import-outside-toplevel
        return hsmd
    except ImportError:
        pass
    if os.path.isdir(HSMD_DIR):
        sys.path.append(HSMD_DIR)
        try:
            import hsmd  # pylint: disable=import-outside-toplevel
            return hsmd
        except ImportError:
            return None
    return None


def hsmd_machine(hsmd, automaton, output):
    def writer(symbol):
        return (lambda: output.append(symbol)) if symbol else None

    def vertices(parent):
        result = [hsmd.Initial(id=ident) for ident, state in automaton.initials.items()
                  if state == parent]
        for state in automaton.states.values():
            if state.parent == parent:
                result.append(hsmd.State(state.name or state.id, id=state.id,
                                         entry=writer(state.output),
                                         states=vertices(state.id) if state.composite else ()))
        return result

    states = vertices(None)
    if automaton.final is not None:
        states.append(hsmd.Final(id=automaton.final))
    transitions = [hsmd.Transition(t.source, t.target, t.symbol or '', action=writer(t.output),
                                   id=t.id) for t in automaton.transitions]
    return hsmd.Machine(automaton.name or 'FA', states=states, transitions=transitions)


def hsmd_run(hsmd, automaton, tape):
    output = []
    dispatcher = hsmd.Dispatcher(hsmd_machine(hsmd, automaton, output))
    dispatcher.start()
    for symbol in tape:
        if dispatcher.send(symbol).status != hsmd.FIRED:
            return fad.REJECTED, output
    outcome = dispatcher.send(fad.EOF)
    verdict = fad.ACCEPTED if outcome.status == hsmd.FIRED and dispatcher.finished() else fad.REJECTED
    return verdict, output


def run_oracle(report):
    hsmd = find_hsmd()
    if hsmd is None:
        print('skipped the oracle: no hsmd')
        return
    for diagram, path in tests_files():
        dispatcher = fad.Dispatcher(diagram)
        with open(path, encoding='utf-8') as source:
            tests = fad_tape.read_tests(source.read())
        differ = []
        for test in tests:
            tape = fad_tape.symbols(test.items, dispatcher.classify)
            result = dispatcher.run(tape)
            expected = hsmd_run(hsmd, dispatcher.automaton, tape)
            if (result.verdict, result.output) != expected:
                differ.append('  line {}: fad {} {}, hsmd {} {}'.format(
                    test.line, result.verdict, result.output, *expected))
        report.check('oracle ' + os.path.relpath(path, REPOSITORY), not differ, '\n'.join(differ))


def main():
    report = Report()
    run_tests_files(report)
    run_negatives(report)
    run_parts(report)
    run_cli(report)
    run_oracle(report)
    if report.failed:
        print('{} failed'.format(report.failed))
    return 1 if report.failed else 0


if __name__ == '__main__':
    sys.exit(main())
