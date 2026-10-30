import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import numpy as np
import semantic

FIX = Path(__file__).parent / 'fixtures'


class FakeEmbedder:
    """Vetores determinísticos: textos que compartilham a 'ideia' ficam próximos."""
    def __init__(self, table):
        self.table = table

    def embed(self, texts):
        out = []
        for t in texts:
            v = np.zeros(4, dtype='float32')
            for key, vec in self.table.items():
                if key in t:
                    v += np.array(vec, dtype='float32')
            if not v.any():
                v[3] = 1.0
            out.append(v / np.linalg.norm(v))
        return np.vstack(out)


class SemanticLogicTests(unittest.TestCase):
    def setUp(self):
        semantic.reset()
        self.embedder = FakeEmbedder({
            'redigit': [1, 0, 0, 0], 're-enter': [0.95, 0.05, 0, 0], 'manual': [0.9, 0.1, 0, 0],
            'estoque': [0, 1, 0, 0], 'inventory': [0, 0.97, 0.03, 0],
        })

    def test_agrupa_mesma_ideia_em_idiomas_diferentes(self):
        items = [
            {'id': 1, 'title': 'Transportadoras redigitam pedidos manualmente', 'text': '', 'source': 'A'},
            {'id': 2, 'title': 'Carriers re-enter orders manually', 'text': '', 'source': 'B'},
            {'id': 3, 'title': 'Controle de estoque em planilha', 'text': '', 'source': 'C'},
        ]
        groups = semantic.cluster_semantic(items, self.embedder, threshold=0.8)
        self.assertEqual(len(groups), 1)
        self.assertEqual(sorted(groups[0]['member_ids']), [1, 2])
        self.assertEqual(groups[0]['sources'], 2)

    def test_lista_vazia_ou_sem_texto(self):
        self.assertEqual(semantic.cluster_semantic([], self.embedder), [])
        self.assertEqual(semantic.cluster_semantic([{'id': 1, 'title': '', 'text': ''}], self.embedder), [])

    def test_limiar_alto_separa_tudo(self):
        items = [
            {'id': 1, 'title': 'redigit pedidos', 'text': '', 'source': 'A'},
            {'id': 2, 'title': 'manual entry', 'text': '', 'source': 'B'},
        ]
        self.assertEqual(semantic.cluster_semantic(items, self.embedder, threshold=0.999), [])


class FallbackTests(unittest.TestCase):
    def setUp(self):
        semantic.reset()

    def tearDown(self):
        semantic.reset()

    def test_desativado_por_variavel_de_ambiente(self):
        with patch.dict(os.environ, {'SETVO_EMBED_DISABLE': '1'}):
            self.assertIsNone(semantic.load_embedder())
        self.assertFalse(semantic.status()['available'])
        self.assertIn('desativado', semantic.status()['reason'])

    def test_dependencia_ausente_nao_quebra(self):
        with patch.dict(os.environ, {'SETVO_EMBED_DISABLE': '0'}), \
                patch.dict(sys.modules, {'sentence_transformers': None}):
            self.assertIsNone(semantic.load_embedder(force_reload=True))
        self.assertIn('não instalado', semantic.status()['reason'])

    def test_modelo_indisponivel_nao_quebra(self):
        fake = types.ModuleType('sentence_transformers')

        class Broken:
            def __init__(self, *a, **k):
                raise OSError('sem rede')
        fake.SentenceTransformer = Broken
        with patch.dict(os.environ, {'SETVO_EMBED_DISABLE': '0'}), \
                patch.dict(sys.modules, {'sentence_transformers': fake}):
            self.assertIsNone(semantic.load_embedder(force_reload=True))
        self.assertIn('modelo indisponível', semantic.status()['reason'])

    def test_resultado_e_cacheado(self):
        with patch.dict(os.environ, {'SETVO_EMBED_DISABLE': '1'}):
            semantic.load_embedder()
            with patch.dict(os.environ, {'SETVO_EMBED_DISABLE': '0'}):
                self.assertIsNone(semantic.load_embedder())  # ainda o resultado anterior


@unittest.skipUnless(os.environ.get('SETVO_RUN_MODEL_TESTS') == '1',
                     'Teste com o modelo real: defina SETVO_RUN_MODEL_TESTS=1 (exige sentence-transformers e download do modelo).')
class RealModelTests(unittest.TestCase):
    def test_recall_multilingue_minimo_com_modelo_real(self):
        semantic.reset()
        emb = semantic.load_embedder(force_reload=True)
        self.assertIsNotNone(emb, semantic.status()['reason'])
        pairs = json.loads((FIX / 'clusters_crosslang_eval.json').read_text(encoding='utf-8'))['pairs']
        a = emb.embed([p['a'] for p in pairs])
        b = emb.embed([p['b'] for p in pairs])
        sims = (a * b).sum(axis=1)
        positives = [s for s, p in zip(sims, pairs) if p['same']]
        self.assertTrue(all(s >= semantic.DEFAULT_THRESHOLD for s in positives),
                        f'pares do mesmo problema abaixo do limiar: {positives}')
        negatives = [s for s, p in zip(sims, pairs) if not p['same']]
        self.assertTrue(all(s < semantic.DEFAULT_THRESHOLD for s in negatives))
        semantic.reset()


if __name__ == '__main__':
    unittest.main()
