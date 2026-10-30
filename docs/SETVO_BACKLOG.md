# Backlog — Setvo

Legenda de estado: ✅ concluído e testado · 🟡 parcial · ⬜ pendente · 🚫 bloqueado

## P0 — bloqueadores
| ID | Tarefa | Estado | Evidência |
|---|---|---|---|
| P0-1 | Limpeza de imports não utilizados | ✅ | `77efc5f`; pyflakes limpo |
| P0-2 | Agendamento: configuração, pausa, vencimento | ✅ | `8b89637`; `tests/test_agenda.py` |
| P0-3 | Trava de execução com expiração | ✅ | testes de trava |
| P0-4 | Isolamento de falhas por coletor | ✅ | `test_falha_de_um_coletor...` |
| P0-5 | API e painel da agenda | ✅ API testada; 🟡 UI não testada em navegador | `a1735a0` |
| P0-6 | Estado individual por feed RSS | ✅ | `a8a00dc`; teste de integração |
| P0-7 | Executável com `--due` para o Agendador do Windows | 🟡 código e teste prontos; **não validado no .exe real** | `cf04f36` |
| P0-8 | Build e instalador Windows validados | 🚫 precisa de Windows | — |
| P0-9 | Reconciliação do estado dos commits no GitHub | 🚫 sem acesso de escrita | — |

## P1 — núcleo de inteligência
| ID | Tarefa | Estado |
|---|---|---|
| P1-1 | Agrupamento lexical de publicações | ✅ módulo e testes (`clusters.py`) |
| P1-2 | Integrar agrupamento ao painel (aba Oportunidades) | ⬜ |
| P1-3 | Agrupamento semântico multilíngue (embeddings) | ⬜ depende de decisão de dependência (ver DECISOES) |
| P1-4 | Detecção de demandas fora das palavras-chave | ⬜ |
| P1-5 | Gold Finder: pontuação com pesos configuráveis e separação de eixos | ⬜ |
| P1-6 | Investigação de concorrentes com evidências | ⬜ |
| P1-7 | Análise de lacunas de mercado | ⬜ |

## P2 — agente
| ID | Tarefa | Estado |
|---|---|---|
| P2-1 | Pesquisa conversacional com limites de custo e ferramentas | ⬜ |
| P2-2 | Dossiê de oportunidade com evidências rastreáveis | ⬜ |
| P2-3 | Monitoramento recorrente de Big Techs | ⬜ |

## P3 — experiência
| ID | Tarefa | Estado |
|---|---|---|
| P3-1 | Teste de interface no navegador (Playwright) | ⬜ |
| P3-2 | Revisão visual da aba Fontes | ⬜ |
