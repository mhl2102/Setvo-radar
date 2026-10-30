# Decisões arquiteturais

## D1 — Agenda dentro do SQLite existente
Tabelas `agenda`, `source_status` e `collection_lock` no mesmo banco. Motivo: volume atual
baixo e nenhuma nova dependência. Mantido conforme a orientação de não trocar a arquitetura sem justificativa.

## D2 — Trava no banco com expiração de 30 min
Evita coletas simultâneas entre painel, CLI e agendador. A expiração impede travamento
permanente se um processo morrer. Risco aceito: uma coleta que dure mais de 30 min pode ser
substituída; o intervalo é configurável em `agenda.LOCK_TTL_MINUTES`.

## D3 — Agendamento por Agendador de Tarefas do Windows, não serviço persistente
Motivo: o protocolo exige consentimento para tarefas persistentes. O app expõe `--due`,
mas não registra nada sozinho.

## D4 — Agrupamento lexical antes de semântico
Jaccard sobre termos normalizados, sem dependências. Limitação aceita e documentada:
não aproxima sinônimos nem idiomas diferentes. Embeddings multilíngues exigem avaliar
tamanho do modelo, hardware do usuário e custo; essa escolha fica pendente (P1-3).

## D5 — Estado por coletor, com RSS por feed
Só o RSS foi detalhado por feed, porque é o coletor com mais fontes independentes.
Os demais coletores continuam com estado agregado.
