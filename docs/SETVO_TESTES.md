# Evidências de teste

Comando: `python -m unittest discover -s tests -v` (o mesmo do CI).

| Data | Commit | Resultado | Observação |
|---|---|---|---|
| 2026-10-30 | `9b4f46f` (base) | 25/25 | estado original |
| 2026-10-30 | `8b89637` | 43/43 | agendamento |
| 2026-10-30 | `a1735a0` | 48/48 | API e painel |
| 2026-10-30 | `a8a00dc` | 50/50 | estado por feed RSS |
| 2026-10-30 | `cf04f36` | 58/58 | `--due` e agrupamento lexical |

## Limites desta verificação
- Nenhum teste de interface no navegador.
- Nenhum teste no executável empacotado nem em Windows.
- Testes de RSS usam respostas simuladas, não feeds reais.
- Não há avaliação de precisão/revocação do agrupamento: falta um conjunto de exemplos revisados manualmente.
