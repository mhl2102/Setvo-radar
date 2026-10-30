# Ponto de retomada

API de agrupamentos pronta. Próximo: interface (passo 3 abaixo).

## Verificar antes de qualquer coisa
```bash
git checkout feat/agendamento-coleta
python -m pyflakes *.py tests/*.py
python -m unittest discover -s tests -v   # esperado: 60 OK
```

## Próxima ação exata
Integrar o agrupamento ao painel (P1-2):
1. ✅ `GET /api/clusters?days=30` em `dashboard.py`, com testes HTTP em `tests/test_clusters.py`.
2. ⬜ Na aba Oportunidades (`web/index.html`, `web/app.js`), mostrar cada grupo com "N fontes independentes", os termos do rótulo e os links de evidência. Sem script inline.
3. ⬜ Conferir visualmente no navegador (ou registrar que não foi possível).

## Depois
P1-4 (demandas fora das palavras-chave) e P1-5 (Gold Finder com pesos configuráveis).

## Bloqueios
- Sem acesso de escrita ao GitHub: push e pull request não feitos.
- Sem Windows: validação do `.exe` e do instalador pendentes (P0-7, P0-8).
- Rotinas recorrentes de desenvolvimento não foram criadas: o protocolo exige autorização explícita.
