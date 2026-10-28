# -----------------------------------------------------------------------------
#  The Python FA dispatcher
#
#  The editor plugin, run through the batch mode of CyberiadaPro
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

"""The plugin in the editor: the session script of test/session and the tests
action. Skipped without a CyberiadaPro binary that starts (CYBERIADA_PRO, PATH,
or the sibling build)."""

import os
import shutil
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.dirname(TEST_DIR)
PLUGIN = 'fa-dispatcher'
SKIPPED = 77
TIMEOUT_S = 120


def environment(profile):
    """A private profile; the plugin's python3 finds the modules of this repository."""
    python_dir = os.path.dirname(sys.executable)
    path = python_dir + os.pathsep + os.environ.get('PATH', '')
    pythonpath = os.pathsep.join(p for p in (REPOSITORY, os.environ.get('PYTHONPATH')) if p)
    return dict(os.environ, QT_QPA_PLATFORM='offscreen', PATH=path, PYTHONPATH=pythonpath,
                XDG_CONFIG_HOME=os.path.join(profile, 'config'),
                XDG_DATA_HOME=os.path.join(profile, 'data'))


def starts(path, env):
    try:
        result = subprocess.run([path, '--help'], env=env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, check=False, timeout=TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def editor(env):
    candidates = [os.environ.get('CYBERIADA_PRO'), shutil.which('CyberiadaPro'),
                  os.path.join(REPOSITORY, '..', 'CyberiadaHSM-Editor', 'build', 'CyberiadaPro')]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK) and starts(path, env):
            return path
    return None


def batch(binary, env, *args):
    result = subprocess.run([binary, '--batch'] + list(args), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True, env=env,
                            cwd=REPOSITORY, check=False, timeout=TIMEOUT_S)
    return result.returncode, result.stdout


def main():
    with tempfile.TemporaryDirectory() as profile:
        env = environment(profile)
        binary = editor(env)
        if binary is None:
            print('skipped: no CyberiadaPro binary')
            return SKIPPED
        failed = 0
        code, out = batch(binary, env, '--plugin-path', '.', '--list-plugins')
        if 'session: tape' not in out:
            print('skipped: the editor has no plugin sessions\n' + out)
            return SKIPPED
        code, out = batch(binary, env, 'examples/morse-decoder.graphml', '--plugin-path', '.',
                          '--run-plugin', PLUGIN + ':tape', '--session-script',
                          'test/session/decoder.session', '--dump-session')
        ok = code == 0 and 'output=J,A' in out and 'verdict=accepted' in out
        print(('ok   ' if ok else 'FAIL ') + 'the session' + ('' if ok else '\n' + out))
        failed += 0 if ok else 1
        tests = os.path.join(profile, 'email.tests')
        with open(tests, 'w', encoding='utf-8') as target:
            target.write('+ "j.doe@mail.ru"\n+ "a@b.c"\n')
        code, out = batch(binary, env, 'examples/email.graphml', '--plugin-path', '.',
                          '--run-plugin', PLUGIN + ':test', '--plugin-param', 'tests=' + tests,
                          '--dump-plugin')
        ok = code == 0 and 'count: 1' in out and \
            'error - T1: line 2: expected accepted, got rejected at EOF' in out
        print(('ok   ' if ok else 'FAIL ') + 'the tests action' + ('' if ok else '\n' + out))
        failed += 0 if ok else 1
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
