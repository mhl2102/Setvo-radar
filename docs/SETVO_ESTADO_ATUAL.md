# Estado atual — Setvo

Atualizado a cada sessão. Branch de trabalho: `feat/agendamento-coleta`.
Base: `main` em `9b4f46f`. Último commit: `cf04f36`. Suíte: 58/58.

## Funcionando e testado (ambiente Linux)
- Agendamento: frequência, ativar/pausar, vencimento, trava com expiração.
- Estado por coletor e por feed RSS; falhas isoladas.
- API `GET/POST /api/agenda` e painel na aba Fontes (verificado por HTTP, não no navegador).
- Comando `--due` no executável e na linha de comando (`radar.py due`).
- Agrupamento lexical (`clusters.py`), ainda não exibido no painel.

## Não verificado
- Executável Windows e instalador: não foram gerados nem testados nesta sessão.
- Interface no navegador: não testada.
- Qualidade do agrupamento: sem conjunto de referência.

## Não publicado
Todos os commits estão locais. Não há acesso de escrita ao GitHub nesta sessão.
Patches exportados em `/mnt/user-data/outputs/setvo-patches/`.
