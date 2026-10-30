# Setvo — estado atual do desenvolvimento

Atualizado em 2026-10-30 (sessão de desenvolvimento via Claude).

## Base verificada
- Branch `main` no commit `9b4f46f`, sem alterações não publicadas quando a sessão começou.
- Suíte de testes original: 25/25 aprovados (pytest e `unittest discover`, o comando do CI).
- Análise estática (pyflakes): limpa após a limpeza de imports.
- Não foi possível consultar as issues do GitHub (limite de requisições da API pública).

## Entregas desta sessão (branch `feat/agendamento-coleta`)
| Commit | Conteúdo | Testes |
|---|---|---|
| `77efc5f` | Remove 6 imports não utilizados | 25 |
| `8b89637` | `agenda.py`: agenda configurável, pausar/ativar, trava de execução, estado por coletor; `cmd_collect` isola falhas; comando `due` para o Agendador do Windows | +18 |
| `a1735a0` | API `GET/POST /api/agenda` e painel na aba "Fontes e coleta" | +5 |

Total: **48 testes aprovados**.

## Funcionalidades entregues
- Frequência da coleta automática: 1 h, 6 h, 12 h ou 24 h (intervalo validado entre 15 min e 7 dias na API).
- Ativar e pausar a coleta automática, com cálculo da próxima execução.
- Trava no banco (`collection_lock`) que impede coletas simultâneas (manual, agendada ou do painel), com expiração em 30 min para evitar travamento permanente.
- Estado de cada coletor (`source_status`): última tentativa, último sucesso, itens da última tentativa, falhas consecutivas e erro.
- Falha de um coletor não interrompe os demais.
- Deduplicação: a tabela `items` usa o identificador como chave primária, então o mesmo item não é gravado duas vezes.
- Modo demonstração: a agenda não pode ser alterada.

## Limitações conhecidas (não resolvidas)
- O estado das fontes é registrado **por coletor** (ex.: `collect_rss`), não por feed individual. Dentro de `collect_rss`, um feed que falha ainda aparece como "funcionando" com 0 itens. Corrigir exige que os coletores retornem estado por feed.
- A coleta automática só roda enquanto o processo estiver ativo ou quando o Agendador do Windows executar `radar.py due`. **Nenhuma tarefa é registrada automaticamente**, por decisão de segurança: a instalação de tarefas persistentes depende de consentimento explícito do usuário.
- Não foi validado o executável Windows nem a interface gráfica em um Windows real.
- Não foi testada a interface no navegador (apenas servidor, script e API via HTTP).
- Os 6 imports não utilizados e o restante da análise estática foram tratados, mas o CI ainda não roda pyflakes.

## Próximas funcionalidades previstas (ver Prompt Mestre)
1. Estado por feed nos coletores RSS e Reddit.
2. Agrupamento semântico multilíngue de problemas.
3. Identificação de demandas fora das palavras-chave.
4. Investigação de concorrentes e análise de lacunas.
5. Aprimoramento do Gold Finder.
6. Agente conversacional de pesquisa.
7. Dossiês de oportunidades com evidências.
8. Monitoramento de Big Techs.
