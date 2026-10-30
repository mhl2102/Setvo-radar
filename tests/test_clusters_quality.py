"""Testes de qualidade do agrupamento lexical, com conjunto rotulado sintético.

Métricas no nível de PAR: um par é previsto como 'mesmo problema' se a similaridade
de Jaccard entre os termos normalizados atinge o limiar. Os limiares mínimos abaixo
foram escolhidos para evitar regressões; não são metas de produto.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import clusters

FIXTURE = Path(__file__).parent / 'fixtures' / 'clusters_eval.json'
THRESHOLD = clusters.DEFAULT_THRESHOLD
MIN_PRECISION = 0.80
MIN_RECALL = 0.60


def evaluate(pairs, threshold=THRESHOLD):
    tp = fp = fn = tn = 0
    misses, false_alarms = [], []
    for p in pairs:
        score = clusters.jaccard(clusters.normalize_tokens(p['a']), clusters.normalize_tokens(p['b']))
        predicted = score >= threshold
        if predicted and p['same']:
            tp += 1
        elif predicted and not p['same']:
            fp += 1
            false_alarms.append(p)
        elif not predicted and p['same']:
            fn += 1
            misses.append(p)
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'precision': precision,
            'recall': recall, 'misses': misses, 'false_alarms': false_alarms}


class ClusterQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = json.loads(FIXTURE.read_text(encoding='utf-8'))['pairs']
        cls.result = evaluate(cls.pairs)

    def test_conjunto_tem_exemplos_suficientes_nos_dois_rotulos(self):
        positives = sum(1 for p in self.pairs if p['same'])
        negatives = len(self.pairs) - positives
        self.assertGreaterEqual(positives, 10)
        self.assertGreaterEqual(negatives, 8)

    def test_precisao_minima(self):
        r = self.result
        self.assertGreaterEqual(r['precision'], MIN_PRECISION,
                                f"falsos positivos: {[p['a'] for p in r['false_alarms']]}")

    def test_revocacao_minima(self):
        r = self.result
        self.assertGreaterEqual(r['recall'], MIN_RECALL,
                                f"perdas: {[p['a'] for p in r['misses']]}")

    def test_metricas_registradas_para_relatorio(self):
        r = self.result
        print(f"\n[qualidade] tp={r['tp']} fp={r['fp']} fn={r['fn']} tn={r['tn']} "
              f"precisão={r['precision']:.2f} revocação={r['recall']:.2f} limiar={THRESHOLD}")

    def test_pares_identicos_sempre_se_agrupam(self):
        for text in ['Falta de integração entre ERP e transportadora',
                     'Controle manual de estoque em planilha']:
            self.assertGreaterEqual(
                clusters.jaccard(clusters.normalize_tokens(text), clusters.normalize_tokens(text)), THRESHOLD)

    def test_mesmo_texto_em_fontes_diferentes_nao_e_duplicado_de_fontes(self):
        items = [
            {'id': 1, 'title': 'Redigitar pedidos entre sistemas de transportadora', 'text': '', 'source': 'A'},
            {'id': 2, 'title': 'Redigitar pedidos entre sistemas de transportadora', 'text': '', 'source': 'A'},
            {'id': 3, 'title': 'Redigitar pedidos entre sistemas de transportadora', 'text': '', 'source': 'B'},
        ]
        groups = clusters.cluster_items(items)
        self.assertEqual(groups[0]['size'], 3)
        self.assertEqual(groups[0]['sources'], 2)

    def test_caso_simples_tem_mesmo_resultado_em_qualquer_ordem(self):
        # Agrupamento guloso depende da ordem em geral; este caso específico é estável.
        base = [
            {'id': 1, 'title': 'pedidos manuais transportadora sistema', 'text': '', 'source': 'A'},
            {'id': 2, 'title': 'pedidos manuais transportadora sistema lento', 'text': '', 'source': 'B'},
            {'id': 3, 'title': 'receita bolo cenoura chocolate', 'text': '', 'source': 'C'},
            {'id': 4, 'title': 'receita bolo cenoura cobertura', 'text': '', 'source': 'D'},
        ]
        n1 = len(clusters.cluster_items(base))
        n2 = len(clusters.cluster_items(list(reversed(base))))
        self.assertEqual(n1, n2)


if __name__ == '__main__':
    unittest.main()
