#!/usr/bin/env python3
"""Janela Windows do Setvo, com banco local persistente e backend em localhost.

Modo --self-test: verifica o backend no processo empacotado, sem abrir interface.
Modo --collect: subprocesso sem GUI utilizado pelo botão Atualizar radar.
"""
import argparse
from contextlib import closing
import json
import os
import sys
import shutil
import sqlite3
import threading
from http.client import HTTPConnection
from pathlib import Path

APP_NAME = 'SetvoIntelligence'
LEGACY_APP_NAME = 'RadarStartupIntelligence'


def data_dir():
    """Pasta gravável independente do local em que o aplicativo foi instalado."""
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    else:
        base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / APP_NAME


def migrate_legacy_data(directory):
    """Preserva pesquisas Radar 2.1 ao adotar a marca Setvo sem tocar no Setvo antigo."""
    legacy = directory.parent / LEGACY_APP_NAME
    if not legacy.is_dir() or legacy == directory:
        return
    for filename in ('radar.db', 'radar_demo.db'):
        source, target = legacy / filename, directory / filename
        if source.is_file() and not target.exists():
            # SQLite backup inclui transações do WAL do banco antigo quando acessível.
            try:
                with closing(sqlite3.connect(f'file:{source.as_posix()}?mode=ro', uri=True)) as src:
                    with closing(sqlite3.connect(target)) as dst:
                        src.backup(dst)
            except (OSError, sqlite3.Error) as exc:
                target.unlink(missing_ok=True)
                (directory / 'migration-warning.log').write_text(
                    f'Não foi possível copiar {filename}: {exc}\n', encoding='utf-8'
                )
    for filename in ('config.yaml', '.env'):
        source, target = legacy / filename, directory / filename
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)


def configure_environment(demo=False):
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    migrate_legacy_data(directory)
    os.environ['SETVO_USER_DATA_DIR'] = str(directory)
    # Um .exe com --windowed pode não possuir stdout/stderr. Sem isso,
    # até o log HTTP do servidor local pode causar exceções silenciosas.
    if sys.stdout is None or sys.stderr is None:
        log = open(directory / 'setvo-desktop.log', 'a', encoding='utf-8', buffering=1)
        if sys.stdout is None:
            sys.stdout = log
        if sys.stderr is None:
            sys.stderr = log
    if demo:
        # Nunca permitir que --demo escreva no banco real, mesmo com RADAR_DB definido.
        os.environ['RADAR_DB'] = str(directory / 'radar_demo.db')
    else:
        os.environ.setdefault('RADAR_DB', str(directory / 'radar.db'))
    os.environ['RADAR_DEMO'] = '1' if demo else '0'
    return directory


def build_server(demo=False):
    configure_environment(demo)
    from dashboard import create_server
    if demo:
        from demo_data import seed_demo
        # Usa um banco separado para nunca confundir exemplos com dados reais.
        seed_demo()
    return create_server(port=0, host='127.0.0.1')


def self_test():
    server = build_server(demo=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        con = HTTPConnection('127.0.0.1', server.server_port, timeout=10)
        con.request('GET', '/')
        page = con.getresponse()
        body = page.read()
        if page.status != 200 or b'<html' not in body.lower():
            raise RuntimeError('HTML indisponível no backend local')
        con.request('GET', '/api/overview')
        response = con.getresponse()
        data = json.loads(response.read())
        if response.status != 200 or 'total' not in data:
            raise RuntimeError('API de dashboard inválida')
        con.close()
        print('SELF-TEST OK: HTML e API local respondendo, porta dinâmica, SQLite persistente.')
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_desktop(demo=False):
    server = build_server(demo=demo)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name='radar-local-api')
    thread.start()
    try:
        import webview  # pywebview é necessário apenas ao abrir a janela
        url = f'http://127.0.0.1:{server.server_port}/'
        webview.create_window(
            'Setvo — Inteligência de Mercado', url=url,
            width=1360, height=860, min_size=(980, 650),
            background_color='#0b121b', confirm_close=True,
        )
        webview.start(gui='edgechromium', debug=False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Setvo — Inteligência de Mercado para Windows')
    parser.add_argument('--demo', action='store_true', help='Exemplos fictícios isolados')
    parser.add_argument('--self-test', action='store_true', help='Teste rápido do executável, sem janela')
    parser.add_argument('--collect', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--due', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.collect:
        configure_environment(demo=False)
        from radar import cmd_collect, load_config, load_env
        load_env()
        cmd_collect(load_config())
        return 0
    if args.due:
        # Chamado pelo Agendador de Tarefas do Windows: coleta só se a agenda estiver ativa e vencida.
        configure_environment(demo=False)
        from radar import cmd_due, load_config, load_env
        load_env()
        cmd_due(load_config())
        return 0
    if args.self_test:
        return self_test()
    run_desktop(demo=args.demo)
    return 0


if __name__ == '__main__':
    sys.exit(main())
