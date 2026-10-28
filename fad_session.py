# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The session: an automaton served to the CyberiadaPro editor step by step
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

"""A driven session with the stream logic (docs/API.md, Sessions): JSON-RPC 2.0
lines on stdin and stdout. There is no clock, so a run goes to its verdict at once."""

import json
import sys

import fad
import fad_tape

METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

PAUSED = 'paused'
FINISHED = 'finished'
INPUT = 'input'
USER = 'user'
TEXT = 'text'


class Session:
    """The tape, its position and the run of one dispatcher."""

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.tape = []               # (symbol, character of a text or None)
        self.position = 0
        self.inputs = []             # the symbols handled, for save
        self.last = None             # the last Step
        self.out = None
        self.done = False

    # ------------------------------------------------------------------------
    # the channel

    def serve(self, reader=None, writer=None):
        """Run the session until shutdown or the end of the input; the exit code."""
        reader = reader if reader is not None else sys.stdin
        self.out = writer if writer is not None else sys.stdout
        for line in reader:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict):
                self.handle(message)
            if self.done:
                break
        return 0

    def send(self, message):
        message = dict(message, jsonrpc='2.0')
        self.out.write(json.dumps(message, ensure_ascii=False, separators=(',', ':')) + '\n')
        self.out.flush()

    def notify(self, method, params):
        self.send({'method': method, 'params': params})

    def reply(self, ident, result):
        if ident is not None:
            self.send({'id': ident, 'result': result})

    def reply_error(self, ident, code, text, data=None):
        error = {'code': code, 'message': text}
        if data is not None:
            error['data'] = data
        if ident is not None:
            self.send({'id': ident, 'error': error})

    def log(self, text, level=None):
        params = {'text': text}
        if level is not None:
            params['level'] = level
        self.notify('log', params)

    def handle(self, message):
        method = message.get('method')
        ident = message.get('id')
        params = message.get('params')
        params = params if isinstance(params, dict) else {}
        if method is None:
            return                   # a reply: the session asks nothing
        if method == 'initialize':
            self.initialize(ident)
        elif method == 'control':
            self.control(params)
        elif method == 'event':
            self.event(params)
        elif method == 'input':
            self.input(ident, params)
        elif method == 'save':
            self.save(ident, params)
        elif method == 'shutdown':
            self.reply(ident, {})
            self.done = True
        elif ident is not None:
            self.reply_error(ident, METHOD_NOT_FOUND, 'unknown method {}'.format(method))

    # ------------------------------------------------------------------------
    # the messages

    def initialize(self, ident):
        automaton = self.dispatcher.automaton
        self.reply(ident, {'kind': 'driven', 'logic': 'stream', 'steps': [INPUT],
                           'controls': ['step', 'run', 'restart'], 'events': automaton.events(),
                           'end': fad.EOF, 'stream': True, 'save': True, 'verdict': True,
                           'output': True})
        self.restart()

    def control(self, params):
        command = params.get('command')
        if command == 'restart':
            self.restart()
        elif command == 'step':
            self.report(self.step())
        elif command == 'run':
            while self.dispatcher.running:
                self.step()
            self.report(self.last)

    def event(self, params):
        name = params.get('name')
        if not isinstance(name, str) or not name:
            return
        if not self.dispatcher.running:
            self.log('the run has its verdict: Restart starts it again', 'warning')
            return
        self.report(self.feed(name, None, USER))

    def input(self, ident, params):
        text = params.get('text')
        if isinstance(params.get('path'), str):
            try:
                with open(params['path'], encoding='utf-8') as source:
                    text = source.read()
            except OSError as e:
                self.reply_error(ident, INVALID_PARAMS, 'the tape cannot be read: {}'.format(e))
                return
        try:
            items = fad_tape.read(text if isinstance(text, str) else '')
        except fad.TapeError as e:
            self.reply_error(ident, INVALID_PARAMS, 'the tape is not read',
                             [{'line': e.line, 'message': e.message}])
            return
        self.tape = []
        for item in items:
            if item.kind == fad_tape.TEXT:
                self.tape.extend(zip(self.dispatcher.classify(item.value), item.value))
            else:
                self.tape.append((item.value, None))
        self.reply(ident, {'items': [self.item(symbol, character)
                                     for symbol, character in self.tape]})
        # the session starts again with the tape (docs/PLUGIN-API.md, Sessions)
        self.restart()

    def save(self, ident, params):
        path = params.get('path')
        items = [fad_tape.Item(fad_tape.SYMBOL, symbol) for symbol in self.inputs]
        try:
            with open(path, 'w', encoding='utf-8') as target:
                target.write(fad_tape.write(items))
        except (OSError, TypeError) as e:
            self.reply_error(ident, INTERNAL_ERROR, 'the tape cannot be written: {}'.format(e))
            return
        self.reply(ident, {})

    # ------------------------------------------------------------------------
    # the run

    @staticmethod
    def item(symbol, character):
        entry = {'event': symbol}
        if character is not None:
            entry['params'] = {TEXT: character}
        return entry

    def restart(self):
        self.position = 0
        self.inputs = []
        self.last = None
        step = self.dispatcher.start()
        self.report(None, fired=step.fired, restart=True)

    def step(self):
        """The next symbol of the tape; after the last one, EOF."""
        if not self.dispatcher.running:
            return None
        if self.position < len(self.tape):
            symbol, character = self.tape[self.position]
            self.position += 1
            return self.feed(symbol, character, INPUT)
        return self.feed(fad.EOF, None, INPUT)

    def feed(self, symbol, character, origin):
        position = self.dispatcher.position
        step = self.dispatcher.feed(symbol)
        self.last = step
        self.inputs.append(symbol)
        row = {'event': symbol, 'position': position, 'origin': origin,
               'outcome': step.status, 'fired': step.fired}
        if character is not None:
            row['params'] = {TEXT: character}
        self.notify('history', row)
        return step

    def report(self, step, fired=None, restart=False):
        """The state after a step; a run sends it once at its end."""
        d = self.dispatcher
        params = {'status': PAUSED if d.running else FINISHED,
                  'active': d.states(), 'events': d.symbols(), 'output': list(d.output),
                  'position': self.position}
        if fired is not None:
            params['fired'] = fired
        elif step is not None:
            params['fired'] = step.fired
        if d.verdict is not None:
            params['verdict'] = d.verdict
            params['text'] = self.message()
        elif restart:
            params['verdict'] = ''
            params['text'] = ''
        self.notify('state', params)

    def message(self):
        """The verdict as fa-run reports it: rejected at 3: R has no DASH."""
        d = self.dispatcher
        steps = [self.last] if self.last is not None else []
        reason = self.last.reason if self.last is not None else None
        return fad.Result(d.verdict, d.output, d.position, d.state(), reason, steps).message


def serve(dispatcher, reader=None, writer=None):
    """Serve the dispatcher to the editor over stdin and stdout; the exit code."""
    return Session(dispatcher).serve(reader, writer)
