import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import agenda
import radar

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def at(minutes):
    return T0 + timedelta(minutes=minutes)


class AgendaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = os.environ.get('RADAR_DB')
        os.environ['RADAR_DB'] = os.path.join(self.temp.name, 'agenda.db')
        self.con = radar.db()

    def tearDown(self):
        self.con.close()
        if self.old_db is None:
            os.environ.pop('RADAR_DB', None)
        else:
            os.environ['RADAR_DB'] = self.old_db
        self.temp.cleanup()

    # ---------- validação
    def test_intervalo_aceita_limites_e_rejeita_fora_deles(self):
        self.assertEqual(agenda.validate_interval(15), 15)
        self.assertEqual(agenda.validate_interval('60'), 60)
        for bad in (14, 0, -5, 10 ** 6, 'abc', None, True, 12.5):
            with self.subTest(valor=bad), self.assertRaises(ValueError):
                agenda.validate_interval(bad)

    # ---------- configuração
    def test_agenda_padrao_comeca_pausada(self):
        a = agenda.get_agenda(self.con, now=T0)
        self.assertFalse(a['enabled'])
        self.assertIsNone(a['next_run'])
        self.assertFalse(agenda.is_due(self.con, now=at(10 ** 4)))

    def test_ativar_agenda_torna_coleta_imediatamente_vencida(self):
        a = agenda.set_agenda(self.con, interval_minutes=60, enabled=True, now=T0)
        self.assertTrue(a['enabled'])
        self.assertEqual(a['next_run'], T0.isoformat())
        self.assertTrue(agenda.is_due(self.con, now=T0))

    def test_pausar_limpa_proxima_execucao_e_impede_coleta(self):
        agenda.set_agenda(self.con, interval_minutes=60, enabled=True, now=T0)
        a = agenda.set_agenda(self.con, enabled=False, now=at(5))
        self.assertIsNone(a['next_run'])
        self.assertFalse(agenda.is_due(self.con, now=at(10000)))

    def test_reativar_apos_pausa_executa_na_proxima_verificacao(self):
        agenda.set_agenda(self.con, interval_minutes=60, enabled=True, now=T0)
        agenda.set_agenda(self.con, enabled=False, now=at(5))
        a = agenda.set_agenda(self.con, enabled=True, now=at(500))
        self.assertEqual(a['next_run'], at(500).isoformat())

    def test_alterar_intervalo_recalcula_a_partir_da_ultima_execucao(self):
        agenda.set_agenda(self.con, interval_minutes=60, enabled=True, now=T0)
        agenda.mark_run(self.con, now=T0)
        a = agenda.set_agenda(self.con, interval_minutes=120, now=at(10))
        self.assertEqual(a['next_run'], at(120).isoformat())

    def test_vencimento_respeita_intervalo(self):
        agenda.set_agenda(self.con, interval_minutes=60, enabled=True, now=T0)
        agenda.mark_run(self.con, now=T0)
        self.assertFalse(agenda.is_due(self.con, now=at(59)))
        self.assertTrue(agenda.is_due(self.con, now=at(60)))

    def test_mark_run_avanca_proxima_execucao(self):
        agenda.set_agenda(self.con, interval_minutes=30, enabled=True, now=T0)
        agenda.mark_run(self.con, now=at(40))
        a = agenda.get_agenda(self.con, now=at(40))
        self.assertEqual(a['last_run'], at(40).isoformat())
        self.assertEqual(a['next_run'], at(70).isoformat())

    # ---------- trava de execução
    def test_trava_impede_segunda_coleta_simultanea(self):
        self.assertTrue(agenda.acquire_lock(self.con, 'a', now=T0))
        self.assertFalse(agenda.acquire_lock(self.con, 'b', now=at(1)))
        self.assertTrue(agenda.lock_state(self.con, now=at(1))['running'])

    def test_trava_expirada_pode_ser_substituida(self):
        agenda.acquire_lock(self.con, 'travado', now=T0)
        later = at(agenda.LOCK_TTL_MINUTES + 1)
        self.assertTrue(agenda.acquire_lock(self.con, 'novo', now=later))
        self.assertEqual(agenda.lock_state(self.con, now=later)['owner'], 'novo')

    def test_liberar_trava_so_pelo_dono(self):
        agenda.acquire_lock(self.con, 'a', now=T0)
        agenda.release_lock(self.con, 'outro')
        self.assertTrue(agenda.lock_state(self.con, now=at(1))['running'])
        agenda.release_lock(self.con, 'a')
        self.assertFalse(agenda.lock_state(self.con, now=at(1))['running'])

    # ---------- estado das fontes
    def test_estado_da_fonte_registra_sucesso_e_falhas_consecutivas(self):
        agenda.record_source(self.con, 'collect_rss', ok=True, count=12, now=T0)
        agenda.record_source(self.con, 'collect_rss', ok=False, error='timeout', now=at(1))
        agenda.record_source(self.con, 'collect_rss', ok=False, error='timeout', now=at(2))
        st = {s['source']: s for s in agenda.source_statuses(self.con)}['collect_rss']
        self.assertEqual(st['failures'], 2)
        self.assertEqual(st['status'], 'falhou')
        self.assertEqual(st['last_success'], T0.isoformat())
        self.assertEqual(st['last_error'], 'timeout')
        agenda.record_source(self.con, 'collect_rss', ok=True, count=3, now=at(3))
        st = {s['source']: s for s in agenda.source_statuses(self.con)}['collect_rss']
        self.assertEqual((st['failures'], st['status'], st['last_error']), (0, 'ok', ''))

    def test_mensagem_de_erro_e_truncada(self):
        agenda.record_source(self.con, 'x', ok=False, error='e' * 1000, now=T0)
        st = agenda.source_statuses(self.con)[0]
        self.assertLessEqual(len(st['last_error']), 300)


class CollectionCycleTests(unittest.TestCase):
    """Garante que o ciclo de coleta isola falhas e respeita a trava."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = os.environ.get('RADAR_DB')
        os.environ['RADAR_DB'] = os.path.join(self.temp.name, 'ciclo.db')
        self.cfg = radar.load_config()

    def tearDown(self):
        if self.old_db is None:
            os.environ.pop('RADAR_DB', None)
        else:
            os.environ['RADAR_DB'] = self.old_db
        self.temp.cleanup()

    @staticmethod
    def _item(i):
        return radar.item('Fonte Teste', f'Título {i}', f'https://exemplo.test/{i}', 'texto',
                          'global', 1, 0, 'news', None)

    def test_falha_de_um_coletor_nao_interrompe_os_demais(self):
        def ok_collector(cfg):
            return [self._item(1), self._item(2)]

        def broken_collector(cfg):
            raise RuntimeError('fonte fora do ar')

        def ok_other(cfg):
            return [self._item(3)]

        ok_collector.__name__ = 'coletor_ok'
        broken_collector.__name__ = 'coletor_quebrado'
        ok_other.__name__ = 'outro_ok'
        with patch.object(radar, 'COLLECTORS', (ok_collector, broken_collector, ok_other)):
            self.assertTrue(radar.cmd_collect(self.cfg))

        con = radar.db()
        statuses = {s['source']: s for s in agenda.source_statuses(con)}
        self.assertEqual(statuses['coletor_ok']['status'], 'ok')
        self.assertEqual(statuses['outro_ok']['status'], 'ok')
        self.assertEqual(statuses['coletor_quebrado']['status'], 'falhou')
        self.assertIn('fonte fora do ar', statuses['coletor_quebrado']['last_error'])
        self.assertEqual(con.execute('SELECT COUNT(*) FROM items').fetchone()[0], 3)
        run = con.execute('SELECT status, details FROM collection_runs ORDER BY id DESC').fetchone()
        self.assertEqual(run['status'], 'concluido com falhas')
        con.close()

    def test_coleta_nao_roda_quando_outra_esta_em_andamento(self):
        con = radar.db()
        agenda.acquire_lock(con, 'outro-processo')
        con.close()
        called = []

        def collector(cfg):
            called.append(True)
            return []

        collector.__name__ = 'coletor_espiao'
        with patch.object(radar, 'COLLECTORS', (collector,)):
            self.assertFalse(radar.cmd_collect(self.cfg))
        self.assertEqual(called, [])

    def test_trava_e_liberada_apos_a_coleta(self):
        def collector(cfg):
            return []

        collector.__name__ = 'vazio'
        with patch.object(radar, 'COLLECTORS', (collector,)):
            radar.cmd_collect(self.cfg)
        con = radar.db()
        self.assertFalse(agenda.lock_state(con)['running'])
        con.close()

    def test_trava_e_liberada_mesmo_quando_gravacao_falha(self):
        def collector(cfg):
            return [self._item(1)]

        collector.__name__ = 'grava'
        with patch.object(radar, 'COLLECTORS', (collector,)), \
                patch.object(radar, 'save', side_effect=sqlite_error()):
            # Erro de gravação é tratado como falha daquele coletor; o ciclo termina e libera a trava.
            self.assertTrue(radar.cmd_collect(self.cfg))
        con = radar.db()
        self.assertFalse(agenda.lock_state(con)['running'])
        st = {s['source']: s for s in agenda.source_statuses(con)}['grava']
        self.assertEqual(st['status'], 'falhou')
        self.assertIn('disco cheio', st['last_error'])
        con.close()

    def test_cmd_due_so_coleta_quando_vencida(self):
        con = radar.db()
        agenda.set_agenda(con, interval_minutes=60, enabled=False)
        con.close()
        called = []

        def collector(cfg):
            called.append(True)
            return []

        collector.__name__ = 'vencido'
        with patch.object(radar, 'COLLECTORS', (collector,)):
            self.assertFalse(radar.cmd_due(self.cfg))
        self.assertEqual(called, [])


def sqlite_error():
    import sqlite3
    return sqlite3.OperationalError('disco cheio (simulado)')


if __name__ == '__main__':
    unittest.main()
