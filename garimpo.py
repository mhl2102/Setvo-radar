"""Garimpo de sinais de necessidade. Score = triagem, nunca receita ou demanda comprovada.

Cada resultado traz URLs verificáveis, amostragem, grau de recorrência e alerta de
cobertura. Não se presume que baixa cobertura pública signifique baixa concorrência.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import math
import re

from insights import _as_datetime, matches, mentioned_companies, normalize

# Palavras neutras removidas SOMENTE para descobrir expressões recorrentes.
STOP = set('''the a an and or of for to in on with from is are was were be this that
why what how when where who your our their you we i they it its my do does can
could should would using use new best any ask hn show help request feature please
there about after before have has not need looking got make more some one two
which into but as than at by via vs get want want to issue problem hard
um uma uns umas o os as de da do das dos em no na nos nas por para com sem
sobre como que qual quais eu voce você nós nos precisamos preciso minha meu
minha sua seu essa esse isto isso esta estão este aquele numa num muito mais
menos atual novo nova ajuda duvida dúvida pergunta perguntaes'''.split())


def _candidate_phrases(title):
    """Extrai pares/trios de termos substantivos de títulos; não é NLP semântico."""
    title = re.sub(r'^(?:ask\s+hn|show\s+hn|feature\s+request|question)\s*:\s*', '', normalize(title))
    tokens = re.findall(r'[a-z][a-z0-9-]{2,26}', title)
    # Não ligamos palavras através de stopwords, para não criar temas fictícios.
    phrases = set()
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            words = tokens[i:i + n]
            if all(w not in STOP for w in words) and len(set(words)) == n:
                phrases.add(' '.join(words))
    return phrases


def _unique(rows):
    selected = {}
    for row in rows:
        ident = row.get('id') or row.get('url')
        if ident and ident not in selected:
            selected[ident] = row
    return list(selected.values())


def _evaluate(ident, name, rows, kind='emergente', spec=None, current=None):
    evidence = _unique(rows)
    direct = [r for r in evidence if r.get('signal') in ('dor', 'pedido')]
    context = [r for r in evidence if r not in direct]
    direct_sources = len({r.get('source') for r in direct})
    sources = sorted({r.get('source', 'Fonte não identificada') for r in evidence})
    if len(direct) >= 4 and direct_sources >= 3:
        confidence = 'Recorrência em várias fontes'
    elif len(direct) >= 2 and direct_sources >= 2:
        confidence = 'Indícios independentes'
    else:
        confidence = 'Exploratório / evidência limitada'

    # Evidência direta pesa mais que quantidade de manchetes ou estrelas.
    direct_points = min(40, len(direct) * 10)
    sources_points = min(25, max(0, direct_sources - 1) * 10)
    total_points = min(12, len(evidence) * 2)
    engagement_points = min(8, sum(math.log1p(max(0, float(r.get('engagement') or 0))) for r in direct) / 3)
    coverage_points = min(15, max(0, 3 - len(context)) * 5) if len(direct) >= 2 else 0
    score = round(min(100, direct_points + sources_points + total_points + engagement_points + coverage_points))
    coverage = ('Poucas publicações não relacionadas a relatos nesta amostra'
                if len(context) <= 1 and len(direct) >= 2 else
                'Há também notícias e lançamentos; investigar alternativas existentes')
    companies = sorted({c for r in evidence for c in mentioned_companies((r.get('title') or '') + ' ' + (r.get('text') or ''))})
    facts = sorted(evidence, key=lambda r: (-int(r.get('signal') in ('dor', 'pedido')),
                                                  -float(r.get('engagement') or 0), r.get('title') or ''))
    return {
        'id': ident, 'name': name, 'origin': kind, 'sector': (spec or {}).get('sector',
             Counter(r.get('sector') or 'Outros' for r in evidence).most_common(1)[0][0]),
        'score': score, 'confidence': confidence, 'direct': len(direct),
        'total': len(evidence), 'context': len(context), 'source_count': len(sources),
        'direct_source_count': direct_sources, 'sources': sources,
        'coverage': coverage, 'big_tech_mentions': companies,
        'problem': (spec or {}).get('problem') or 'Problema inferido de títulos recorrentes; verificar contexto e usuários afetados.',
        'customer': (spec or {}).get('customer') or 'Público ainda não identificado: descobrir quem relata a dificuldade.',
        'mvp': (spec or {}).get('mvp') or 'Entrevistas e protótipo focado no problema mais repetido.',
        'validation': (spec or {}).get('validation') or 'Confirmar problema com 10 potenciais clientes, mapear soluções atuais e testar piloto pago.',
        'evidence': [dict(id=r.get('id'), title=r.get('title'), url=r.get('url'),
                          source=r.get('source'), published=r.get('published'),
                          signal=r.get('signal'), excerpt=(r.get('text') or '')[:240]) for r in facts[:10]],
        'warning': 'Baixa cobertura na amostra NÃO comprova falta de concorrentes, mercado livre, TAM ou disposição de pagar.',
        'demo': any(bool(r.get('demo')) for r in evidence),
    }


def find_gold(rows, themes, days=30, current=None):
    """Faz triagem de hipóteses conhecidas e descobre temas repetidos sem template.

    - Apenas publicações recentes e URLs únicas.
    - Sem dados = nenhuma conclusão, jamais oportunidade inventada.
    - O campo score é ordinal e não representa chance de sucesso.
    """
    current = current or datetime.now(timezone.utc)
    since = current - timedelta(days=days)
    candidates = _unique([r for r in rows if (dt := _as_datetime(r.get('published'))) and
                         since <= dt <= current + timedelta(days=1) and r.get('url')])
    output, theme_sets = [], []
    for ident, spec in themes.items():
        relevant = [r for r in candidates if matches((r.get('title') or '') + ' ' + (r.get('text') or ''),
                                                      spec.get('keywords', []))]
        if not relevant:
            continue
        group = _evaluate('tema:' + ident, spec.get('name', ident), relevant, 'tema monitorado', spec)
        # Não chamar uma manchete isolada de oportunidade destacada.
        if group['direct']:
            output.append(group)
        theme_sets.append({r.get('id') for r in relevant})

    phrases = defaultdict(list)
    for row in candidates:
        if row.get('signal') not in ('dor', 'pedido'):
            continue
        for phrase in _candidate_phrases(row.get('title') or ''):
            phrases[phrase].append(row)

    dynamic = []
    for phrase, direct_rows in phrases.items():
        if len(direct_rows) < 2 or len({r.get('source') for r in direct_rows}) < 2:
            continue
        # Busca publicações contextuais apenas pela expressão exata; não pressupõe similaridade semântica.
        pattern = re.compile(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)')
        related = [r for r in candidates if pattern.search(normalize((r.get('title') or '') + ' ' + (r.get('text') or '')))]
        if len(related) < 2:
            continue
        ids = {r.get('id') for r in related}
        if any(len(ids & seen) >= len(ids) * .75 for seen in theme_sets):
            continue
        group = _evaluate('descoberta:' + phrase.replace(' ', '-'), phrase.title(), related)
        dynamic.append(group)
    # Desduplicação de expressões do mesmo tema, preservando conjunto mais robusto.
    used = []
    for candidate in sorted(dynamic, key=lambda c: (-c['direct_source_count'], -c['direct'], -c['score'], -len(c['name']), c['name'])):
        seen = {e['id'] for e in candidate['evidence']}
        if any(len(seen & other) >= .75 * min(len(seen), len(other)) for other in used):
            continue
        output.append(candidate)
        used.append(seen)
        if len(used) >= 25:
            break
    return sorted(output, key=lambda c: (-c['direct_source_count'], -c['score'], c['name']))
