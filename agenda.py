"""Agendamento da coleta automática do Setvo.

Responsabilidades (todas recebem uma conexão SQLite, para facilitar testes):
- guardar a configuração da agenda (intervalo, ativa/pausada, última e próxima execução);
- decidir se uma coleta está vencida;
- registrar o estado de cada coletor (última tentativa, último sucesso, erro, contagem);
- impedir duas coletas simultâneas com uma trava que expira sozinha;
- validar entradas vindas da interface.

Nenhuma função abre conexões próprias nem cria processos em segundo plano.
"""
from datetime import datetime, timedelta, timezone

MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 7 * 24 * 60
DEFAULT_INTERVAL_MINUTES = 360
LOCK_TTL_MINUTES = 30
DEFAULT_NAME = 'coleta_principal'


def utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _parse(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def ensure_tables(con):
    con.execute("""CREATE TABLE IF NOT EXISTS agenda (
        name TEXT PRIMARY KEY,
        interval_minutes INTEGER NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        last_run TEXT,
        next_run TEXT,
        updated_at TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS source_status (
        source TEXT PRIMARY KEY,
        last_attempt TEXT,
        last_success TEXT,
        last_count INTEGER DEFAULT 0,
        last_error TEXT DEFAULT '',
        failures INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS collection_lock (
        name TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        acquired_at TEXT NOT NULL,
        expires_at TEXT NOT NULL)""")
    con.commit()


def validate_interval(value):
    """Converte e valida o intervalo em minutos. Lança ValueError se inválido."""
    if isinstance(value, bool):
        raise ValueError('Intervalo deve ser um número inteiro de minutos')
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise ValueError('Intervalo deve ser um número inteiro de minutos')
    if not MIN_INTERVAL_MINUTES <= minutes <= MAX_INTERVAL_MINUTES:
        raise ValueError(
            f'Intervalo deve estar entre {MIN_INTERVAL_MINUTES} minutos e {MAX_INTERVAL_MINUTES} minutos')
    return minutes


def get_agenda(con, name=DEFAULT_NAME, now=None):
    ensure_tables(con)
    row = con.execute('SELECT * FROM agenda WHERE name=?', (name,)).fetchone()
    if row is None:
        now = now or utc_now()
        set_agenda(con, interval_minutes=DEFAULT_INTERVAL_MINUTES, enabled=False, name=name, now=now)
        row = con.execute('SELECT * FROM agenda WHERE name=?', (name,)).fetchone()
    return {
        'name': row['name'],
        'interval_minutes': row['interval_minutes'],
        'enabled': bool(row['enabled']),
        'last_run': row['last_run'],
        'next_run': row['next_run'],
    }


def set_agenda(con, interval_minutes=None, enabled=None, name=DEFAULT_NAME, now=None):
    """Cria ou atualiza a agenda.

    Regras:
    - pausar limpa a próxima execução;
    - ativar agenda que estava pausada agenda a execução para agora;
    - alterar o intervalo recalcula a próxima execução a partir da última execução.
    """
    ensure_tables(con)
    now = now or utc_now()
    current = con.execute('SELECT * FROM agenda WHERE name=?', (name,)).fetchone()
    if interval_minutes is not None:
        interval = validate_interval(interval_minutes)
    else:
        interval = current['interval_minutes'] if current else DEFAULT_INTERVAL_MINUTES
    was_active = bool(current['enabled']) if current else False
    active = bool(enabled) if enabled is not None else was_active
    last_run = current['last_run'] if current else None
    if not active:
        next_run = None
    elif not was_active:
        next_run = _iso(now)
    elif interval_minutes is not None or current is None or current['next_run'] is None:
        base = _parse(last_run)
        next_run = _iso(base + timedelta(minutes=interval)) if base else _iso(now)
    else:
        next_run = current['next_run']
    con.execute("""INSERT INTO agenda (name, interval_minutes, enabled, last_run, next_run, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET interval_minutes=excluded.interval_minutes,
                   enabled=excluded.enabled, next_run=excluded.next_run, updated_at=excluded.updated_at""",
                (name, interval, int(active), last_run, next_run, _iso(now)))
    con.commit()
    return get_agenda(con, name=name, now=now)


def is_due(con, name=DEFAULT_NAME, now=None):
    now = now or utc_now()
    agenda = get_agenda(con, name=name, now=now)
    if not agenda['enabled']:
        return False
    next_run = _parse(agenda['next_run'])
    return next_run is None or next_run <= now


def mark_run(con, name=DEFAULT_NAME, now=None):
    """Registra a execução e calcula a próxima, preservando a agenda ativa."""
    now = now or utc_now()
    agenda = get_agenda(con, name=name, now=now)
    next_run = _iso(now + timedelta(minutes=agenda['interval_minutes'])) if agenda['enabled'] else None
    con.execute('UPDATE agenda SET last_run=?, next_run=?, updated_at=? WHERE name=?',
                (_iso(now), next_run, _iso(now), name))
    con.commit()


def acquire_lock(con, owner, name=DEFAULT_NAME, now=None):
    """Tenta obter a trava de coleta. Trava vencida (processo travado) é substituída."""
    ensure_tables(con)
    now = now or utc_now()
    row = con.execute('SELECT owner, expires_at FROM collection_lock WHERE name=?', (name,)).fetchone()
    if row and _parse(row['expires_at']) and _parse(row['expires_at']) > now and row['owner'] != owner:
        return False
    con.execute("""INSERT INTO collection_lock (name, owner, acquired_at, expires_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET owner=excluded.owner,
                   acquired_at=excluded.acquired_at, expires_at=excluded.expires_at""",
                (name, owner, _iso(now), _iso(now + timedelta(minutes=LOCK_TTL_MINUTES))))
    con.commit()
    return True


def release_lock(con, owner, name=DEFAULT_NAME):
    con.execute('DELETE FROM collection_lock WHERE name=? AND owner=?', (name, owner))
    con.commit()


def lock_state(con, name=DEFAULT_NAME, now=None):
    ensure_tables(con)
    now = now or utc_now()
    row = con.execute('SELECT owner, acquired_at, expires_at FROM collection_lock WHERE name=?', (name,)).fetchone()
    if not row or not _parse(row['expires_at']) or _parse(row['expires_at']) <= now:
        return {'running': False}
    return {'running': True, 'owner': row['owner'], 'since': row['acquired_at']}


def record_source(con, source, ok, count=0, error='', now=None):
    """Registra o resultado de uma tentativa de coleta por fonte/coletor."""
    ensure_tables(con)
    now = now or utc_now()
    error = (error or '')[:300]
    if ok:
        con.execute("""INSERT INTO source_status (source, last_attempt, last_success, last_count, last_error, failures)
                       VALUES (?, ?, ?, ?, '', 0)
                       ON CONFLICT(source) DO UPDATE SET last_attempt=excluded.last_attempt,
                       last_success=excluded.last_success, last_count=excluded.last_count,
                       last_error='', failures=0""",
                    (source, _iso(now), _iso(now), int(count)))
    else:
        con.execute("""INSERT INTO source_status (source, last_attempt, last_count, last_error, failures)
                       VALUES (?, ?, 0, ?, 1)
                       ON CONFLICT(source) DO UPDATE SET last_attempt=excluded.last_attempt,
                       last_error=excluded.last_error, failures=source_status.failures + 1""",
                    (source, _iso(now), error))
    con.commit()


def source_statuses(con):
    ensure_tables(con)
    rows = con.execute('SELECT * FROM source_status ORDER BY source').fetchall()
    return [{
        'source': r['source'],
        'last_attempt': r['last_attempt'],
        'last_success': r['last_success'],
        'last_count': r['last_count'],
        'last_error': r['last_error'],
        'failures': r['failures'],
        'status': 'ok' if r['failures'] == 0 and r['last_success'] else 'falhou',
    } for r in rows]
