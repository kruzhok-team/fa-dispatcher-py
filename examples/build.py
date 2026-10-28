# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The examples: the diagrams built from their descriptions and laid out
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

"""Writes the example diagrams (README.md) into this directory, laid out here: the
states and the comments are placed, the editor draws the transitions."""

import math
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))

# the international Morse code of the letters (README.md, the Morse table)
MORSE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.',
    'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.',
    'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-',
    'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..',
}
CODE_SYMBOLS = {'.': 'DOT', '-': 'DASH'}

STATE_W, STATE_H = 80, 50
LETTER_W, LETTER_H = 44, 40
COMMENT_W = 150
COMMENT_TITLE_H, LINE_H = 36, 20
REGION_MARGIN = 10
TREE_SLOT, TREE_ROW = 80, 140
ENCODER_W = 1160
POINT_RADIUS = 10
LOOP_W, LOOP_H, LOOP_STEP, LOOP_MARGIN = 24, 28, 80, 16
LABEL_GAP = 10
PARALLEL_GAP = 56
RETURN_LABEL_AT = 34
FINAL_ROWS = 1.8

KEYS = '''<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <data key="gFormat">Cyberiada-GraphML-1.0</data>
  <key id="gFormat" for="graphml" attr.name="format" attr.type="string"/>
  <key id="dName" for="graph" attr.name="name" attr.type="string"/>
  <key id="dName" for="node" attr.name="name" attr.type="string"/>
  <key id="dStateMachine" for="graph" attr.name="stateMachine" attr.type="string"/>
  <key id="dRegion" for="graph" attr.name="region" attr.type="string"/>
  <key id="dGeometry" for="graph" attr.name="geometry"/>
  <key id="dGeometry" for="node" attr.name="geometry"/>
  <key id="dGeometry" for="edge" attr.name="geometry"/>
  <key id="dSourcePoint" for="edge" attr.name="sourcePoint"/>
  <key id="dTargetPoint" for="edge" attr.name="targetPoint"/>
  <key id="dLabelGeometry" for="edge" attr.name="labelGeometry"/>
  <key id="dNote" for="node" attr.name="note" attr.type="string"/>
  <key id="dVertex" for="node" attr.name="vertex" attr.type="string"/>
  <key id="dData" for="node" attr.name="data" attr.type="string"/>
  <key id="dData" for="edge" attr.name="data" attr.type="string"/>
'''


class Diagram:
    """An FA diagram: the vertices in the document order, the transitions, the comments."""

    def __init__(self, name):
        self.name = name
        self.vertices = []           # (kind, id, name, parent, entry)
        self.transitions = []        # (id, source, target, text, label_at)
        self.comments = [('CGML_META', 'standardVersion/ 1.0\n\ntype/ fa', None)]
        self.places = {}             # id -> (x, y) or (x, y, w, h), relative to the parent

    def place(self, ident, *geometry):
        self.places[ident] = geometry

    def state(self, ident, name=None, parent=None, entry=None):
        self.vertices.append(('state', ident, name if name is not None else ident, parent, entry))

    def initial(self, ident, parent=None):
        self.vertices.append(('initial', ident, '', parent, None))

    def final(self, ident):
        self.vertices.append(('final', ident, '', None, None))

    def comment(self, name, body, x=None, y=None):
        """A formal comment; placed at x, y it is as high as its lines."""
        rect = None
        if x is not None:
            rect = (x, y, COMMENT_W, COMMENT_TITLE_H + LINE_H * (body.count('\n') + 1))
        self.comments.append((name, body, rect))

    def _geometry(self, ident, pad):
        geometry = self.places.get(ident)
        if geometry is None:
            return []
        if len(geometry) == 2:
            shape = '<point x="{}" y="{}"/>'.format(*geometry)
        else:
            shape = '<rect x="{}" y="{}" width="{}" height="{}"/>'.format(*geometry)
        return ['{}  <data key="dGeometry">'.format(pad), '{}    {}'.format(pad, shape),
                '{}  </data>'.format(pad)]

    def transition(self, source, target, symbol=None, output=None, label_at=None):
        """A transition; label_at puts its label that far from the source on a straight line."""
        base = '{}-{}'.format(source, target)
        ident, n = base, 1
        while any(t[0] == ident for t in self.transitions):
            n += 1
            ident = '{}#{}'.format(base, n)
        text = None if symbol is None else symbol + '/' + ('\n' + output if output else '')
        self.transitions.append((ident, source, target, text, label_at))

    # ------------------------------------------------------------------------
    # the routes: the points of a transition and its label are relative to the
    # top left corner of its source (PNST 1044, 9.1.1), the centre of a point

    def _parent(self, ident):
        return next((v[3] for v in self.vertices if v[1] == ident), None)

    def _box(self, ident):
        """The absolute (x, y, w, h) of a state, (x, y) of a point."""
        geometry = self.places[ident]
        x, y, parent = geometry[0], geometry[1], self._parent(ident)
        while parent is not None:
            x += self.places[parent][0] + REGION_MARGIN
            y += self.places[parent][1] + REGION_MARGIN
            parent = self._parent(parent)
        return (x, y) + tuple(geometry[2:])

    @staticmethod
    def _centre(box):
        return (box[0] + box[2] / 2, box[1] + box[3] / 2) if len(box) == 4 else box

    def _border(self, box, toward):
        cx, cy = self._centre(box)
        dx, dy = toward[0] - cx, toward[1] - cy
        length = math.hypot(dx, dy) or 1.0
        if len(box) == 2:
            t = POINT_RADIUS / length
        else:
            t = min(box[2] / 2 / abs(dx) if dx else math.inf,
                    box[3] / 2 / abs(dy) if dy else math.inf)
        return (cx + t * dx, cy + t * dy)

    def _routes(self):
        """id -> (source point, target point, bends, label), absolute."""
        routes = {}
        loops, pairs = {}, {}
        for ident, source, target, text, _ in self.transitions:
            if text is None or source not in self.places or target not in self.places:
                continue
            if source == target:
                loops.setdefault(source, []).append(ident)
            else:
                pairs.setdefault(tuple(sorted((source, target))), []).append(ident)
        self._loop_routes(loops, routes)
        self._pair_routes(pairs, routes)
        return routes

    def _loop_routes(self, loops, routes):
        """The loops of a state alternate between its top and its bottom."""
        for state, idents in loops.items():
            x, y, _, h = self._box(state)
            for n, ident in enumerate(idents):
                left = x + LOOP_MARGIN + (n // 2) * LOOP_STEP
                edge, out = (y, -1) if n % 2 == 0 else (y + h, 1)
                top = edge + out * LOOP_H
                routes[ident] = ((left, edge), (left + LOOP_W, edge),
                                 [(left, top), (left + LOOP_W, top)],
                                 (left + LOOP_W / 2, top + out * LABEL_GAP))

    def _pair_routes(self, pairs, routes):
        """The transitions between two states bend apart; label_at moves a straight label."""
        ends = {t[0]: (t[1], t[2], t[4]) for t in self.transitions}
        for (first, second), idents in pairs.items():
            a, b = self._centre(self._box(first)), self._centre(self._box(second))
            length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            normal = ((a[1] - b[1]) / length, (b[0] - a[0]) / length)
            for n, ident in enumerate(idents):
                source, target, label_at = ends[ident]
                shift = (n - (len(idents) - 1) / 2) * PARALLEL_GAP
                if shift == 0 and label_at is None:
                    continue
                sbox, tbox = self._box(source), self._box(target)
                if shift == 0:
                    start = self._border(sbox, self._centre(tbox))
                    end = self._border(tbox, self._centre(sbox))
                    along = min(1.0, label_at / (math.hypot(end[0] - start[0],
                                                            end[1] - start[1]) or 1.0))
                    label = (start[0] + (end[0] - start[0]) * along,
                             start[1] + (end[1] - start[1]) * along)
                    routes[ident] = (start, end, [], label)
                    continue
                bend = ((a[0] + b[0]) / 2 + normal[0] * shift, (a[1] + b[1]) / 2 + normal[1] * shift)
                routes[ident] = (self._border(sbox, bend), self._border(tbox, bend), [bend], bend)

    def _origin(self, ident):
        box = self._box(ident)
        return box[0], box[1]

    def _edge_geometry(self, source, target, route):
        sx, sy = self._origin(source)
        tx, ty = self._origin(target)
        start, end, bends, label = route

        def point(p, ox, oy):
            return '<point x="{:.1f}" y="{:.1f}"/>'.format(p[0] - ox, p[1] - oy)

        lines = []
        if bends:
            lines += ['      <data key="dGeometry">'] + \
                ['        ' + point(p, sx, sy) for p in bends] + ['      </data>']
        lines += ['      <data key="dSourcePoint">', '        ' + point(start, sx, sy),
                  '      </data>', '      <data key="dTargetPoint">',
                  '        ' + point(end, tx, ty), '      </data>',
                  '      <data key="dLabelGeometry">', '        ' + point(label, sx, sy),
                  '      </data>']
        return lines

    def _node(self, vertex, indent):
        kind, ident, name, _, entry = vertex
        pad = ' ' * indent
        lines = ['{}<node id="{}">'.format(pad, ident)]
        if kind != 'state':
            lines.append('{}  <data key="dVertex">{}</data>'.format(pad, kind))
            lines.extend(self._geometry(ident, pad))
        else:
            lines.append('{}  <data key="dName">{}</data>'.format(pad, escape(name)))
            if entry:
                lines.append('{}  <data key="dData">entry/\n{}</data>'.format(pad, escape(entry)))
            lines.extend(self._geometry(ident, pad))
            children = [v for v in self.vertices if v[3] == ident]
            if children:
                lines.append('{}  <graph id="{}:" edgedefault="directed">'.format(pad, ident))
                lines.append('{}    <data key="dRegion"/>'.format(pad))
                geometry = self.places.get(ident)
                if geometry is not None:
                    region = (REGION_MARGIN, REGION_MARGIN, geometry[2] - 2 * REGION_MARGIN,
                              geometry[3] - 2 * REGION_MARGIN)
                    lines += ['{}    <data key="dGeometry">'.format(pad),
                              '{}      <rect x="{}" y="{}" width="{}" height="{}"/>'.format(
                                  pad, *region),
                              '{}    </data>'.format(pad)]
                for child in children:
                    lines.extend(self._node(child, indent + 4))
                lines.append('{}  </graph>'.format(pad))
        lines.append('{}</node>'.format(pad))
        return lines

    def xml(self):
        lines = [KEYS.rstrip('\n'), '  <graph id="sm" edgedefault="directed">',
                 '    <data key="dStateMachine"/>',
                 '    <data key="dName">{}</data>'.format(escape(self.name))]
        for n, (name, body, rect) in enumerate(self.comments):
            lines += ['    <node id="{}">'.format('nMeta' if n == 0 else 'c{}'.format(n)),
                      '      <data key="dNote">formal</data>',
                      '      <data key="dName">{}</data>'.format(escape(name)),
                      '      <data key="dData">{}</data>'.format(escape(body))]
            if rect is not None:
                lines += ['      <data key="dGeometry">',
                          '        <rect x="{}" y="{}" width="{}" height="{}"/>'.format(*rect),
                          '      </data>']
            lines.append('    </node>')
        for vertex in self.vertices:
            if vertex[3] is None:
                lines.extend(self._node(vertex, 4))
        routes = self._routes()
        for ident, source, target, text, _ in self.transitions:
            if text is None:
                lines.append('    <edge id="{}" source="{}" target="{}"/>'.format(ident, source,
                                                                               target))
            else:
                lines += ['    <edge id="{}" source="{}" target="{}">'.format(ident, source, target),
                          '      <data key="dData">{}</data>'.format(escape(text))]
                if ident in routes:
                    lines += self._edge_geometry(source, target, routes[ident])
                lines.append('    </edge>')
        lines += ['  </graph>', '</graphml>']
        return '\n'.join(lines) + '\n'


def parity(kind):
    """a) the recognizer of an even number of ones, b) Mealy, c) Moore."""
    names = {'recognizer': 'Even number of ones', 'mealy': 'Parity (Mealy)',
             'moore': 'Running parity (Moore)'}
    d = Diagram(names[kind])
    d.comment('FA_INPUT', '0\n1', 0, -110)
    if kind == 'mealy':
        d.comment('FA_OUTPUT', 'EVEN\nODD', 170, -110)
    elif kind == 'moore':
        d.comment('FA_OUTPUT', '0\n1', 170, -110)
    d.initial('init')
    d.state('Even', entry='0' if kind == 'moore' else None)
    d.state('Odd', entry='1' if kind == 'moore' else None)
    d.final('fin')
    d.place('init', -60, STATE_H // 2)
    d.place('Even', 0, 0, STATE_W, STATE_H)
    d.place('Odd', 240, 0, STATE_W, STATE_H)
    d.place('fin', 160, 160)
    d.transition('init', 'Even')
    d.transition('Even', 'Even', '0')
    d.transition('Even', 'Odd', '1')
    d.transition('Odd', 'Odd', '0')
    d.transition('Odd', 'Even', '1')
    d.transition('Even', 'fin', 'EOF', 'EVEN' if kind == 'mealy' else None)
    if kind != 'recognizer':
        d.transition('Odd', 'fin', 'EOF', 'ODD' if kind == 'mealy' else None)
    return d


def email():
    """[a-z0-9]+([._-][a-z0-9]+)*@[a-z0-9]+(\\.[a-z0-9]+)*\\.[a-z]{2,} over classes."""
    d = Diagram('E-mail address')
    d.comment('CGML_COMPONENT chars', 'type/ Classes\n\nletter/ [a-zA-Zа-яА-ЯёЁ]\n\n'
              'digit/ [0-9]\n\ndot/ \\.\n\nsep/ [_\\-]\n\nat/ @', 0, -260)
    d.comment('FA_INPUT', 'letter\ndigit\ndot\nsep\nat', 170, -260)
    d.initial('init')
    for name in ('Start', 'Local', 'LocalSep', 'At'):
        d.state(name)
    d.state('Domain')
    for name in ('Label', 'T1', 'T2', 'Mid'):
        d.state(name, parent='Domain')
    d.state('Dot')
    d.final('fin')
    places = {'Start': (0, 0), 'Local': (200, 0), 'LocalSep': (200, 220), 'At': (400, 0),
              'Label': (20, 70), 'Mid': (200, 70), 'T1': (20, 270), 'T2': (200, 270),
              'Dot': (640, 480)}
    for name, (x, y) in places.items():
        d.place(name, x, y, STATE_W, STATE_H)
    d.place('init', -60, STATE_H // 2)
    d.place('Domain', 540, -60, 320, 420)
    d.place('fin', 940, 245)
    d.transition('init', 'Start')
    for source, target, symbols in (
            ('Start', 'Local', 'letter digit'), ('Local', 'Local', 'letter digit'),
            ('Local', 'LocalSep', 'dot sep'), ('Local', 'At', 'at'),
            ('LocalSep', 'Local', 'letter digit'), ('At', 'Label', 'letter digit'),
            ('Label', 'Label', 'letter digit'), ('Domain', 'Dot', 'dot'),
            ('Dot', 'T1', 'letter'), ('Dot', 'Mid', 'digit'),
            ('T1', 'T2', 'letter'), ('T1', 'Mid', 'digit'),
            ('T2', 'T2', 'letter'), ('T2', 'Mid', 'digit'), ('T2', 'fin', 'EOF'),
            ('Mid', 'Mid', 'letter digit')):
        for symbol in symbols.split():
            d.transition(source, target, symbol)
    return d


def tree_order():
    """The letters in the order of the Morse tree: DOT before DASH, depth first."""
    def walk(prefix):
        result = []
        for mark in '.-':
            code = prefix + mark
            letter = next((k for k, v in MORSE.items() if v == code), None)
            if letter is not None:
                result.append(letter)
            if any(v.startswith(code) and v != code for v in MORSE.values()):
                result.extend(walk(code))
        return result
    return walk('')


def morse_decoder():
    """The Morse tree: a state remembers the code read so far."""
    d = Diagram('Morse decoder')
    d.comment('CGML_COMPONENT chars', 'type/ Classes\n\nDOT/ \\.\n\nDASH/ \\-\n\nGAP/ [ ]\n\n'
              'WORD/ /', 0, -260)
    d.comment('FA_INPUT', 'DOT\nDASH\nGAP\nWORD', 170, -260)
    d.comment('FA_OUTPUT_RE', '[A-Z]\n/', 340, -260)
    d.initial('init')
    d.state('Ready')
    letters = tree_order()
    for letter in letters:
        d.state(letter)
    d.final('fin')
    # the tree: a code of length L spans 2^(DEPTH-L) leaf slots, DOT left
    depth = max(len(code) for code in MORSE.values())
    for name, code in [('Ready', '')] + [(letter, MORSE[letter]) for letter in letters]:
        span = 2 ** (depth - len(code))
        first = int(code.replace('.', '0').replace('-', '1') or '0', 2) * span
        x = (first + span / 2) * TREE_SLOT
        w, h = (STATE_W, STATE_H) if name == 'Ready' else (LETTER_W, LETTER_H)
        d.place(name, int(x - w / 2), len(code) * TREE_ROW, w, h)
    middle = 2 ** depth * TREE_SLOT // 2
    d.place('init', middle - STATE_W, STATE_H // 2)
    d.place('fin', middle, int((depth + FINAL_ROWS) * TREE_ROW))
    d.transition('init', 'Ready')
    codes = {code: letter for letter, code in MORSE.items()}
    for letter in letters:
        code = MORSE[letter]
        d.transition(codes.get(code[:-1], 'Ready'), letter, CODE_SYMBOLS[code[-1]])
    for letter in letters:
        d.transition(letter, 'Ready', 'GAP', letter, label_at=RETURN_LABEL_AT)
        d.transition(letter, 'fin', 'EOF', letter, label_at=RETURN_LABEL_AT)
    d.transition('Ready', 'Ready', 'WORD', '/')
    d.transition('Ready', 'Ready', 'GAP')
    d.transition('Ready', 'fin', 'EOF')
    return d


def morse_encoder():
    """One state with a loop per row of the Morse table."""
    d = Diagram('Morse encoder')
    d.comment('CGML_COMPONENT chars', 'type/ Classes\n\nWORD/ [ /]', 0, -160)
    d.comment('FA_INPUT_RE', '[A-Z]\nWORD', 170, -160)
    d.comment('FA_OUTPUT_RE', '(\\.|\\-){1,4}\n/', 340, -160)
    d.initial('init')
    d.state('Ready')
    d.final('fin')
    d.place('init', -60, STATE_H // 2)
    d.place('Ready', 0, 0, ENCODER_W, STATE_H)
    d.place('fin', ENCODER_W + 80, STATE_H // 2)
    d.transition('init', 'Ready')
    for letter in sorted(MORSE):
        d.transition('Ready', 'Ready', letter, MORSE[letter])
    d.transition('Ready', 'Ready', 'WORD', '/')
    d.transition('Ready', 'fin', 'EOF')
    return d


EXAMPLES = {
    'parity-recognizer': lambda: parity('recognizer'),
    'parity-mealy': lambda: parity('mealy'),
    'parity-moore': lambda: parity('moore'),
    'email': email,
    'morse-decoder': morse_decoder,
    'morse-encoder': morse_encoder,
}


def main():
    for name, build in EXAMPLES.items():
        path = os.path.join(HERE, name + '.graphml')
        with open(path, 'w', encoding='utf-8') as target:
            target.write(build().xml())
        print(path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
