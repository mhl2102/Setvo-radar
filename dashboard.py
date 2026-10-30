#!/usr/bin/env python3
"""Interface local de inteligência de oportunidades; escuta só em localhost por padrão.

Uso: python dashboard.py [--port 8765] [--demo]
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import threading
import traceback
from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from radar import HERE, db, load_config, load_env
from insights import COMPANIES, build_opportunities, mentioned_companies, summarize_sector_trends
from garimpo import find_gold

STATE_LOCK = threading.Lock()
COLLECTION_STATE = {'running': False, 'started_at': None, 'completed_at': None, 'status': 'Nunca iniciada nesta sessão', 'log': ''}
ALLOWED_STATUSES = {'novo', 'observando', 'pesquisando', 'validando', 'arquivado'}


def _days(params):
    try:
        return max(1, min(365, int(params.get('days', ['30'])[0])))
    except (ValueError, TypeError):
        return 30


def _rows(con, days=30, include_demo=False):
    dt = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    query = ('SELECT id, source, title, url, text, geo, weight, engagement, kind, '
             'published, collected, sector, score, signal, pain_level, demo FROM items '
             'WHERE published >= ? AND demo = ? ORDER BY published DESC')
    return [dict(r) for r in con.execute(query, (dt, int(include_demo)))]


def _states(con):
    return {r['id']: dict(r) for r in con.execute('SELECT * FROM opportunity_notes')}


def _base(params, cfg):
    use_demo = os.environ.get('RADAR_DEMO', '') == '1'
    with db() as con:
        rows = _rows(con, _days(params), use_demo)
        states = _states(con)
        n_all = con.execute('SELECT COUNT(*) AS n FROM items WHERE demo=?', (int(use_demo),)).fetchone()['n']
        last = con.execute('SELECT * FROM collection_runs ORDER BY id DESC LIMIT 1').fetchone()
    return rows, states, n_all, dict(last) if last else None


def _match_filter(r, params):
    sector = params.get('sector', ['todos'])[0]
    signal = params.get('signal', ['todos'])[0]
    geo = params.get('geo', ['todos'])[0]
    query = params.get('q', [''])[0].strip().casefold()
    company = params.get('company', ['todos'])[0]
    if sector != 'todos' and r['sector'] != sector:
        return False
    if signal != 'todos' and r['signal'] != signal:
        return False
    if geo != 'todos' and r['geo'] != geo:
        return False
    if company != 'todos' and company not in mentioned_companies(r['title'] + ' ' + r['text']):
        return False
    if query and query not in (r['title'] + ' ' + r['text'] + ' ' + r['source']).casefold():
        return False
    return True


def fetch_api(route, params, cfg):
    rows, states, all_count, last = _base(params, cfg)
    demo = os.environ.get('RADAR_DEMO', '') == '1'
    if route == '/api/status':
        with STATE_LOCK:
            return {**COLLECTION_STATE, 'demo': demo, 'last_run': last}
    if route == '/api/config':
        return {'sectors': list(cfg['sectors'].keys()), 'companies': list(COMPANIES),
                'sources': [f['name'] for f in cfg['feeds']], 'demo': demo}
    if route == '/api/overview':
        pain = sum(r['signal'] in ('dor', 'pedido') for r in rows)
        companies = Counter(c for r in rows for c in mentioned_companies(r['title'] + ' ' + r['text']))
        source_counts = Counter(r['source'] for r in rows)
        by_sector = Counter(r['sector'] for r in rows)
        opportunity_groups = build_opportunities(rows, cfg['themes'], _days(params), states)
        return {
            'demo': demo, 'total': len(rows), 'stored': all_count, 'direct_signals': pain,
            'sources_count': len(source_counts), 'countries_brazil': sum(r['geo'] == 'brasil' for r in rows),
            'opportunities': len(opportunity_groups),
            'last_run': last, 'by_sector': [{'name': s, 'count': n} for s, n in by_sector.most_common()],
            'by_source': [{'name': s, 'count': n} for s, n in source_counts.most_common()],
            'big_tech': [{'name': s, 'count': n} for s, n in companies.most_common()],
            'top_opportunities': [{k: v for k, v in group.items() if k != 'evidence'} for group in opportunity_groups[:5]],
            'recent': [dict(r, companies=mentioned_companies(r['title'] + ' ' + r['text'])) for r in rows[:6]],
            'trend': summarize_sector_trends(rows, cfg),
        }
    if route == '/api/items':
        filtered = [dict(r, companies=mentioned_companies(r['title'] + ' ' + r['text']))
                    for r in rows if _match_filter(r, params)]
        sort = params.get('sort', ['recente'])[0]
        if sort == 'score':
            filtered.sort(key=lambda x: (-x['score'], x['title']))
        if sort == 'engagement':
            filtered.sort(key=lambda x: (-x['engagement'], x['title']))
        try:
            page = max(1, min(100000, int(params.get('page', ['1'])[0])))
            size = max(1, min(100, int(params.get('limit', ['18'])[0])))
        except ValueError:
            page, size = 1, 18
        return {'total': len(filtered), 'page': page, 'pages': max(1, (len(filtered)+size-1)//size),
                'items': filtered[(page-1)*size:page*size], 'demo': demo}
    if route == '/api/gold':
        findings = find_gold(rows, cfg['themes'], _days(params))
        minimum = max(0, min(20, int(params.get('min_direct', ['2'])[0]) if params.get('min_direct', ['2'])[0].isdigit() else 2))
        origin = params.get('origin', ['todos'])[0]
        findings = [r for r in findings if r['direct'] >= minimum and (origin == 'todos' or r['origin'] == origin)]
        return {'findings': findings[:80], 'total': len(findings), 'demo': demo,
                'method': 'Triagem heurística baseada em sinais públicos, com rastreabilidade por URL. Não mede TAM, concorrência real ou chance de sucesso.',
                'coverage_warning': 'Ausência de menções ou notícias na amostra não significa ausência de soluções, concorrentes ou investimento.'}
    if route == '/api/opportunities':
        all_ops = build_opportunities(rows, cfg['themes'], _days(params), states)
        sector = params.get('sector', ['todos'])[0]
        status = params.get('status', ['todos'])[0]
        search = params.get('q', [''])[0].strip().casefold()
        ops = [o for o in all_ops if (sector == 'todos' or o['sector'] == sector)
               and (status == 'todos' or o['status'] == status)
               and (not search or search in (o['name']+' '+o['problem']+' '+o['customer']).casefold())]
        return {'opportunities': ops, 'total': len(ops), 'demo': demo,
                'disclaimer': 'As oportunidades são hipóteses automáticas; sinais não comprovam demanda, TAM nem disposição de pagamento.'}
    if route == '/api/trends':
        with db() as con:
            history = _rows(con, 16, demo)
            oldest = con.execute('SELECT MIN(collected) AS d FROM items WHERE demo=?', (int(demo),)).fetchone()['d']
        coverage = bool(oldest and datetime.fromisoformat(oldest) <= datetime.now(timezone.utc)-timedelta(days=14))
        return {'coverage_sufficient': coverage and not demo,
                'note': 'Variação em volume de publicações, não em demanda. Requer histórico contínuo por pelo menos 14 dias.',
                'sectors': summarize_sector_trends(history, cfg)}
    raise KeyError(route)


def export_rows(params, cfg):
    rows, _, _, _ = _base(params, cfg)
    return [r for r in rows if _match_filter(r, params)]


def save_note(data, cfg):
    ident = data.get('id')
    if not isinstance(ident, str) or ident not in cfg['themes']:
        raise ValueError('Tema inválido')
    status = data.get('status', 'novo')
    notes = data.get('notes', '')
    if status not in ALLOWED_STATUSES or not isinstance(notes, str) or len(notes) > 10000:
        raise ValueError('Status ou notas inválidos (limite 10.000 caracteres)')
    with db() as con:
        con.execute("""INSERT INTO opportunity_notes (id, status, notes, updated_at) VALUES (?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET status=excluded.status, notes=excluded.notes,
                       updated_at=excluded.updated_at""",
                    (ident, status, notes, datetime.now(timezone.utc).isoformat()))
    return {'ok': True, 'id': ident, 'status': status}


def _collect_task():
    try:
        command = ([sys.executable, '--collect'] if getattr(sys, 'frozen', False)
                   else [sys.executable, os.path.join(HERE, 'radar.py'), 'collect'])
        process = subprocess.run(command, cwd=HERE, capture_output=True, text=True, timeout=240, check=False,
                                 env=os.environ.copy())
        with STATE_LOCK:
            COLLECTION_STATE['status'] = 'Concluída' if process.returncode == 0 else 'Erro na execução'
            COLLECTION_STATE['log'] = (process.stdout + '\n' + process.stderr)[-16000:]
    except Exception as exc:
        with STATE_LOCK:
            COLLECTION_STATE['status'] = f'Erro: {str(exc)[:250]}'
            COLLECTION_STATE['log'] = str(exc)
    finally:
        with STATE_LOCK:
            COLLECTION_STATE['running'] = False
            COLLECTION_STATE['completed_at'] = datetime.now(timezone.utc).isoformat()


def start_collect():
    if os.environ.get('RADAR_DEMO', '') == '1':
        raise ValueError('Coleta real desativada no banco de demonstração. Abra a versão normal.')
    with STATE_LOCK:
        if COLLECTION_STATE['running']:
            return {'started': False, 'reason': 'Já existe uma coleta em andamento.'}
        COLLECTION_STATE.update(running=True, started_at=datetime.now(timezone.utc).isoformat(),
                                completed_at=None, status='Coletando fontes...', log='')
    threading.Thread(target=_collect_task, daemon=True).start()
    return {'started': True}


class Handler(BaseHTTPRequestHandler):
    server_version = 'SetvoIntelligence/2.3'

    def _send(self, data, code=200, content_type='application/json; charset=utf-8', filename=None):
        b = data if isinstance(data, bytes) else (json.dumps(data, ensure_ascii=False).encode('utf-8')
                                                 if content_type.startswith('application/json') else data.encode('utf-8'))
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(b)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(b)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path
        try:
            if path == '/':
                with open(os.path.join(HERE, 'web', 'index.html'), 'rb') as file:
                    self._send(file.read(), content_type='text/html; charset=utf-8')
            elif path in ('/app.css', '/app.js'):
                ext = 'text/css; charset=utf-8' if path.endswith('.css') else 'text/javascript; charset=utf-8'
                with open(os.path.join(HERE, 'web', path[1:]), 'rb') as file:
                    self._send(file.read(), content_type=ext)
            elif path == '/api/export.csv':
                cols = ['published','source','title','text','url','geo','sector','signal','pain_level','score','engagement']
                stream = io.StringIO()
                writer = csv.DictWriter(stream, fieldnames=cols, extrasaction='ignore', delimiter=';')
                writer.writeheader()
                for row in export_rows(params, self.server.config):
                    safe = {key: ("'" + str(row.get(key, '')) if str(row.get(key, '')).lstrip().startswith(('=', '+', '-', '@'))
                                  else row.get(key, '')) for key in cols}
                    writer.writerow(safe)
                self._send(('\ufeff'+stream.getvalue()).encode('utf-8'), content_type='text/csv; charset=utf-8',
                           filename='setvo_sinais.csv')
            elif path == '/api/export.json':
                self._send(export_rows(params, self.server.config), filename='setvo_sinais.json')
            elif path.startswith('/api/'):
                self._send(fetch_api(path, params, self.server.config))
            else:
                self._send({'error': 'Página não encontrada'}, 404)
        except KeyError:
            self._send({'error': 'Rota não encontrada'}, 404)
        except Exception:
            traceback.print_exc()
            self._send({'error': 'Falha ao consultar dados locais'}, 500)

    def do_POST(self):
        # POST exige JSON; bloqueia envios simples de páginas externas
        # (CSRF contra o serviço local sem autenticação).
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            self._send({'error': 'A API exige application/json'}, 415)
            return
        origin = self.headers.get('Origin')
        if origin and origin != f'http://127.0.0.1:{self.server.server_port}' and origin != f'http://localhost:{self.server.server_port}':
            self._send({'error': 'Origem não permitida'}, 403)
            return
        path = urlparse(self.path).path
        length = self.headers.get('Content-Length', '0')
        try:
            size = int(length)
            if size < 0 or size > 65536:
                self._send({'error': 'Corpo de requisição inválido'}, 413)
                return
            raw = self.rfile.read(size)
            data = json.loads(raw.decode('utf-8')) if raw else {}
            if not isinstance(data, dict):
                raise ValueError('JSON deve ser um objeto')
            if path == '/api/notes':
                self._send(save_note(data, self.server.config))
            elif path == '/api/collect':
                self._send(start_collect(), 202)
            else:
                self._send({'error': 'Rota não encontrada'}, 404)
        except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
            self._send({'error': str(exc)}, 400)
        except Exception:
            traceback.print_exc()
            self._send({'error': 'Erro interno'}, 500)


def create_server(port=8765, host='127.0.0.1'):
    load_env()
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.config = load_config()
    return server


def main():
    parser = argparse.ArgumentParser(description='Setvo — Inteligência de Mercado')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--demo', action='store_true', help='Abre somente exemplos explicitamente fictícios')
    parser.add_argument('--host', default='127.0.0.1', help='Padrão seguro: apenas este computador')
    args = parser.parse_args()
    if args.demo:
        os.environ['RADAR_DEMO'] = '1'
        os.environ['RADAR_DB'] = os.path.join(HERE, 'radar_demo.db')
        if not os.path.exists(os.environ['RADAR_DB']):
            from demo_data import seed_demo
            seed_demo()
    try:
        server = create_server(args.port, args.host)
    except OSError as exc:
        raise SystemExit(f'Não foi possível iniciar a porta {args.port}: {exc}')
    print(f'Setvo disponível em http://{args.host}:{args.port}')
    print('Ctrl+C para encerrar. Nenhum dado é enviado pelo dashboard para servidores externos.')
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print('\nEncerrado.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
