#!/bin/bash

FILES="fad.py fad_model.py fad_reader.py fad_tape.py fad_cli.py examples/build.py test/run.py"
pylint --disable=I1101,C0301,W0703 $FILES
