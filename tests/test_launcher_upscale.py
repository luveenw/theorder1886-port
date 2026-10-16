"""Experimental resolution/upscaling controls are visible and opt-in."""
import sys
import unittest

from paths import ROOT
sys.path.insert(0, str(ROOT / 'launcher'))
import port_launcher_win as launcher


class UpscalerSettingsTest(unittest.TestCase):
    def test_remaining_choices_have_no_spatial_upscaler(self):
        self.assertEqual([value for value, _text in launcher.UPSCALERS], ['fsr3', 'taa', 'off'])

    def test_removed_controls_do_not_supply_defaults_to_save(self):
        for key in ('fsr1', 'sharpen', 'sharpness', 'rcas', 'rcas_strength'):
            self.assertNotIn(key, launcher.INI_DEFAULTS)

    def test_graphics_page_exposes_resolution_and_upscaling(self):
        try:
            import tkinter as tk
            from tkinter import ttk
            root = tk.Tk()
        except ImportError as error:
            self.skipTest(f'Tk unavailable: {error}')
        except tk.TclError as error:
            self.skipTest(f'Tk display unavailable: {error}')
        root.withdraw()
        self.addCleanup(root.destroy)
        app = launcher.Launcher.__new__(launcher.Launcher)
        app.tk, app.ttk, app.root, app.dpi = tk, ttk, root, 1.0
        app.content, app.pages, app.vars = ttk.Frame(root), {}, {}
        app.app, app.ini = dict(launcher.APP_DEFAULTS), dict(launcher.INI_DEFAULTS)
        app.build_graphics()
        for key in ('experimental_upscaler', 'upscaler', 'preset', 'output_res', 'live_resolution'):
            self.assertIn(key, app.vars)
        self.assertFalse(app.vars['experimental_upscaler'].get())
        app.vars['experimental_upscaler'].set(True)
        self.assertEqual(launcher.game_environment({**app.app, 'experimental_upscaler': True})[
            'THEORDER_EXPERIMENTAL_UPSCALER'], '1')


if __name__ == '__main__':
    unittest.main()
