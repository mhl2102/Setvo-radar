"""Regressões críticas do app desktop, sem abrir janela durante os testes."""
import os
import tempfile
import unittest
from unittest.mock import patch

import desktop


class DesktopTests(unittest.TestCase):
    def test_demo_always_uses_isolated_db(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'RADAR_DB': os.path.join(folder, 'production.db'),
                                      'LOCALAPPDATA': folder, 'XDG_DATA_HOME': folder}):
                desktop.configure_environment(demo=True)
                self.assertTrue(os.environ['RADAR_DB'].endswith('radar_demo.db'))
                self.assertEqual(os.environ['RADAR_DEMO'], '1')

    def test_live_preserves_explicit_db(self):
        with tempfile.TemporaryDirectory() as folder:
            explicit = os.path.join(folder, 'custom.db')
            with patch.dict(os.environ, {'RADAR_DB': explicit, 'LOCALAPPDATA': folder,
                                      'XDG_DATA_HOME': folder}):
                desktop.configure_environment(demo=False)
                self.assertEqual(os.environ['RADAR_DB'], explicit)
                self.assertEqual(os.environ['RADAR_DEMO'], '0')


if __name__ == '__main__':
    unittest.main()
