#!/bin/bash

FILES="fad.py fad_model.py fad_reader.py fad_tape.py fad_cli.py fad_session.py fad_plugin.py examples/build.py test/run.py test/session_test.py test/plugin_test.py"
pylint --disable=I1101,C0301,W0703 $FILES
