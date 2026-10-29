#!/usr/bin/env python3
"""Janela Windows do Radar, com banco local persistente e backend em localhost.

Modo --self-test: verifica o backend no processo empacotado, sem abrir interface.
Modo --collect: subprocesso sem GUI utilizado pelo botão Atualizar radar.
"""
import argparse
import json
import os
import sys
import threading
from http.client import HTTPConnection
from pathlib import Path

APP_NAME = 'RadarStartupIntelligence'


def data_dir():
    """Pasta gravável independente do local em que o aplicativo foi instalado."""
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    else:
        base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / APP_NAME


def configure_environment(demo=False):
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
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
            'Radar Startup Intelligence', url=url,
            width=1360, height=860, min_size=(980, 650),
            background_color='#0b121b', confirm_close=True,
        )
        webview.start(gui='edgechromium', debug=False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Radar Startup Intelligence — Windows')
    parser.add_argument('--demo', action='store_true', help='Exemplos fictícios isolados')
    parser.add_argument('--self-test', action='store_true', help='Teste rápido do executável, sem janela')
    parser.add_argument('--collect', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.collect:
        configure_environment(demo=False)
        from radar import cmd_collect, load_config, load_env
        load_env()
        cmd_collect(load_config())
        return 0
    if args.self_test:
        return self_test()
    run_desktop(demo=args.demo)
    return 0


if __name__ == '__main__':
    sys.exit(main())
