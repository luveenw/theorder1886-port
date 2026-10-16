"""Exercise the distributed shell entry point in a relocated path with spaces."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux shell entry point')
class LinuxLaunch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='theorder launch ')
        self.addCleanup(self.tmp.cleanup)
        self.port = Path(self.tmp.name) / 'port with spaces'
        (self.port / 'bin').mkdir(parents=True)
        shutil.copy(ROOT / 'play-linux.sh', self.port)
        # Report the actual environment received by the native child and Python runner.
        report = (f'#!{sys.executable}\nimport json,os,sys\n'
                  'print(json.dumps({"args":sys.argv[1:],"game":os.getenv("THEORDER_GAME_DIR"),'
                  '"data":os.getenv("THEORDER_DATA_DIR"),"layers":os.getenv("VK_LOADER_LAYERS_DISABLE")}))\n')
        probe = self.port / 'bin' / 'theorder-probe'
        probe.write_text(report)
        probe.chmod(0o755)
        (self.port / 'run.py').write_text(report)
        (self.port / 'launcher').mkdir()
        (self.port / 'launcher' / 'port_launcher_win.py').write_text(report)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('THEORDER_')}
        self.env.update(PYTHON=sys.executable, XDG_DATA_HOME=str(Path(self.tmp.name) / 'data with spaces'))

    def run_script(self, *args):
        return subprocess.run(['bash', str(self.port / 'play-linux.sh'), *args],
                              cwd='/', env=self.env, text=True, capture_output=True)

    def test_packaged_probe_diagnostic(self):
        result = self.run_script('--clean-vulkan', '--cpu-features')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['args'], ['--cpu-features'])
        self.assertEqual(report['layers'], '~implicit~')

    def test_game_folder_and_forwarded_options_survive_spaces(self):
        result = self.run_script('--game-dir', '/game folder/01.02', '--level', 'level name')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['game'], '/game folder/01.02')
        self.assertEqual(report['args'], ['--level', 'level name'])
        self.assertEqual(report['data'], str(Path(self.env['XDG_DATA_HOME']) / 'theorder1886'))

    def test_missing_game_folder_argument_is_an_error(self):
        result = self.run_script('--game-dir')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--game-dir needs a folder', result.stderr)

    def test_settings_window_uses_same_game_and_data_environment(self):
        result = self.run_script('--settings', '--game-dir', '/game folder', '--play')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['game'], '/game folder')
        self.assertEqual(report['args'], ['--play'])

    def test_missing_binary_is_actionable(self):
        (self.port / 'bin' / 'theorder-probe').unlink()
        result = self.run_script('--cpu-features')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Build first', result.stderr)
