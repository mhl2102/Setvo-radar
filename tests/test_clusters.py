import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault('SETVO_EMBED_DISABLE', '1')  # testes não carregam modelo local
import clusters


def it(i, title, source, text=''):
    return {'id': i, 'title': title, 'text': text, 'source': source}


class NormalizeTests(unittest.TestCase):
    def test_remove_acentos_e_stopwords(self):
        self.assertEqual(normalize_set('Automação da logística para as transportadoras'),
                         {'automa', 'logist', 'transp'})

    def test_texto_vazio(self):
        self.assertEqual(clusters.normalize_tokens(None), set())
        self.assertEqual(clusters.normalize_tokens(''), set())


def normalize_set(text):
    return clusters.normalize_tokens(text)


class ClusterTests(unittest.TestCase):
    def test_relatos_parecidos_de_fontes_diferentes_formam_um_grupo(self):
        items = [
            it(1, 'Transportadoras precisam transferir pedidos manualmente entre sistemas', 'Reddit', 'logistica'),
            it(2, 'Empresa relata transferir pedidos manualmente entre sistemas incompativeis', 'Hacker News'),
            it(3, 'Receita de bolo de cenoura simples', 'Blog de culinaria'),
        ]
        groups = clusters.cluster_items(items)
        self.assertEqual(len(groups), 1)
        self.assertEqual(sorted(groups[0]['member_ids']), [1, 2])
        self.assertEqual(groups[0]['sources'], 2)

    def test_republicacao_da_mesma_fonte_nao_conta_como_fontes_independentes(self):
        items = [
            it(1, 'Falta de integração entre ERP e transportadora', 'Feed A'),
            it(2, 'Falta de integração entre ERP e transportadora', 'Feed A'),
            it(3, 'Falta de integração entre ERP e transportadora', 'Feed A'),
        ]
        groups = clusters.cluster_items(items)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['size'], 3)
        self.assertEqual(groups[0]['sources'], 1)

    def test_itens_sem_relacao_nao_formam_grupo(self):
        items = [
            it(1, 'Banco central anuncia nova regra de pix', 'Neofeed'),
            it(2, 'Robô industrial aprende a soldar peças', 'Robot Report'),
        ]
        self.assertEqual(clusters.cluster_items(items), [])

    def test_grupos_ordenados_por_fontes_distintas(self):
        items = [
            it(1, 'pedido ajuste rota frota entrega', 'A'),
            it(2, 'pedido ajuste rota frota entrega', 'A'),
            it(3, 'controle estoque armazem pequeno negocio', 'X'),
            it(4, 'controle estoque armazem pequeno negocio', 'Y'),
        ]
        groups = clusters.cluster_items(items)
        self.assertEqual(groups[0]['sources'], 2)
        self.assertEqual(groups[1]['sources'], 1)

    def test_limitacao_documentada_idiomas_diferentes_nao_se_aproximam(self):
        items = [
            it(1, 'pedido de integração entre sistemas', 'Fórum BR'),
            it(2, 'integration request between legacy systems', 'Forum EN'),
        ]
        self.assertEqual(clusters.cluster_items(items), [])



class ClusterApiTests(unittest.TestCase):
    def setUp(self):
        import json as _json, os as _os, tempfile as _tf, threading as _th
        from http.client import HTTPConnection as _HC
        import dashboard
        self._json, self._HC = _json, _HC
        self.temp = _tf.TemporaryDirectory()
        self.saved = {k: _os.environ.get(k) for k in ('RADAR_DB', 'RADAR_DEMO', 'SETVO_EMBED_DISABLE')}
        _os.environ['RADAR_DB'] = _os.path.join(self.temp.name, 'cl.db')
        _os.environ['RADAR_DEMO'] = '0'
        # Testes da API não devem depender do modelo instalado no ambiente.
        _os.environ['SETVO_EMBED_DISABLE'] = '1'
        import semantic
        semantic.reset()
        self.server = dashboard.create_server(port=0)
        self.port = self.server.server_port
        self.thread = _th.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        import os as _os
        import semantic
        semantic.reset()
        self.server.shutdown()
        self.server.server_close()
        for k, v in self.saved.items():
            if v is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = v
        self.temp.cleanup()

    def get(self, path):
        conn = self._HC('127.0.0.1', self.port, timeout=10)
        conn.request('GET', path)
        resp = conn.getresponse()
        data = self._json.loads(resp.read().decode('utf-8'))
        conn.close()
        return resp.status, data

    def test_endpoint_responde_mesmo_sem_dados(self):
        status, data = self.get('/api/clusters?days=30')
        self.assertEqual(status, 200)
        self.assertEqual(data['groups'], [])
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['method'], 'lexical por termos em comum (fallback: semântico indisponível)')
        self.assertIn('Fontes independentes', data['note'])

    def test_endpoint_agrupa_itens_gravados(self):
        import radar
        con = radar.db()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        for i, (title, src) in enumerate([
            ('Transportadoras transferem pedidos manualmente entre sistemas', 'Reddit'),
            ('Pedidos transferidos manualmente entre sistemas incompatíveis', 'Hacker News'),
            ('Receita de bolo simples', 'Blog')]):
            con.execute("""INSERT INTO items (id, source, title, url, text, geo, weight, engagement,
                           kind, published, collected, sector, score, signal, pain_level, demo)
                           VALUES (?, ?, ?, ?, '', 'global', 1, 0, 'news', ?, ?, 'Logística', 1, 'dor', 1, 0)""",
                        (f'x{i}', src, title, f'https://exemplo.test/{i}', now, now))
        con.commit()
        con.close()
        status, data = self.get('/api/clusters?days=30')
        self.assertEqual(status, 200)
        self.assertEqual(len(data['groups']), 1)
        group = data['groups'][0]
        self.assertEqual(group['sources'], 2)
        self.assertEqual(len(group['evidence']), 2)
        self.assertTrue(all(e['url'].startswith('https://') for e in group['evidence']))


    def test_modo_semantico_sem_modelo_informa_erro_claro(self):
        status, data = self.get('/api/clusters?days=30&mode=semantic')
        self.assertEqual(status, 200)
        self.assertEqual(data['groups'], [])
        self.assertIn('indisponível', data['error'])


if __name__ == '__main__':
    unittest.main()
