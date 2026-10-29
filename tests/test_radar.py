import contextlib
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parents[1]))
import radar
import dashboard
import rss_compat
from insights import build_opportunities, detect_signal, mentioned_companies, summarize_sector_trends


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = os.environ.get('RADAR_DB')
        self.old_demo = os.environ.get('RADAR_DEMO')
        os.environ['RADAR_DB'] = os.path.join(self.temp.name, 'testing.db')
        os.environ['RADAR_DEMO'] = '0'
        self.cfg = radar.load_config()

    def tearDown(self):
        for key, value in [('RADAR_DB', self.old_db), ('RADAR_DEMO', self.old_demo)]:
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        self.temp.cleanup()

    def make_item(self, title='Need to automate inventory planning', kind='ask', source='Ask HN',
                  url='https://news.ycombinator.com/item?id=123', age=2, geo='global', desc='We struggle with demand forecasting and stockout.'):
        return radar.item(source, title, url, desc, geo, 2, 14, kind,
                          datetime.now(timezone.utc)-timedelta(days=age))

    def test_ask_hn_collector_keeps_different_posts(self):
        class Result:
            def raise_for_status(self): pass
            def json(self): return {'hits': [
                {'objectID':'121','title':'Ask HN: How do I automate supply chain demand forecasting?',
                 'story_text':'I need better forecasting.','created_at_i':int(datetime.now(timezone.utc).timestamp()),'points':3,'num_comments':2},
                {'objectID':'122','title':'Ask HN: Any good tool for inventory planning?',
                 'story_text':'Our stockout problem is recurrent.','created_at_i':int(datetime.now(timezone.utc).timestamp()),'points':5,'num_comments':5}]}
        with patch.object(radar.HTTP,'get',return_value=Result()):
            rows=radar.collect_ask_hn(self.cfg)
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])
        self.assertEqual(rows[0]['kind'],'ask')

    def test_github_issues_collector_limits_and_parses_dates(self):
        class Result:
            def raise_for_status(self): pass
            def json(self): return {'items':[{'title':'Feature request: add API monitor','html_url':'https://github.com/example/repo/issues/23',
             'body':'Please add an integration monitor.','comments':7,'created_at':'2026-10-27T12:00:00Z'}]}
        with patch.object(radar.HTTP,'get',return_value=Result()):
            issues=radar.collect_github_issues(self.cfg)
        self.assertEqual(len(issues),2)  # duas consultas retornaram o mesmo issue
        with radar.db() as con:
            self.assertEqual(radar.save(con,issues,self.cfg),1)

    def test_hn_urls_preserve_query_identifiers(self):
        x = radar.item('Ask HN', 'A', 'https://news.ycombinator.com/item?id=123')
        y = radar.item('Ask HN', 'B', 'https://news.ycombinator.com/item?id=124')
        self.assertNotEqual(x['id'], y['id'])
        z = radar.item('Ask HN', 'A', 'https://news.ycombinator.com/item?utm_source=feed&id=123')
        self.assertEqual(x['id'], z['id'])

    def test_rss_fallback_parses_rss_and_atom(self):
        rss = b'<rss><channel><item><title>Logistics</title><link>https://example.org/1</link><description>Pain point</description><pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        r = rss_compat.parse(rss)
        self.assertEqual(r.entries[0]['summary'], 'Pain point')
        self.assertEqual(r.entries[0]['link'], 'https://example.org/1')
        self.assertEqual(radar.feed_date(r.entries[0]).day, 27)
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Agent</title><link href="https://example.org/2"/><summary>agentic</summary><published>2026-10-26T08:30:00Z</published></entry></feed>'
        self.assertEqual(rss_compat.parse(atom).entries[0]['link'], 'https://example.org/2')
        self.assertEqual(rss_compat.parse(atom).entries[0]['summary'], 'agentic')

    def test_signal_strength_by_source(self):
        self.assertEqual(detect_signal({'kind':'issue','title':'Feature request: API monitoring','text':'Please add support'})[0], 'pedido')
        self.assertEqual(detect_signal({'kind':'news','title':'Manual API workflows cause problems','text':''})[0], 'indicacao')
        self.assertEqual(detect_signal({'kind':'research','title':'Neural algorithm','text':''})[0], 'pesquisa')

    def test_migration_from_original_schema(self):
        dbpath=os.environ['RADAR_DB']
        con=sqlite3.connect(dbpath)
        con.execute('CREATE TABLE items (id TEXT PRIMARY KEY, source TEXT,title TEXT,url TEXT,text TEXT,geo TEXT,weight REAL,engagement REAL,kind TEXT,published TEXT,collected TEXT,sector TEXT,score REAL,summary TEXT,sent INTEGER DEFAULT 0)')
        con.execute("INSERT INTO items (id,title,text,kind,source,score,published) VALUES (?,?,?,?,?,?,?)",('old','Feature request: inventory forecasting','Please add inventory planning','issue','GitHub Issues',7,datetime.now(timezone.utc).isoformat()))
        con.commit();con.close()
        with radar.db() as con:
            record=con.execute("SELECT signal,pain_level FROM items WHERE id='old'").fetchone()
            self.assertEqual(record['signal'],'pedido')
            self.assertGreaterEqual(record['pain_level'],1)

    def test_save_duplicates_and_distinct_hn_ids(self):
        with radar.db() as con:
            i = self.make_item()
            j = self.make_item(title='Wish for an agent API', url='https://news.ycombinator.com/item?id=456')
            self.assertEqual(radar.save(con,[i,j],self.cfg),2)
            self.assertEqual(radar.save(con,[i],self.cfg),0)
            self.assertEqual(con.execute('SELECT COUNT(*) AS c FROM items').fetchone()['c'],2)

    def test_opportunities_generated_only_with_evidence(self):
        with radar.db() as con:
            radar.save(con,[self.make_item(), self.make_item(title='Need inventory planning',kind='issue',source='GitHub Issues',url='https://github.com/example/repo/issues/2')],self.cfg)
            rows=[dict(r) for r in con.execute('SELECT * FROM items')]
        ops=build_opportunities(rows,self.cfg['themes'])
        inventory=next(o for o in ops if o['id']=='previsao-suprimentos')
        self.assertEqual(inventory['direct'],2)
        self.assertEqual(inventory['source_count'],2)
        self.assertIn(inventory['evidence_level'],['Indício inicial','Sinais recorrentes'])
        self.assertTrue(all(o['total']>0 for o in ops))
        self.assertEqual(build_opportunities([],self.cfg['themes']),[])

    def test_trends_compare_published_weekly_counts(self):
        current=datetime.now(timezone.utc)
        rows=[dict(sector='IA e agentes',published=(current-timedelta(days=d)).isoformat(),demo=0) for d in [1,2,8,10]]
        trend=next(x for x in summarize_sector_trends(rows,self.cfg,current) if x['sector']=='IA e agentes')
        self.assertEqual((trend['recent'],trend['previous'],trend['growth_pct']),(2,2,0.0))

    def test_tech_mentions(self):
        self.assertIn('Microsoft',mentioned_companies('Azure Microsoft announces copilot'))
        self.assertIn('Meta',mentioned_companies('Meta Llama model'))

    def test_dashboard_filters_notes_export(self):
        a=self.make_item()
        b=self.make_item(title='Logtech entrega atrasada',kind='news',source='Portal Teste',url='https://example.org/abc',geo='brasil',desc='Problema de logística com atraso de entrega.')
        with radar.db() as con:
            radar.save(con,[a,b],self.cfg)
        data=dashboard.fetch_api('/api/overview',{'days':['30']},self.cfg)
        self.assertEqual(data['total'],2)
        self.assertEqual(data['countries_brazil'],1)
        self.assertGreaterEqual(data['opportunities'],1)
        data=dashboard.fetch_api('/api/items',{'q':['Logtech']},self.cfg)
        self.assertEqual(data['total'],1)
        data=dashboard.fetch_api('/api/items',{'geo':['brasil']},self.cfg)
        self.assertEqual(data['items'][0]['source'],'Portal Teste')
        self.assertEqual(dashboard.save_note({'id':'previsao-suprimentos','status':'validando','notes':'Entrevista 1'},self.cfg)['ok'],True)
        ops=dashboard.fetch_api('/api/opportunities',{},self.cfg)['opportunities']
        self.assertEqual(next(o for o in ops if o['id']=='previsao-suprimentos')['notes'],'Entrevista 1')
        self.assertEqual(len(dashboard.export_rows({'geo':['brasil']},self.cfg)),1)
        with self.assertRaises(ValueError):dashboard.save_note({'id':'previsao-suprimentos','status':'saiu','notes':'test'},self.cfg)

    def test_http_api_and_csv_safety(self):
        bad=self.make_item(title='=2+3 price',url='https://example.org/attack',kind='news',desc='Pricing workflow')
        with radar.db() as con:
            radar.save(con,[bad],self.cfg)
        server=dashboard.create_server(port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            con=HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            con.request('GET','/api/overview?days=30')
            response=con.getresponse(); overview=json.loads(response.read())
            self.assertEqual(response.status,200);self.assertEqual(overview['total'],1)
            con.request('GET','/api/export.csv?days=30')
            csvresp=con.getresponse(); data=csvresp.read().decode('utf-8-sig')
            self.assertIn("'=2+3 price",data)
            con.request('GET','/api/missing')
            err=con.getresponse();err.read();self.assertEqual(err.status,404)
            con.request('POST','/api/notes',body=json.dumps({'id':'previsao-suprimentos','status':'observando','notes':'Test'}),headers={'Content-Type':'application/json'})
            saved=con.getresponse();saved.read();self.assertEqual(saved.status,200)
            con.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

    def test_digest_max_cotas_and_no_demo(self):
        today=datetime.now(timezone.utc)
        records=[]
        for i in range(14):
            row=self.make_item(title=f'AI agent business launches today {i}',source=f'Source{i%3}',url=f'https://example.org/{i}')
            row['published']=today.isoformat()
            records.append(row)
        with radar.db() as con:
            radar.save(con,records,self.cfg)
        digest=radar.build_digest(self.cfg)
        self.assertIsNotNone(digest)
        self.assertLessEqual(len(digest[1]),self.cfg['digest']['max_items'])
        with radar.db() as con:
            self.assertEqual(con.execute('SELECT SUM(sent) AS sent FROM items').fetchone()['sent'],0)


if __name__ == '__main__':unittest.main()
