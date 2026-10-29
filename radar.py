#!/usr/bin/env python3
"""
Radar de mercado tech/startups (Brasil + global).
Coleta -> normaliza -> deduplica -> classifica por setor -> pontua -> resumo.

Uso:
  python radar.py collect          # coleta tudo e grava no SQLite
  python radar.py digest           # monta o resumo (imprime e envia ao Telegram se configurado)
  python radar.py run              # collect + digest
  python radar.py loop --every 30  # repete a cada 30 minutos
"""
import argparse
import hashlib
import math
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qsl, urlencode
from insights import detect_signal

try:
    import feedparser
except ImportError:
    import rss_compat as feedparser  # fallback sem instalação externa
import requests
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
# SQLite e configurações de usuário NÃO ficam dentro do executável empacotado.
if getattr(__import__('sys'), 'frozen', False):
    _base = os.environ.get('LOCALAPPDATA') or os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
    USER_DATA_DIR = os.path.join(_base, 'RadarStartupIntelligence')
    os.makedirs(USER_DATA_DIR, exist_ok=True)
else:
    USER_DATA_DIR = HERE
DB_PATH = os.path.join(USER_DATA_DIR, 'radar.db')
UA = "Mozilla/5.0 (compatible; MarketRadar/0.1; personal research)"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": UA})


# ------------------------------------------------------------------ util
def load_env():
    path = os.path.join(USER_DATA_DIR, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_config():
    # Permite configurar fontes fora do executável em %LOCALAPPDATA%.
    user_config = os.path.join(USER_DATA_DIR, 'config.yaml')
    default_config = os.path.join(HERE, 'config.yaml')
    with open(user_config if os.path.isfile(user_config) else default_config, encoding='utf-8') as f:
        return yaml.safe_load(f)


def now():
    return datetime.now(timezone.utc)


def clean(text, limit=600):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def norm_url(url):
    p = urlparse(url or '')
    # Preserva identificadores essenciais em queries (HN ?id=123, YouTube ?v=...).
    # Remove parâmetros de tracking e normaliza ordem para deduplicação segura.
    ignored = {'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid'}
    q = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
               if not k.lower().startswith('utm_') and k.lower() not in ignored)
    suffix = ('?' + urlencode(q)) if q else ''
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}{suffix}"


def item(source, title, url, text="", geo="global", weight=1, engagement=0, kind="news", published=None):
    return {
        "id": hashlib.sha1(norm_url(url).encode()).hexdigest()[:16],
        "source": source, "title": clean(title, 300), "url": url,
        "text": clean(text), "geo": geo, "weight": weight,
        "engagement": engagement, "kind": kind,
        "published": (published or now()).isoformat(),
    }


# ------------------------------------------------------------------ banco
class RadarConnection(sqlite3.Connection):
    """Contexto fecha o arquivo, evitando conexões penduradas no dashboard."""
    def __exit__(self, exc_type, exc_value, exc_tb):
        try:
            return super().__exit__(exc_type, exc_value, exc_tb)
        finally:
            self.close()


def db():
    path = os.environ.get('RADAR_DB', DB_PATH)
    con = sqlite3.connect(path, timeout=20, factory=RadarConnection)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=15000')
    con.execute("""CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY, source TEXT, title TEXT, url TEXT, text TEXT,
        geo TEXT, weight REAL, engagement REAL, kind TEXT, published TEXT,
        collected TEXT, sector TEXT, score REAL, summary TEXT, sent INTEGER DEFAULT 0,
        signal TEXT DEFAULT 'tendencia', pain_level INTEGER DEFAULT 0,
        demo INTEGER DEFAULT 0)""")
    # Migração automática de bancos da versão original.
    cols = {r['name'] for r in con.execute('PRAGMA table_info(items)')}
    needs_backfill = 'signal' not in cols
    for name, ddl in [('signal', "TEXT DEFAULT 'tendencia'"),
                      ('pain_level', 'INTEGER DEFAULT 0'), ('demo', 'INTEGER DEFAULT 0')]:
        if name not in cols:
            con.execute(f'ALTER TABLE items ADD COLUMN {name} {ddl}')
    con.execute("""CREATE TABLE IF NOT EXISTS opportunity_notes (
        id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'novo',
        notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS collection_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT, finished TEXT,
        seen INTEGER, added INTEGER, status TEXT, details TEXT)""")
    if needs_backfill:
        for row in con.execute('SELECT id, title, text, kind FROM items').fetchall():
            signal, level = detect_signal(dict(row))
            con.execute('UPDATE items SET signal=?, pain_level=? WHERE id=?', (signal, level, row['id']))
    con.execute('CREATE INDEX IF NOT EXISTS idx_items_pub ON items(published)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_items_sector ON items(sector)')
    con.commit()
    return con


def save(con, items, cfg):
    new = 0
    for it in items:
        if not it.get('url') or not it.get('title'):
            continue
        old = con.execute('SELECT engagement FROM items WHERE id=?', (it['id'],)).fetchone()
        if old:
            eng = max(float(old['engagement'] or 0), float(it['engagement'] or 0))
            new_score = compute_score(dict(it, engagement=eng), classify(it, cfg), cfg)
            con.execute('UPDATE items SET engagement=?, score=? WHERE id=?',
                        (eng, new_score, it['id']))
            continue
        sector = classify(it, cfg)
        signal, pain_level = detect_signal(it)
        score = compute_score(it, sector, cfg)
        con.execute("""INSERT INTO items
            (id, source, title, url, text, geo, weight, engagement, kind, published,
             collected, sector, score, summary, sent, signal, pain_level, demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?, ?)""",
            (it['id'], it['source'], it['title'], it['url'], it['text'], it['geo'],
             it['weight'], it['engagement'], it['kind'], it['published'],
             now().isoformat(), sector, score, signal, pain_level, int(it.get('demo', 0))))
        new += 1
    con.commit()
    return new


def feed_date(entry):
    parsed = entry.get('published_parsed') or entry.get('updated_parsed')
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return None


# ------------------------------------------------------------------ coletores
def collect_rss(cfg):
    out = []
    for f in cfg["feeds"]:
        try:
            r = HTTP.get(f["url"], timeout=20)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            for e in feed.entries[:25]:
                out.append(item(f["name"], e.get("title", ""), e.get("link", ""),
                                e.get("summary", ""), f["geo"], f["weight"], 0, "news", feed_date(e)))
            print(f"  [rss] {f['name']}: {len(feed.entries[:25])}")
        except Exception as ex:
            print(f"  [rss] FALHOU {f['name']}: {str(ex)[:80]}")
    return out


def collect_reddit(cfg):
    out = []
    for s in cfg["reddit"]:
        try:
            r = None
            for host in ("www.reddit.com", "old.reddit.com"):
                r = HTTP.get(f"https://{host}/r/{s['name']}/new/.rss", timeout=20)
                if r.ok:
                    break
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            for e in feed.entries[:25]:
                out.append(item(f"r/{s['name']}", e.get("title", ""), e.get("link", ""),
                                e.get("summary", ""), s["geo"], 1, 0, "community", feed_date(e)))
            print(f"  [reddit] r/{s['name']}: {len(feed.entries[:25])}")
        except Exception as ex:
            print(f"  [reddit] bloqueado/indisponível ({str(ex)[:40]}); pulando o Reddit neste ciclo")
            break
    return out


def collect_hn(cfg):
    c = cfg["hackernews"]
    since = int((now() - timedelta(hours=c["hours"])).timestamp())
    try:
        r = HTTP.get("https://hn.algolia.com/api/v1/search_by_date", timeout=20, params={
            "tags": "story", "hitsPerPage": 100,
            "numericFilters": f"points>={c['min_points']},created_at_i>{since}"})
        r.raise_for_status()
        out = []
        for h in r.json()["hits"]:
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
            hn_link = f"https://news.ycombinator.com/item?id={h['objectID']}"
            title = h.get("title", "")
            kind = "launch" if title.startswith("Show HN") else "community"
            out.append(item("Hacker News", title, url, f"Discussão: {hn_link}", "global", 2,
                            h.get("points", 0) + h.get("num_comments", 0), kind,
                            datetime.fromtimestamp(h["created_at_i"], tz=timezone.utc) if h.get("created_at_i") else None))
        print(f"  [hn] {len(out)}")
        return out
    except Exception as ex:
        print(f"  [hn] FALHOU: {str(ex)[:80]}")
        return []


def collect_ask_hn(cfg):
    """Perguntas abertas de fundadores/usuários (evidência indireta)."""
    c = cfg.get('ask_hn', {})
    if not c.get('enabled', True):
        return []
    since = int((now() - timedelta(hours=int(c.get('hours', 168)))).timestamp())
    try:
        r = HTTP.get('https://hn.algolia.com/api/v1/search_by_date', timeout=20, params={
            'tags': 'ask_hn', 'hitsPerPage': min(100, int(c.get('max_results', 60))),
            'numericFilters': f'created_at_i>{since}'})
        r.raise_for_status()
        output = []
        for hit in r.json().get('hits', []):
            title = hit.get('title', '')
            if not title:
                continue
            url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
            output.append(item('Ask HN', title, url,
                               hit.get('story_text') or '', 'global', 2,
                               (hit.get('points') or 0) + (hit.get('num_comments') or 0),
                               'ask', datetime.fromtimestamp(hit['created_at_i'], tz=timezone.utc)
                               if hit.get('created_at_i') else None))
        print(f'  [ask hn] {len(output)}')
        return output
    except Exception as exc:
        print(f'  [ask hn] FALHOU: {str(exc)[:80]}')
        return []


def collect_github_issues(cfg):
    """Pedidos públicos de funcionalidades; consulta limitada e respeita rate limits."""
    c = cfg.get('github_issues', {})
    if not c.get('enabled', False):
        return []
    since = (now() - timedelta(days=int(c.get('days', 14)))).strftime('%Y-%m-%d')
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    results = []
    for query in c.get('queries', [])[:3]:
        try:
            r = HTTP.get('https://api.github.com/search/issues', headers=headers, timeout=25,
                         params={'q': f'{query} created:>={since}', 'sort': 'comments',
                                 'order': 'desc', 'per_page': min(int(c.get('max_results', 20)), 50)})
            r.raise_for_status()
            for it in r.json().get('items', []):
                if 'pull_request' in it:
                    continue
                results.append(item('GitHub Issues', it.get('title', ''), it.get('html_url', ''),
                                    it.get('body') or '', 'global', 1,
                                    it.get('comments') or 0, 'issue',
                                    datetime.fromisoformat(it['created_at'].replace('Z', '+00:00'))
                                    if it.get('created_at') else None))
        except Exception as exc:
            print(f'  [github issues] falha/limite: {str(exc)[:70]}')
            if 'rate limit' in str(exc).lower() or getattr(getattr(exc, 'response', None), 'status_code', None) in (403, 429):
                break
    print(f'  [github issues] {len(results)}')
    return results


def collect_github(cfg):
    c = cfg["github"]
    day = (now() - timedelta(days=c["days"])).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        r = HTTP.get("https://api.github.com/search/repositories", headers=headers, timeout=20,
                     params={"q": f"created:>{day} stars:>={c['min_stars']}",
                             "sort": "stars", "order": "desc", "per_page": 40})
        r.raise_for_status()
        out = []
        spam = cfg["github"].get("spam_words", [])
        for repo in r.json()["items"]:
            blob = f"{repo['full_name']} {repo.get('description') or ''}".lower()
            if any(w in blob for w in spam):
                continue
            out.append(item("GitHub", f"{repo['full_name']}: {(repo.get('description') or '')[:140]}",
                            repo["html_url"], " ".join(repo.get("topics", [])), "global", 2,
                            repo["stargazers_count"], "tech",
                            datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")) if repo.get("created_at") else None))
        print(f"  [github] {len(out)}")
        return out
    except Exception as ex:
        print(f"  [github] FALHOU: {str(ex)[:80]}")
        return []


def collect_arxiv(cfg):
    out = []
    c = cfg["arxiv"]
    for cat in c["categories"]:
        try:
            r = HTTP.get("https://export.arxiv.org/api/query", timeout=30, params={
                "search_query": f"cat:{cat}", "sortBy": "submittedDate",
                "sortOrder": "descending", "max_results": c["max_results"]})
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            for e in feed.entries:
                out.append(item(f"arXiv {cat}", e.get("title", ""), e.get("link", ""),
                                e.get("summary", ""), "global", 1, 0, "research", feed_date(e)))
            print(f"  [arxiv] {cat}: {len(feed.entries)}")
        except Exception as ex:
            print(f"  [arxiv] FALHOU {cat}: {str(ex)[:80]}")
        time.sleep(3)  # a arXiv pede intervalo entre chamadas
    return out


# ------------------------------------------------------------------ classificação e pontuação
_RX = {}


def _has(word, blob):
    rx = _RX.get(word)
    if rx is None:
        tail = r"(?![a-zà-ú0-9])" if len(word) <= 4 else ""
        rx = _RX[word] = re.compile(r"(?<![a-zà-ú0-9])" + re.escape(word) + tail)
    return bool(rx.search(blob))


def classify(it, cfg):
    blob = f"{it['title']} {it['text']}".lower()
    best, best_hits = "Outros", 0
    for sector, words in cfg["sectors"].items():
        hits = sum(1 for w in words if _has(w, blob))
        if hits > best_hits:
            best, best_hits = sector, hits
    return best


def compute_score(it, sector, cfg):
    blob = f"{it['title']} {it['text']}".lower()
    score = float(it["weight"])                                       # peso da fonte
    score += min(3.0, math.log10(1 + it["engagement"]) * 1.2)         # engajamento (log)
    score += 1.0 * min(2, sum(1 for w in cfg["novelty_words"] if _has(w, blob)))  # sinal de novidade
    if sector != "Outros":
        score += 1.5                                                  # dentro dos seus setores
    if it["kind"] == "launch":
        score += 1.0
    if it["kind"] == "research":
        score -= 0.5                                                  # arXiv é volumoso
    return round(score, 2)


# ------------------------------------------------------------------ LLM opcional
def llm_summarize(rows):
    """Resume em português e dá nota 1-5 de relevância. Só roda se houver ANTHROPIC_API_KEY."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not rows:
        return {}
    model = os.environ.get("RADAR_MODEL", "claude-haiku-4-5-20251001")
    listing = "\n".join(f"{i}. [{r[1]}] {r[2]} | {r[3][:300]}" for i, r in enumerate(rows))
    prompt = (
        "Para cada item abaixo, escreva UMA frase em português dizendo o que aconteceu e por que "
        "importa para quem acompanha o mercado de tecnologia e startups. Responda uma linha por item "
        "no formato `número|frase`, sem mais nada.\n\n" + listing)
    try:
        r = HTTP.post("https://api.anthropic.com/v1/messages", timeout=60,
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                      json={"model": model, "max_tokens": 1500,
                            "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        out = {}
        for line in text.splitlines():
            m = re.match(r"\s*(\d+)\s*\|\s*(.+)", line)
            if m:
                out[int(m.group(1))] = m.group(2).strip()
        return out
    except Exception as ex:
        print(f"  [llm] falhou, seguindo sem resumo: {str(ex)[:80]}")
        return {}


# ------------------------------------------------------------------ resumo
def select_balanced(rows, d):
    """rows: (id, source, title, text, url, sector, geo, score) ordenadas por nota.
    Limita por fonte e por setor e garante uma cota mínima do Brasil."""
    per_source, per_sector, chosen = {}, {}, []
    def ok(r):
        cap_sec = d["per_other"] if r[5] == "Outros" else d["per_sector"]
        return per_source.get(r[1], 0) < d["per_source"] and per_sector.get(r[5], 0) < cap_sec
    def take(r):
        chosen.append(r)
        per_source[r[1]] = per_source.get(r[1], 0) + 1
        per_sector[r[5]] = per_sector.get(r[5], 0) + 1
    for r in rows:                       # 1ª passada: cotas por fonte e setor
        if len(chosen) < d["max_items"] and ok(r):
            take(r)
    br = [r for r in chosen if r[6] == "brasil"]
    if len(br) < d["min_brasil"]:        # 2ª passada: reforça o Brasil
        extra = [r for r in rows if r[6] == "brasil" and r[5] != "Outros" and r not in chosen
                 and per_source.get(r[1], 0) < d["per_source"]]
        for r in extra:
            if len([x for x in chosen if x[6] == "brasil"]) >= d["min_brasil"]:
                break
            if not ok(r):
                continue
            if len(chosen) >= d["max_items"]:
                removable = next((x for x in reversed(chosen) if x[6] != "brasil"), None)
                if removable is None:
                    break
                chosen.remove(removable)
                per_source[removable[1]] -= 1
                per_sector[removable[5]] -= 1
            take(r)
    return sorted(chosen, key=lambda r: -r[7])


def build_digest(cfg):
    con = db()
    d = cfg["digest"]
    rows = con.execute(
        "SELECT id, source, title, text, url, sector, geo, score FROM items "
        "WHERE sent=0 AND demo=0 AND score>=? ORDER BY score DESC LIMIT 400", (d["min_score"],)).fetchall()
    rows = select_balanced(rows, d)
    if not rows:
        con.close()
        return None
    con.close()
    summaries = llm_summarize([(r[0], r[1], r[2], r[3]) for r in rows])
    by_sector = {}
    for i, r in enumerate(rows):
        by_sector.setdefault(r[5], []).append((i, r))
    lines = [f"📡 Radar de mercado — {datetime.now().strftime('%d/%m/%Y %H:%M')}", ""]
    for sector, entries in by_sector.items():
        lines.append(f"▌{sector}")
        for i, r in entries:
            flag = "🇧🇷" if r[6] == "brasil" else "🌎"
            desc = summaries.get(i, "")
            lines.append(f"{flag} {r[2][:160]}  ({r[1]}, nota {r[7]})")
            if desc:
                lines.append(f"   → {desc}")
            lines.append(f"   {r[4]}")
        lines.append("")
    return "\n".join(lines), [r[0] for r in rows]


def send_telegram(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return False
    try:
        for part in range(0, len(text), 3800):
            r = HTTP.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          json={"chat_id": chat, "text": text[part:part + 3800],
                                "disable_web_page_preview": True}, timeout=20)
            r.raise_for_status()
            if not r.json().get('ok'):
                return False
        return True
    except requests.RequestException as exc:
        print(f'  [telegram] falhou: {str(exc)[:100]}')
        return False


# ------------------------------------------------------------------ comandos
def cmd_collect(cfg):
    print("Coletando...")
    started = now().isoformat()
    seen = new = 0
    con = db()
    for fn in (collect_rss, collect_reddit, collect_hn, collect_ask_hn, collect_github, collect_github_issues, collect_arxiv):
        batch = fn(cfg)
        seen += len(batch)
        new += save(con, batch, cfg)  # persistência incremental: falhas posteriores não perdem o progresso
    con.execute("INSERT INTO collection_runs (started, finished, seen, added, status, details) VALUES (?, ?, ?, ?, ?, ?)",
                (started, now().isoformat(), seen, new, 'concluido', 'Coleta concluída; confira alertas de cada fonte no terminal.'))
    con.commit()
    con.close()
    print(f"Itens vistos: {seen} | novos gravados: {new}")


def cmd_digest(cfg):
    result = build_digest(cfg)
    if not result:
        print("Nada novo acima da nota mínima.")
        return
    message, ids = result
    print(message)
    # Só marca como enviado se não houver Telegram configurado, ou se a entrega for bem-sucedida.
    telegram_configured = bool(os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'))
    succeeded = send_telegram(message) if telegram_configured else True
    if succeeded:
        with db() as con:
            con.executemany('UPDATE items SET sent=1 WHERE id=?', [(id_,) for id_ in ids])
    if telegram_configured:
        print('(enviado ao Telegram)' if succeeded else '(Telegram indisponível; itens continuam pendentes)')


def main():
    load_env()
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "digest", "run", "loop", "demo"])
    ap.add_argument("--every", type=int, default=30, help="minutos entre ciclos (loop)")
    a = ap.parse_args()
    if a.cmd == "demo":
        from demo_data import seed_demo
        os.environ['RADAR_DB'] = os.path.join(HERE, 'radar_demo.db')
        seed_demo()
        print('Exemplos inseridos em radar_demo.db (NÃO são dados reais). Inicie: python dashboard.py --demo')
    elif a.cmd == "collect":
        cmd_collect(cfg)
    elif a.cmd == "digest":
        cmd_digest(cfg)
    elif a.cmd == "run":
        cmd_collect(cfg)
        cmd_digest(cfg)
    else:
        while True:
            cmd_collect(cfg)
            cmd_digest(cfg)
            time.sleep(a.every * 60)


if __name__ == "__main__":
    main()
