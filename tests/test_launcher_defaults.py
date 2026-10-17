"""Reset through the real launcher, with all persistent files isolated."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from paths import ROOT
sys.path.insert(0, str(ROOT / 'launcher'))
import port_launcher_win as launcher


class LauncherDefaultsTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox, ttk
        except ImportError as error:
            self.skipTest(str(error))
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f'Tk display unavailable: {error}')
        self.root.withdraw()
        self.addCleanup(self.close_window)
        self.tmp_context = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_context.cleanup)
        self.tmp = Path(self.tmp_context.name)
        self.ini = self.tmp / 'theorder.ini'
        self.config = self.tmp / 'config' / 'settings.json'
        self.config.parent.mkdir()
        self.data = self.tmp / 'data'
        self.data.mkdir()
        self.save = self.data / 'user' / 'savedata' / 'SYSTEM.DAT'
        self.save.parent.mkdir(parents=True)
        self.save.write_bytes(b'keep my save')
        self.cache = self.data / 'user' / 'cache' / 'shader.bin'
        self.cache.parent.mkdir()
        self.cache.write_bytes(b'keep my shader cache')
        self.settings = dict(launcher.APP_DEFAULTS, game_dir=str(self.tmp / 'game'),
                             update_dir=str(self.tmp / 'update'), user_dir=str(self.data / 'user'),
                             mods_dir=str(self.tmp / 'mods'), patches_dir=str(self.tmp / 'patches'),
                             experimental_upscaler=True, video_backend='x11', draw_pipe='0',
                             controls={'key': {'cross': 'Q'}, 'pad': {'cross': 'b'}},
                             pad_style='xbox', game_patches={'CUSA00785': ['chosen']})
        self.config.write_text(json.dumps(self.settings))
        self.ini.write_text('upscaler=fsr3\npreset=3\noutput_res=3840x2160\nengine_fps=120\nsharpen=1\n')
        for patch in (mock.patch.object(launcher, 'CONFIG_FILE', self.config),
                      mock.patch.object(launcher, 'CONFIG_DIR', self.config.parent),
                      mock.patch.object(launcher, 'DATA_DIR', self.data),
                      mock.patch.object(launcher, 'LANG', 'en'),
                      mock.patch.object(launcher, 'list_gpus', return_value=[]),
                      mock.patch.dict(os.environ, {'THEORDER_CONFIG': str(self.ini)})):
            patch.start()
            self.addCleanup(patch.stop)
        self.app = launcher.Launcher(self.root, tk, ttk, filedialog, messagebox)

    def close_window(self):
        for pending in self.root.tk.call('after', 'info'):
            self.root.after_cancel(pending)
        self.root.destroy()

    def test_reset_stages_then_persists_defaults_without_touching_content(self):
        before = self.ini.read_bytes(), self.config.read_bytes()
        # Keep unsaved path edits too.
        self.app.var('update_dir', 'app').set(str(self.tmp / 'new-update'))
        self.app.reset_button.invoke()
        self.assertEqual((self.ini.read_bytes(), self.config.read_bytes()), before)
        self.assertEqual(str(self.app.save_button['state']), 'normal')
        self.assertFalse(self.app.var('experimental_upscaler', 'app').get())
        self.assertEqual(self.app.var('output_res', 'ini').get(), '1920x1080')
        self.assertEqual(self.app.gather()['app']['controls'], {'key': {}, 'pad': {}})
        self.app.save_button.invoke()
        values, _lines = launcher.load_ini()
        self.assertEqual(values, launcher.INI_DEFAULTS)
        saved = json.loads(self.config.read_text())
        self.assertEqual(saved['update_dir'], str(self.tmp / 'new-update'))
        for key in ('game_dir', 'user_dir', 'mods_dir', 'patches_dir', 'ui_language',
                    'mods_enabled', 'game_patches'):
            self.assertEqual(saved[key], self.settings[key], key)
        self.assertEqual(saved['video_backend'], 'auto')
        self.assertEqual(saved['draw_pipe'], '')
        self.assertEqual(saved['pad_style'], 'playstation')
        self.assertEqual(self.save.read_bytes(), b'keep my save')
        self.assertEqual(self.cache.read_bytes(), b'keep my shader cache')
        self.assertEqual(str(self.app.save_button['state']), 'disabled')
        self.close_window()
        self.root = self.app.tk.Tk()
        self.root.withdraw()
        reopened = launcher.Launcher(self.root, self.app.tk, self.app.ttk,
                                     self.app.filedialog, self.app.messagebox)
        self.assertFalse(reopened.var('experimental_upscaler', 'app').get())
        self.assertEqual(reopened.var('engine_fps', 'ini').get(), launcher.INI_DEFAULTS['engine_fps'])
        self.assertEqual(reopened.gather()['app']['controls'], {'key': {}, 'pad': {}})
        self.assertEqual(str(reopened.save_button['state']), 'disabled')

    def test_reset_failure_keeps_reset_pending_for_retry(self):
        self.app.reset_defaults()
        with mock.patch.object(launcher, 'atomic_write', side_effect=PermissionError('locked')), \
                mock.patch.object(self.app.messagebox, 'showerror'):
            self.assertFalse(self.app.collect())
        self.assertTrue(self.app.reset_pending)
        self.assertEqual(str(self.app.save_button['state']), 'normal')
        self.assertTrue(self.app.collect())
        self.assertEqual(launcher.load_ini()[0], launcher.INI_DEFAULTS)

    def test_running_game_cannot_reset_settings(self):
        self.app.process = mock.Mock()
        self.app.process.poll.return_value = None
        before = self.app.gather()
        with mock.patch.object(self.app.messagebox, 'showinfo') as notice:
            self.app.reset_defaults()
        notice.assert_called_once()
        self.assertEqual(self.app.gather(), before)
        self.assertFalse(self.app.reset_pending)

    def test_ordinary_save_still_preserves_external_runtime_changes(self):
        self.ini.write_text(self.ini.read_text() + 'fps_limit=30\nexternal_runtime_key=keep\n')
        self.app.var('vsync', 'ini').set(False)
        self.app.save()
        values, _lines = launcher.load_ini()
        self.assertEqual(values['fps_limit'], '30')
        self.assertEqual(values['external_runtime_key'], 'keep')
        self.assertEqual(values['sharpen'], '1')


if __name__ == '__main__':
    unittest.main()
