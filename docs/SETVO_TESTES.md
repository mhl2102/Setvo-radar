# Evidências de teste

Comando: `python -m unittest discover -s tests -v` (o mesmo do CI).

| Data | Commit | Resultado | Observação |
|---|---|---|---|
| 2026-10-30 | `9b4f46f` (base) | 25/25 | estado original |
| 2026-10-30 | `8b89637` | 43/43 | agendamento |
| 2026-10-30 | `a1735a0` | 48/48 | API e painel |
| 2026-10-30 | `a8a00dc` | 50/50 | estado por feed RSS |
| 2026-10-30 | `cf04f36` | 58/58 | `--due` e agrupamento lexical |
| 2026-10-30 | `5c3bedc` | 60/60 | API `/api/clusters` |
| 2026-10-30 | `af17397` | 67/67 | visualização, testes de qualidade, truncamento |
| 2026-10-30 | `484d3c4` | 75/75 (+1 com modelo real opcional) | backend semântico com fallback |
| 2026-10-30 | (último commit) | 78/78 (+1 pulado) | agrupamentos no Gold Finder |

## Qualidade do agrupamento (conjunto SINTÉTICO escrito para teste)
- Lexical com truncamento (limiar 0,34): precisão 0,92, revocação 0,92 em 24 pares em português.
  Antes do truncamento: precisão 0,90, revocação 0,75. Conjunto pequeno e escrito pelo autor: ganho indicativo.
- Multilíngue, mesmo tipo de conjunto (10 pares, PT/EN):
  - lexical: revocação 0,00 (nenhum par de idiomas diferentes é encontrado);
  - semântico com limiar 0,65: precisão 1,00, revocação 1,00.
  - Limiar 0,70 reduz a revocação para 0,67 em idiomas diferentes.
- Latência do semântico: ~7 ms por texto em CPU (400 textos, batch 32).

## Limitações destes números
- Conjuntos pequenos (24 e 10 pares) escritos pelo próprio desenvolvedor: não medem generalização.
- Não há relatos reais rotulados. Antes de confiar nos limiares, é preciso rotular amostras reais.
- Os limiares foram escolhidos olhando os mesmos pares que os medem.

## Limites desta verificação
- Nenhum teste de interface no navegador.
- Nenhum teste no executável empacotado nem em Windows.
- Testes de RSS usam respostas simuladas, não feeds reais.
- Não há avaliação de precisão/revocação do agrupamento: falta um conjunto de exemplos revisados manualmente.
