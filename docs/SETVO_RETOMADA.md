# Ponto de retomada

## Verificar antes de qualquer coisa
```bash
git checkout feat/agendamento-coleta
python -m pyflakes *.py tests/*.py
python -m unittest discover -s tests -v   # esperado: 58 OK
```

## Próxima ação exata
Integrar o agrupamento ao painel (P1-2):
1. Em `dashboard.py`, adicionar `GET /api/clusters?days=30` que carrega os itens do
   período com `_rows(...)` e devolve `clusters.cluster_items(...)`, limitado a 50 grupos.
2. Teste HTTP em `tests/test_clusters.py` cobrindo: resposta 200, formato, período vazio.
3. Na aba Oportunidades, mostrar os grupos com "N fontes independentes" e rótulo de termos.

## Depois
P1-4 (demandas fora das palavras-chave) e P1-5 (Gold Finder com pesos configuráveis).

## Bloqueios
- Sem acesso de escrita ao GitHub: push e pull request não feitos.
- Sem Windows: validação do `.exe` e do instalador pendentes (P0-7, P0-8).
- Rotinas recorrentes de desenvolvimento não foram criadas: o protocolo exige autorização explícita.
