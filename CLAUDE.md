# Diretrizes permanentes — Setvo

## Produto
Setvo é um aplicativo Windows (Python + pywebview + SQLite) para descobrir problemas
e oportunidades de startups a partir de fontes públicas. Não é um assistente de
automação do PC. Não inventar dados, concorrentes, consumidores ou receita.

## Regras de desenvolvimento
- Branch por funcionalidade; nunca commitar direto na `main`.
- Antes de cada commit: `python -m pyflakes *.py tests/*.py` e
  `python -m unittest discover -s tests` devem passar.
- Testes usam banco temporário (`RADAR_DB`), nunca o banco real do usuário.
- Não gravar tokens, `.env` ou bancos de usuário no repositório.
- Não criar tarefas agendadas do sistema sem consentimento explícito do usuário.
- Não fazer force push, reescrever histórico publicado ou mesclar na `main` sem verificação.
- Alterações na interface: sem scripts inline (CSP `script-src 'self'`).
- Toda POST da API exige `application/json` e origem local.

## Como retomar
Ler `docs/SETVO_RETOMADA.md`, depois `docs/SETVO_BACKLOG.md`.
