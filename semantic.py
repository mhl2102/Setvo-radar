"""Agrupamento semântico multilíngue (opcional).

Backend: sentence-transformers com o modelo multilíngue
'paraphrase-multilingual-MiniLM-L12-v2' (384 dimensões).

Decisão (ver docs/SETVO_DECISOES.md, D6):
- Opcional. Se as dependências ou o modelo não estiverem disponíveis, o sistema usa o
  agrupamento lexical de clusters.py e informa qual método foi utilizado.
- Nada é enviado a APIs externas: o modelo roda localmente na CPU.
- O modelo não é empacotado no .exe; é carregado quando instalado pelo usuário.

Variáveis de ambiente:
  SETVO_EMBED_MODEL  caminho local ou nome do modelo (padrão: o multilíngue acima)
  SETVO_EMBED_DISABLE=1  desativa o backend semântico
"""
import os
import threading

DEFAULT_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
DEFAULT_THRESHOLD = 0.65  # escolhido no benchmark (docs/SETVO_TESTES.md); conjunto pequeno

_LOCK = threading.Lock()
_STATE = {'loaded': False, 'embedder': None, 'reason': 'não carregado'}


class SentenceEmbedder:
    def __init__(self, model):
        self._model = model

    def embed(self, texts):
        import numpy as np
        vectors = self._model.encode(list(texts), normalize_embeddings=True, batch_size=32,
                                     show_progress_bar=False)
        return np.asarray(vectors, dtype='float32')


def load_embedder(force_reload=False):
    """Retorna um embedder ou None. Nunca lança exceção: o fallback é sempre possível."""
    with _LOCK:
        if _STATE['loaded'] and not force_reload:
            return _STATE['embedder']
        _STATE.update(loaded=True, embedder=None)
        if os.environ.get('SETVO_EMBED_DISABLE') == '1':
            _STATE['reason'] = 'desativado por SETVO_EMBED_DISABLE'
            return None
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            _STATE['reason'] = 'sentence-transformers não instalado'
            return None
        try:
            model = SentenceTransformer(os.environ.get('SETVO_EMBED_MODEL', DEFAULT_MODEL), device='cpu')
            _STATE.update(embedder=SentenceEmbedder(model), reason='carregado')
        except Exception as ex:  # modelo ausente, sem rede, arquivo corrompido
            _STATE['reason'] = f'modelo indisponível: {type(ex).__name__}'
        return _STATE['embedder']


def reset():
    """Limpa o cache do embedder (usado pelos testes)."""
    with _LOCK:
        _STATE.update(loaded=False, embedder=None, reason='não carregado')


def status():
    return {'available': _STATE['embedder'] is not None, 'reason': _STATE['reason']}


def cluster_semantic(items, embedder, threshold=DEFAULT_THRESHOLD):
    """Agrupamento guloso por similaridade de cosseno com o centróide do grupo.

    Mesma estrutura de saída de clusters.cluster_items, para a API tratar os dois de forma igual.
    """
    import numpy as np
    texts = [f"{it.get('title', '')}. {it.get('text', '')}".strip() for it in items]
    usable = [i for i, t in enumerate(texts) if t.strip('. ')]
    if not usable:
        return []
    vectors = embedder.embed([texts[i] for i in usable])
    groups = []  # cada grupo: {'centroid': vetor normalizado, 'members': [índices de items]}
    for pos, idx in enumerate(usable):
        v = vectors[pos]
        best, best_sim = None, -1.0
        for g in groups:
            sim = float(np.dot(g['centroid'], v))
            if sim > best_sim:
                best, best_sim = g, sim
        if best is not None and best_sim >= threshold:
            best['members'].append(idx)
            c = best['sum'] + v
            best['sum'] = c
            best['centroid'] = c / np.linalg.norm(c)
        else:
            groups.append({'centroid': v, 'sum': v.copy(), 'members': [idx]})

    result = []
    for g in groups:
        if len(g['members']) < 2:
            continue
        members = [items[i] for i in g['members']]
        sources = {m.get('source') for m in members if m.get('source')}
        label = _label_for(members)
        result.append({'label': label, 'size': len(members), 'sources': len(sources),
                       'member_ids': [m.get('id') for m in members]})
    result.sort(key=lambda c: (-c['sources'], -c['size']))
    return result


def _label_for(members):
    from clusters import normalize_tokens
    counts = {}
    for m in members:
        for t in normalize_tokens(f"{m.get('title', '')} {m.get('text', '')}"):
            counts[t] = counts.get(t, 0) + 1
    return [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
