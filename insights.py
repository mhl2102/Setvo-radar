"""Inteligência baseada em evidências públicas: não constitui validação de mercado."""
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

PAIN_PATTERNS = [
    r'\b(?:struggl(?:e|ing)|frustrat(?:ed|ing)|pain\s*point|broken|manual(?:ly)?|tedious|time.consuming|workaround|can.t\s+(?:find|use|afford)|too\s+expensive)\b',
    r'\b(?:problem(?:s)?|difficult|hard\s+to|need\s+(?:a|an|to)|wish\s+(?:there|i)|looking\s+for|how\s+do\s+(?:you|i))\b',
    r'\b(?:dificuldade(?:s)?|problema(?:s)?|reclama(?:cao|coes)|nao\s+consigo|precis(?:o|amos)\s+(?:de|um|uma)|falta\s+(?:de|um|uma)|demora|caro|custoso|retrabalho|planilha(?:s)?\s+manual)\b',
]
REQUEST_PATTERNS = [
    r'\b(?:feature\s+request|please\s+add|request\s+for|would\s+be\s+(?:nice|great)|requesting|missing\s+(?:feature|support)|support\s+for)\b',
    r'\b(?:solicita(?:cao|coes)|gostaria\s+de|poderia\s+(?:ter|adicionar)|precisa\s+(?:incluir|integrar))\b',
]
COMPANIES = {
    'Microsoft': ['microsoft', 'azure', 'copilot'], 'Google': ['google', 'deepmind', 'gemini', 'alphabet'],
    'Amazon': ['amazon', 'aws'], 'Apple': ['apple', 'ios', 'macos'],
    'Meta': ['meta', 'meta ai', 'facebook', 'instagram', 'llama'],
    'OpenAI': ['openai', 'chatgpt', 'gpt-'], 'Anthropic': ['anthropic', 'claude'],
    'Nvidia': ['nvidia', 'cuda', 'geforce'], 'ByteDance': ['bytedance', 'tiktok'],
    'Tesla': ['tesla', 'optimus'], 'SpaceX': ['spacex', 'starlink'],
}


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', (value or '').lower())
                   if not unicodedata.combining(c))


def matches(text, terms):
    blob = normalize(text)
    return [term for term in terms if normalize(term) in blob]


def detect_signal(item):
    """Rótulo heurístico; não confundir com intenção de compra comprovada."""
    blob = normalize((item.get('title') or '') + ' ' + (item.get('text') or ''))
    pain = sum(bool(re.search(pattern, blob)) for pattern in PAIN_PATTERNS)
    requests = sum(bool(re.search(pattern, blob)) for pattern in REQUEST_PATTERNS)
    if item.get('kind') == 'issue':
        return ('pedido', max(1, min(3, pain + requests + 1)))
    if item.get('kind') == 'ask':
        return ('dor' if pain or requests else 'discussao', min(3, pain + requests))
    if pain or requests:
        if item.get('kind') in ('community', 'issue', 'ask'):
            return ('dor' if pain else 'pedido', min(3, pain + requests))
        return ('indicacao', min(2, pain + requests))  # notícia sobre dor ≠ relato em 1a pessoa
    if item.get('kind') == 'research':
        return ('pesquisa', 0)
    if item.get('kind') in ('launch', 'tech'):
        return ('lancamento', 0)
    return ('tendencia', 0)


def mentioned_companies(text):
    raw = normalize(text)
    result = []
    for name, aliases in COMPANIES.items():
        if any(re.search(r'(?<!\w)' + re.escape(normalize(alias)) + r'(?!\w)', raw) for alias in aliases):
            result.append(name)
    return result


def _as_datetime(v):
    try:
        dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (AttributeError, ValueError):
        return None


def build_opportunities(rows, themes, days=30, user_states=None, current=None):
    """Agrupa itens reais por tema. Não gera oportunidades sem evidências."""
    current = current or datetime.now(timezone.utc)
    start = current - timedelta(days=days)
    prior_start = current - timedelta(days=days * 2)
    groups = []
    state = user_states or {}
    for theme_id, spec in themes.items():
        matched = []
        for r in rows:
            combined = (r['title'] or '') + ' ' + (r['text'] or '')
            if matches(combined, spec.get('keywords', [])):
                matched.append(r)
        recent = [r for r in matched if (dt := _as_datetime(r['published'])) and dt >= start and dt <= current + timedelta(days=1) and not r.get('demo')]
        # Em modo demo a origem é explicitamente fictícia, mas pode ser explorada separadamente.
        demo = [r for r in matched if r.get('demo') and (dt := _as_datetime(r['published'])) and dt >= start]
        evidence = recent or demo
        if not evidence:
            continue
        previous = [r for r in matched if (dt := _as_datetime(r['published'])) and prior_start <= dt < start and not r.get('demo')]
        direct = [r for r in evidence if r.get('signal') in ('dor', 'pedido')]
        sources = sorted({r['source'] for r in evidence})
        # Nota de priorização (não é estimativa de TAM nem probabilidade de sucesso).
        volume_points = min(25, len(evidence) * 3)
        pain_points = min(40, len(direct) * 8)
        diversity_points = min(20, max(0, len(sources) - 1) * 5)
        engagement_points = min(15, sum(min(3, math.log1p(max(0, r.get('engagement') or 0))) for r in evidence))
        score = int(round(min(100, 10 + volume_points + pain_points + diversity_points + engagement_points)))
        if not direct:
            evidence_level = 'Apenas tendência'
        elif len(direct) >= 3 and len({r['source'] for r in direct}) >= 2:
            evidence_level = 'Sinais recorrentes'
        else:
            evidence_level = 'Indício inicial'
        current_data = state.get(theme_id, {})
        groups.append({
            'id': theme_id, 'name': spec.get('name', theme_id), 'sector': spec.get('sector', 'Outros'),
            'problem': spec.get('problem', ''), 'customer': spec.get('customer', ''),
            'mvp': spec.get('mvp', ''), 'validation': spec.get('validation', ''),
            'business_model': spec.get('business_model', ''), 'score': score,
            'evidence_level': evidence_level, 'total': len(evidence), 'direct': len(direct),
            'sources': sources, 'source_count': len(sources), 'previous': len(previous),
            'demo': bool(demo and not recent), 'status': current_data.get('status', 'novo'),
            'notes': current_data.get('notes', ''), 'updated_at': current_data.get('updated_at'),
            'evidence': [dict(id=r['id'], title=r['title'], url=r['url'], source=r['source'],
                              signal=r.get('signal', 'tendencia'), published=r['published'],
                              excerpt=(r['text'] or '')[:260], demo=bool(r.get('demo')))
                         for r in sorted(evidence, key=lambda x: (-int(x.get('pain_level', 0)), -float(x.get('score', 0))))[:12]],
        })
    return sorted(groups, key=lambda g: (-g['direct'], -g['score'], -g['total'], g['name']))


def summarize_sector_trends(rows, config, now_dt=None):
    current = now_dt or datetime.now(timezone.utc)
    cut = current - timedelta(days=7)
    before = cut - timedelta(days=7)
    sectors = list(config.get('sectors', {})) + ['Outros']
    out = []
    for sector in sectors:
        subset = [r for r in rows if r.get('sector') == sector and not r.get('demo')]
        recent = sum(1 for r in subset if (v := _as_datetime(r['published'])) and cut <= v <= current + timedelta(days=1))
        prev = sum(1 for r in subset if (v := _as_datetime(r['published'])) and before <= v < cut)
        out.append({'sector': sector, 'recent': recent, 'previous': prev,
                    'difference': recent - prev,
                    'growth_pct': round(100 * (recent - prev) / prev, 1) if prev else None})
    return sorted(out, key=lambda a: (-a['recent'], a['sector']))
