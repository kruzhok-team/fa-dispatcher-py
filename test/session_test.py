# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The tests of the session: a scripted editor against fad.session
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

"""The session of docs/API.md, Sessions: the editor's messages in, the replies,
the states and the history rows out."""

import io
import json
import os
import sys
import tempfile

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
import fad.session  # pylint: disable=wrong-import-position

DECODER = os.path.join(REPOSITORY, 'examples', 'morse-decoder.graphml')


def request(ident, method, **params):
    return json.dumps({'jsonrpc': '2.0', 'id': ident, 'method': method, 'params': params})


def notification(method, **params):
    return json.dumps({'jsonrpc': '2.0', 'method': method, 'params': params})


def session(*lines):
    """The messages of the session for the editor's lines."""
    out = io.StringIO()
    code = fad.session.serve(fad.Dispatcher(DECODER), io.StringIO('\n'.join(lines) + '\n'), out)
    return code, [json.loads(line) for line in out.getvalue().splitlines()]


def kind(message):
    if 'method' in message:
        return message['method']
    return 'error {}'.format(message['id']) if 'error' in message else 'reply {}'.format(
        message['id'])


def last_state(messages):
    return [m['params'] for m in messages if m.get('method') == 'state'][-1]


def main():
    failed = 0

    def check(name, ok, detail=''):
        nonlocal failed
        print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '\n  ' + str(detail)))
        failed += 0 if ok else 1

    code, messages = session(
        request(1, 'initialize', session=1, editor='1.1.0', language='en', plugin='fa',
                action='tape'),
        request(2, 'input', text='".--- .-"\n'),
        notification('control', command='step', unit='input'),
        notification('control', command='run', speed=1),
        notification('event', name='DOT'),
        notification('control', command='restart'),
        request(3, 'shutdown'))
    kinds = [kind(m) for m in messages]
    check('the exchange', code == 0 and kinds == [
        'reply 1', 'state', 'reply 2', 'state', 'history', 'state'] + ['history'] * 7 +
          ['state', 'log', 'state', 'reply 3'], kinds)
    model = messages[0]['result']
    check('the model', model['logic'] == 'stream' and model['end'] == fad.EOF and
          model['events'] == ['DOT', 'DASH', 'GAP', 'WORD'], model)
    items = messages[2]['result']['items']
    check('the items of a text', items[0] == {'event': 'DOT', 'params': {'text': '.'}} and
          len(items) == 7, items)
    check('a step', messages[3 + 2]['params']['active'] == ['E'] and
          messages[4]['params']['fired'] == ['Ready-E'], messages[3:6])
    final = messages[13]['params']
    check('the verdict of a run', final['status'] == 'finished' and final['verdict'] == 'accepted'
          and final['output'] == ['J', 'A'] and final['active'] == ['fin'], final)
    check('the restart clears the verdict', last_state(messages)['verdict'] == '' and
          last_state(messages)['output'] == [], last_state(messages))

    code, messages = session(
        request(1, 'initialize'),
        request(2, 'input', text='"abc'),
        notification('event', name='DASH'),
        notification('event', name='DASH'),
        notification('event', name='DASH'),
        notification('event', name='EOF'),
        request(3, 'unknown'))
    error = next(m for m in messages if m.get('id') == 2)
    check('a wrong tape', error['error']['code'] == fad.session.INVALID_PARAMS and
          error['error']['data'][0]['line'] == 1, error)
    final = last_state(messages)
    check('the user symbols and the end button', final['verdict'] == 'accepted' and
          final['output'] == ['O'], final)
    rows = [m['params'] for m in messages if m.get('method') == 'history']
    check('the origin user', all(r['origin'] == 'user' for r in rows) and len(rows) == 4, rows)
    check('an unknown request', messages[-1].get('error', {}).get('code') ==
          fad.session.METHOD_NOT_FOUND, messages[-1])

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, 'saved.tape')
        code, messages = session(
            request(1, 'initialize'), request(2, 'input', text='".-.- .--"'),
            notification('control', command='run'), request(3, 'save', path=path))
        final = last_state(messages)
        check('a rejection', final['verdict'] == 'rejected' and
              final['text'] == 'rejected at 3: R has no DASH', final)
        with open(path, encoding='utf-8') as source:
            saved = source.read()
        check('the saved tape', saved == 'DOT\nDASH\nDOT\nDASH\n', saved)
    if failed:
        print('{} failed'.format(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
