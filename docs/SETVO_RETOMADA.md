# Setvo — ponto de retomada

## Onde está
Branch de trabalho: `feat/agendamento-coleta` (a partir de `main`, incluindo o commit de limpeza de imports `77efc5f`).
Último commit: `a1735a0`. Suíte: 48/48 aprovados.

## Como verificar o estado
```bash
git checkout feat/agendamento-coleta
python -m pyflakes *.py tests/*.py
python -m unittest discover -s tests -v
```

## Próxima ação exata
Implementar **estado por feed** nos coletores RSS (`collect_rss` em `radar.py`):
1. Fazer `collect_rss` retornar também o status de cada feed (sucesso/erro, contagem, mensagem).
2. Gravar cada feed com `agenda.record_source(con, f"rss:{nome}", ...)`.
3. Adicionar um teste em `tests/test_agenda.py` que simule um feed com erro e outro com sucesso, e verifique os dois registros.

## Pendências antes de publicar
- Abrir pull request de `feat/agendamento-coleta` para `main` (não foi feito: não há autorização de escrita no GitHub nesta sessão).
- Registrar a tarefa do Agendador do Windows apenas com consentimento do usuário.
- Validar o executável e o instalador em um Windows real.
