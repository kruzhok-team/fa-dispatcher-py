# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  fa-run: the command line
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

"""fa-run (docs/API.md, The command line): the output on stdout, the verdict on
stderr, so one automaton pipes into another."""

import argparse
import json
import sys

import fad
import fad_plugin
import fad_tape

EXIT_ACCEPTED = 0
EXIT_REJECTED = 1
EXIT_ERROR = 2
STDIN = '-'
INSTALL = '--install-editor-plugin'


def _read(path):
    if path == STDIN:
        return sys.stdin.read()
    with open(path, encoding='utf-8') as source:
        return source.read()


def _drop_newline(text):
    """A text from stdin without its last newline."""
    if text.endswith('\r\n'):
        return text[:-2]
    return text[:-1] if text.endswith('\n') else text


def _trace(record):
    print(' '.join(str(item) for item in record), file=sys.stderr)


def _write_diagnostics(path, diagnostics):
    """The findings of the editor (docs/API.md, The command line)."""
    with open(path, 'w', encoding='utf-8') as target:
        json.dump(diagnostics, target, ensure_ascii=False, indent=1)


def _test(dispatcher, path, diagnostics=None):
    try:
        tests = fad_tape.read_tests(_read(path))
    except fad.TapeError as e:
        if diagnostics:
            _write_diagnostics(diagnostics, [{'severity': 'error', 'message': '{}: {}'.format(
                path, e)}])
        raise
    failures = fad_tape.check(dispatcher, tests)
    for failure in failures:
        print('{}:{}: {}'.format(path, failure.test.line, failure.message), file=sys.stderr)
    passed = len(tests) - len(failures)
    summary = '{} passed'.format(passed) + (', {} failed'.format(len(failures)) if failures else '')
    print(summary, file=sys.stderr)
    if diagnostics:
        findings = [{'severity': 'error', 'element': failure.result.state,
                     'message': 'line {}: {}'.format(failure.test.line, failure.message)}
                    for failure in failures]
        _write_diagnostics(diagnostics, findings or [{'severity': 'info', 'message': summary}])
    return EXIT_REJECTED if failures else EXIT_ACCEPTED


def install_plugin(argv):
    """The --install-editor-plugin [DIR] command."""
    index = argv.index(INSTALL)
    target = argv[index + 1] if index + 1 < len(argv) else None
    try:
        folder = fad_plugin.install(target or None)
    except fad_plugin.PluginError as e:
        print('fa-run: {}'.format(e), file=sys.stderr)
        return EXIT_ERROR
    print('installed the editor plugin {} to\n  {}\nit runs {}; restart the editor'.format(
        fad_plugin.PLUGIN_ID, folder, sys.executable))
    return EXIT_ACCEPTED


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if INSTALL in argv:
        return install_plugin(argv)
    parser = argparse.ArgumentParser(
        prog='fa-run', description='Run a finite automaton diagram (type/ fa) on a tape.')
    parser.add_argument('diagram', help='the CyberiadaML document')
    parser.add_argument('symbols', nargs='*', help='a tape of symbols')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--text', help='a text, one symbol per character through the classes; '
                        '"-" reads stdin')
    source.add_argument('--tape', help='a tape file; "-" reads stdin')
    source.add_argument('--test', help='a tests file')
    source.add_argument('--session', action='store_true',
                        help='serve the editor session over stdin and stdout')
    parser.add_argument('--diagnostics', metavar='FILE',
                        help='with --test: the failures as the findings of the editor')
    parser.add_argument('--join', action='store_true',
                        help='the output without spaces between the symbols')
    parser.add_argument('--trace', action='store_true', help='the trace records on stderr')
    parser.add_argument(INSTALL, metavar='DIR', nargs='?', const='',
                        help='copy the editor plugin into the plugin folder of the editor '
                             '(or into DIR) and exit')
    args = parser.parse_args(argv)
    if args.symbols and (args.text is not None or args.tape or args.test or args.session):
        parser.error('the symbols go without --text, --tape, --test and --session')
    try:
        dispatcher = fad.Dispatcher(args.diagram, trace=_trace if args.trace else None)
        if args.session:
            import fad_session  # pylint: disable=import-outside-toplevel
            return fad_session.serve(dispatcher)
        if args.test:
            return _test(dispatcher, args.test, args.diagnostics)
        if args.text is not None:
            text = _drop_newline(_read(STDIN)) if args.text == STDIN else args.text
            tape = dispatcher.classify(text)
        elif args.tape:
            tape = fad_tape.symbols(fad_tape.read(_read(args.tape)), dispatcher.classify)
        else:
            tape = args.symbols
    except (fad.FAError, OSError) as e:
        print('fa-run: {}'.format(e), file=sys.stderr)
        return EXIT_ERROR
    result = dispatcher.run(tape)
    print(('' if args.join else ' ').join(result.output))
    print(result.message, file=sys.stderr)
    return EXIT_ACCEPTED if result.verdict == fad.ACCEPTED else EXIT_REJECTED


if __name__ == '__main__':
    sys.exit(main())
