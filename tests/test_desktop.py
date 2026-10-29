"""Regressões críticas do app desktop, sem abrir janela durante os testes."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path
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


    def test_setvo_brand_and_storage_are_distinct_from_old_setvo(self):
        self.assertEqual(desktop.APP_NAME, 'SetvoIntelligence')
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'LOCALAPPDATA': folder, 'XDG_DATA_HOME': folder}):
                self.assertEqual(desktop.data_dir().name, 'SetvoIntelligence')

    def test_migrates_legacy_radar_db_without_deleting_original(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder) / 'RadarStartupIntelligence'
            original.mkdir()
            with closing(sqlite3.connect(original / 'radar.db')) as db, db:
                db.execute('CREATE TABLE evidence (test INTEGER)')
                db.execute('INSERT INTO evidence VALUES (42)')
            (original / 'config.yaml').write_text('feeds: []', encoding='utf-8')
            current = Path(folder) / 'SetvoIntelligence'
            current.mkdir()
            desktop.migrate_legacy_data(current)
            with closing(sqlite3.connect(current / 'radar.db')) as db, db:
                self.assertEqual(db.execute('SELECT test FROM evidence').fetchone()[0], 42)
            self.assertEqual((current / 'config.yaml').read_text(encoding='utf-8'), 'feeds: []')
            self.assertTrue((original / 'radar.db').exists())
            # A migração nunca sobrescreve dados já modificados no Setvo.
            with closing(sqlite3.connect(current / 'radar.db')) as db, db:
                db.execute('UPDATE evidence SET test=43')
            desktop.migrate_legacy_data(current)
            with closing(sqlite3.connect(current / 'radar.db')) as db, db:
                self.assertEqual(db.execute('SELECT test FROM evidence').fetchone()[0], 43)

    def test_site_brand_matches_setvo(self):
        html = (Path(desktop.__file__).parent / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<title>Setvo | Inteligência de Mercado</title>', html)
        self.assertIn('SETVO / V2.3', html)

if __name__ == '__main__':
    unittest.main()
