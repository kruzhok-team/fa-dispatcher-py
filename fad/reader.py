# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The reader: a CyberiadaML document into the automaton
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

"""Opens a document with the CyberiadaML module - the binding of libcyberiadamlpp-py,
else the pure-Python interface of cyberiadaml-py - and builds the Automaton."""

try:
    import CyberiadaML
except ImportError:
    from cyberiadaml_py import cml as CyberiadaML

from fad.model import (DocumentError, Automaton, State, Transition, INPUT_NAMES,
                       OUTPUT_NAMES)

META_NAME = 'CGML_META'
META_TYPE = 'type'
META_TYPE_FA = 'fa'
COMPONENT_PREFIX = 'CGML_COMPONENT '
PARAMETER_SEPARATOR = '/'
PARAMETER_TYPE = 'type'
CLASSES_TYPE = 'Classes'

_STATES = (CyberiadaML.elementSimpleState, CyberiadaML.elementCompositeState)


def parse_parameters(body):
    """The name/value blocks of a formal comment (PNST 1044, 6.9, 10.3.1), as in hsmd."""
    parameters = []
    name = None
    for line in body.split('\n'):
        if not line.strip():
            name = None
            continue
        if name is None:
            if PARAMETER_SEPARATOR not in line:
                raise DocumentError("bad parameter line '{}'".format(line))
            name, value = line.split(PARAMETER_SEPARATOR, 1)
            name = name.strip()
            parameters.append([name, value.strip()])
        else:
            parameters[-1][1] += '\n' + line
    return parameters


def _lines(body):
    return [line.strip() for line in body.split('\n') if line.strip()]


def _is_fa(doc):
    if hasattr(doc, 'is_fa'):
        return doc.is_fa()
    return doc.get_meta().get_string(META_TYPE).strip() == META_TYPE_FA


def _open(path):
    doc = CyberiadaML.LocalDocument()
    try:
        doc.open(path, CyberiadaML.formatDetect, CyberiadaML.geometryFormatNone)
        # the libraries take a broken automaton as a draft unless they read strictly
        if _is_fa(doc):
            doc = CyberiadaML.LocalDocument()
            doc.open(path, CyberiadaML.formatDetect, CyberiadaML.geometryFormatNone, strict=True)
    except Exception as e:  # pylint: disable=broad-except
        raise DocumentError("'{}': {}".format(path, e)) from e
    if not _is_fa(doc):
        raise DocumentError("'{}': no FA document: the metadata has no type/ fa".format(path))
    return doc


def _read_comment(element, automaton):
    name = element.get_name().strip()
    body = element.get_body()
    if name in INPUT_NAMES:
        automaton.input_alphabet = (name, _lines(body))
    elif name in OUTPUT_NAMES:
        automaton.output_alphabet = (name, _lines(body))
    elif name.startswith(COMPONENT_PREFIX):
        parameters = parse_parameters(body)
        ctype = [value for key, value in parameters if key == PARAMETER_TYPE]
        if ctype != [CLASSES_TYPE]:
            return                   # a component of another tool
        if automaton.classes:
            raise DocumentError('two Classes components')
        automaton.classes = [(key, value) for key, value in parameters if key != PARAMETER_TYPE]


def _read_children(element, parent, automaton):
    for child in element.get_children():
        etype = child.get_type()
        ident = child.get_id()
        if etype == CyberiadaML.elementFormalComment:
            _read_comment(child, automaton)
        elif etype in _STATES:
            output = None
            for action in child.get_actions():
                if action.get_type() == CyberiadaML.actionEntry:
                    output = action.get_behavior().strip() or None
            composite = etype == CyberiadaML.elementCompositeState
            automaton.states[ident] = State(ident, child.get_name(), parent, composite, output)
            if composite:
                _read_children(child, ident, automaton)
        elif etype == CyberiadaML.elementInitial:
            automaton.initials[ident] = parent
            if parent is None:
                automaton.initial = ident
        elif etype == CyberiadaML.elementFinal:
            automaton.final = ident


def _read_transitions(sm, automaton):
    for trans in sm.get_transitions():
        symbol, output = None, None
        if trans.has_action():
            action = trans.get_action()
            symbol = action.get_trigger().strip() or None
            output = action.get_behavior().strip() or None
        automaton.transitions.append(Transition(trans.get_id(), trans.get_source_element_id(),
                                                trans.get_target_element_id(), symbol, output))


def read(path):
    """The Automaton of a document; DocumentError when it is no FA diagram."""
    doc = _open(path)
    machines = doc.get_state_machines()
    if len(machines) != 1:
        raise DocumentError("'{}': {} state machines, one expected".format(path, len(machines)))
    sm = machines[0]
    automaton = Automaton(sm.get_name())
    try:
        _read_children(sm, None, automaton)
        _read_transitions(sm, automaton)
        automaton.compute()
    except DocumentError as e:
        raise DocumentError("'{}': {}".format(path, e)) from e
    return automaton
