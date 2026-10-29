# Setvo 2.3 — Agente de garimpo de oportunidades

## Objetivo
Encontrar problemas recorrentes com fontes verificáveis, inclusive fora dos temas configurados.

## Fontes da primeira etapa
Feeds RSS de tecnologia e setores; Reddit RSS quando acessível; Hacker News e Ask HN; issues e repositórios públicos do GitHub; arXiv; perguntas públicas Stack Exchange (Stack Overflow, Super User e Server Fault). Falhas, paginação e limites de API reduzem a cobertura. Não há acesso universal à internet.

## Regras de interpretação
- O ranking destaca **relatos/pedidos independentes**, não quantidade de manchetes.
- Dinamicamente extraímos expressões de 2-3 palavras de títulos; exige pelo menos dois sinais diretos em duas fontes diferentes. A extração é heurística, não compreensão semântica profunda.
- `score` (0-100) é uma **nota ordinal de triagem**; não é TAM, probabilidade de sucesso, arrecadação ou potencial de faturamento.
- A informação **pouca cobertura na amostra** não demonstra desatenção do mercado, falta de concorrência, nem ausência de investimento de Big Techs.
- Evidências precisam ser abertas e contextualizadas; não realizar decisões de negócio apenas com a nota.
- Perguntas técnicas, issues e feedbacks não são necessariamente intenção de compra.
- Coleta só acontece quando acionada no app; ainda não existe agente em segundo plano, pesquisa competitiva externa abrangente, embeddings/LLM, monitoramento regulatório ou validação com clientes.
- Dados de demonstração são identificados; em modo normal não aparecem.

## Próximas etapas
1. Pipeline agendado com cache/quotas/erros por fonte e atualização incremental.
2. Agrupamento semântico multilíngue, deduplicação interfontes e detecção geográfica confiável.
3. Busca sistemática de soluções concorrentes, pricing, financiamento, portfólio de Big Techs e patentes, distinguindo fatos de inferências.
4. Dossiê de oportunidade com citações, ICP, disposição para pagar e experimentos.
5. Agente conversacional com busca sob demanda e aprovação antes de ações externas.

## Rodar testes
`python -m unittest discover -s tests -v`
