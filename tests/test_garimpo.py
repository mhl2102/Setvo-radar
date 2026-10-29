"""Testes do agente de garimpo sem depender de APIs externas."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import os
import tempfile
import unittest

import radar
import dashboard
from garimpo import find_gold


class GoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = os.environ.get('RADAR_DB')
        os.environ['RADAR_DB'] = os.path.join(self.temp.name, 'test.db')
        self.old_demo = os.environ.get('RADAR_DEMO')
        os.environ['RADAR_DEMO'] = '0'
        self.config = radar.load_config()

    def tearDown(self):
        if self.old_db is None:
            os.environ.pop('RADAR_DB', None)
        else:
            os.environ['RADAR_DB'] = self.old_db
        if self.old_demo is None:
            os.environ.pop('RADAR_DEMO', None)
        else:
            os.environ['RADAR_DEMO'] = self.old_demo
        self.temp.cleanup()

    def signal(self, title, source, url, kind='ask', days=1):
        r = radar.item(source, title, url, 'Frustrated manual workarounds and recurring issue',
                       kind=kind, published=datetime.now(timezone.utc) - timedelta(days=days))
        r.update(signal='dor' if kind == 'ask' else 'tendencia', sector='Ferramentas para devs', demo=0)
        return r

    def test_new_unconfigured_topic_multiple_sources(self):
        rows = [
            self.signal('Broken invoice reconciliation workflow for founders', 'Ask HN', 'https://example.org/a'),
            self.signal('Broken invoice reconciliation reporting with spreadsheets', 'GitHub Issues', 'https://example.org/b'),
            self.signal('Broken invoice reconciliation startups announced', 'Tech Blog', 'https://example.org/c', kind='news'),
        ]
        result = find_gold(rows, {}, days=30)
        candidate = next(o for o in result if 'invoice reconciliation' in o['name'].lower())
        self.assertEqual(candidate['direct'], 2)
        self.assertEqual(candidate['direct_source_count'], 2)
        self.assertEqual(candidate['total'], 3)
        self.assertEqual(candidate['origin'], 'emergente')
        self.assertEqual(len(candidate['evidence']), 3)
        self.assertIn('não comprova', candidate['warning'].lower())

    def test_single_source_is_not_emerging_validation(self):
        rows = [self.signal('Unusual testing triage pipeline', 'Ask HN', 'https://example.org/a'),
                self.signal('Unusual testing triage pipeline', 'Ask HN', 'https://example.org/b')]
        self.assertEqual(find_gold(rows, {}, days=30), [])

    def test_no_data_no_opportunities(self):
        self.assertEqual(find_gold([], self.config['themes']), [])
        self.assertEqual(dashboard.fetch_api('/api/gold', {}, self.config)['total'], 0)

    def test_demo_flag_carries_to_result(self):
        row1 = self.signal('Unusual testing triage pipeline', 'Ask HN', 'https://example.org/a')
        row2 = self.signal('Unusual testing triage pipeline', 'GitHub Issues', 'https://example.org/b')
        row1['demo'] = row2['demo'] = 1
        self.assertTrue(find_gold([row1, row2], {}, days=30)[0]['demo'])

    def test_api_gold_and_filter(self):
        rows = [self.signal('Broken invoice reconciliation reports', 'Ask HN', 'https://example.org/a'),
                self.signal('Broken invoice reconciliation workflow', 'GitHub Issues', 'https://example.org/b')]
        with radar.db() as con:
            radar.save(con, rows, self.config)
        results = dashboard.fetch_api('/api/gold', {'min_direct':['2']}, self.config)
        self.assertGreaterEqual(results['total'], 1)
        self.assertIn('não significa', results['coverage_warning'])
        self.assertEqual(dashboard.fetch_api('/api/gold', {'min_direct':['12']}, self.config)['total'], 0)

    def test_stackexchange_collector_exposes_urls_and_dates(self):
        class Resp:
            def raise_for_status(self): pass
            def json(self):return {'items':[
                {'title':'How do I fix a frustrating invoice reconciliation issue?',
                 'link':'https://stackoverflow.com/questions/4321', 'score':3, 'answer_count':2,
                 'tags':['python','invoice'], 'creation_date':int(datetime.now(timezone.utc).timestamp())}],
                 'backoff':0, 'quota_remaining':9999}
        cfg = {'stackexchange': {'enabled':True, 'sites':['stackoverflow'], 'per_site':25, 'min_score':1}}
        with patch.object(radar.HTTP, 'get', return_value=Resp()):
            out=radar.collect_stackexchange(cfg)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['source'],'Stack Exchange: stackoverflow')
        self.assertEqual(out[0]['kind'],'ask')
        self.assertEqual(out[0]['url'],'https://stackoverflow.com/questions/4321')

    def test_stackexchange_respects_backoff(self):
        class Resp:
            def raise_for_status(self): pass
            def json(self):return {'items':[], 'backoff':100, 'quota_remaining':1000}
        cfg = {'stackexchange': {'enabled':True, 'sites':['stackoverflow','superuser']}}
        with patch.object(radar.HTTP, 'get', return_value=Resp()) as mocked:
            radar.collect_stackexchange(cfg)
            self.assertEqual(mocked.call_count,1)

if __name__ == '__main__':unittest.main()
