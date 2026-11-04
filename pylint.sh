#!/bin/bash

FILES="fad examples/build.py test/run.py test/session_test.py test/plugin_test.py"
pylint --disable=I1101,C0301,W0703 $FILES
