"""Agrupamento de publicações por similaridade lexical.

Limitações deliberadas (ver docs/SETVO_DECISOES.md):
- Não é agrupamento semântico: sinônimos e idiomas diferentes não se aproximam.
  Ex.: "pedido de integração" e "integration request" ficam em grupos separados.
- Usa apenas Python padrão, sem modelos externos nem custo de API.
- Serve como primeira camada: agrupa relatos muito parecidos e separa
  republicações de evidências independentes pela contagem de fontes distintas.
"""
import re
import unicodedata

STOPWORDS = {
    # português
    'para', 'com', 'uma', 'uns', 'umas', 'que', 'por', 'mais', 'como', 'dos', 'das', 'nos', 'nas',
    'pelo', 'pela', 'sobre', 'entre', 'seu', 'sua', 'seus', 'suas', 'ele', 'ela', 'isso', 'este',
    'esta', 'esse', 'essa', 'ser', 'ter', 'foi', 'sao', 'são', 'mas', 'quando', 'onde', 'tambem',
    'também', 'ainda', 'muito', 'pode', 'podem', 'uso', 'usar', 'novo', 'nova',
    # inglês
    'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was', 'were', 'has', 'have', 'not',
    'but', 'you', 'your', 'can', 'its', 'our', 'out', 'new', 'how', 'why', 'what', 'when', 'about',
}

_TOKEN = re.compile(r'[a-z0-9]{3,}')
DEFAULT_THRESHOLD = 0.34
STEM_LEN = 6  # truncamento simples: aproxima flexões (conciliar/conciliação) sem dependências


def normalize_tokens(text):
    """Minúsculas, sem acentos, termos de 3+ caracteres sem stopwords, truncados em STEM_LEN."""
    if not text:
        return set()
    decomposed = unicodedata.normalize('NFKD', str(text).lower())
    ascii_text = ''.join(ch for ch in decomposed if not unicodedata.combining(ch))
    return {t[:STEM_LEN] for t in _TOKEN.findall(ascii_text) if t not in STOPWORDS}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_items(items, threshold=DEFAULT_THRESHOLD):
    """Agrupa itens (dicts com id, title, text, source) de forma gulosa.

    Cada item entra no primeiro grupo cujo termo representativo tenha similaridade
    de Jaccard >= threshold; senão cria um grupo novo. Retorna grupos ordenados por
    número de fontes distintas e depois por tamanho.
    """
    groups = []
    for it in items:
        tokens = normalize_tokens(f"{it.get('title', '')} {it.get('text', '')}")
        if not tokens:
            continue
        best, best_score = None, 0.0
        for g in groups:
            score = jaccard(tokens, g['seed'])
            if score > best_score:
                best, best_score = g, score
        if best is not None and best_score >= threshold:
            best['members'].append(it)
            best['seed'] = best['seed'] | tokens
        else:
            groups.append({'seed': set(tokens), 'members': [it]})

    result = []
    for g in groups:
        if len(g['members']) < 2:
            continue
        sources = {m.get('source') for m in g['members'] if m.get('source')}
        counts = {}
        for m in g['members']:
            for t in normalize_tokens(f"{m.get('title', '')} {m.get('text', '')}"):
                counts[t] = counts.get(t, 0) + 1
        label = [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
        result.append({
            'label': label,
            'size': len(g['members']),
            'sources': len(sources),
            'member_ids': [m.get('id') for m in g['members']],
        })
    result.sort(key=lambda c: (-c['sources'], -c['size']))
    return result
