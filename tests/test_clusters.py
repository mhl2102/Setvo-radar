import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import clusters


def it(i, title, source, text=''):
    return {'id': i, 'title': title, 'text': text, 'source': source}


class NormalizeTests(unittest.TestCase):
    def test_remove_acentos_e_stopwords(self):
        self.assertEqual(normalize_set('Automação da logística para as transportadoras'),
                         {'automacao', 'logistica', 'transportadoras'})

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


if __name__ == '__main__':
    unittest.main()
