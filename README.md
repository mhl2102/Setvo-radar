# RADAR — Startup Intelligence · V2.0

Ferramenta local para **monitorar tendências de tecnologia, startups e Big Techs e transformar sinais públicos em hipóteses de novos negócios**. Evolução do `radar.zip` original: preserva a coleta Python/SQLite, acrescenta identificação heurística de pedidos/dificuldades, temas de oportunidade configuráveis, dashboard, anotações, exportação e monitoramento temporal.

> **Regra central:** uma notícia, uma opinião ou um pedido em fórum **não comprova demanda pagante**. O radar sugere **hipóteses de mercado** para pesquisa humana, sem inventar consumidores, tamanho de mercado ou receita potencial.

## Início rápido (Windows)

1. Extraia todo o ZIP em uma pasta do computador. **Atalho:** com Python instalado, também pode abrir `iniciar_windows.bat` (e `experimentar_demo.bat` para dados fictícios).
2. Abra o PowerShell na pasta `radar`.
3. Instale as dependências (Python 3.10+):

   ```powershell
   py -m pip install -r requirements.txt
   ```

4. Inicie o painel:

   ```powershell
   py dashboard.py
   ```

5. Acesse no navegador: **http://127.0.0.1:8765** e clique em **Atualizar radar**. A coleta consulta fontes externas em tempo real. Pode durar alguns minutos; fontes bloqueadas/indisponíveis são puladas.

Para **experimentar a interface antes de coletar**, use:

```powershell
py dashboard.py --demo
```

Esse comando usa apenas o arquivo `radar_demo.db`, criado com exemplos FICTÍCIOS, visualmente identificados no painel. **O modo de demonstração é isolado do banco real.** Feche com `Ctrl+C` e execute `py dashboard.py` para iniciar a versão real. Se já estiver usando a porta 8765, encerre o processo anterior ou selecione `--port 8770`.

No Linux/macOS, substitua `py` por `python3`.

## O que foi entregue

| Módulo | Função |
|---|---|
| Visão geral | KPIs, setores, hipóteses prioritárias, publicações recentes |
| Explorar sinais | Busca, setor, país/território, tipo de evidência, ranking, paginação |
| Oportunidades | 12 teses configuráveis: problema, potencial cliente, MVP, validação, monetização, evidências |
| Tendências | Volume de publicações dos últimos 7 dias x 7 dias anteriores, com aviso sobre histórico insuficiente |
| Big Techs | Menções a empresas relevantes com acesso aos registros originais |
| Minha pesquisa | Salvar estágio (observando/pesquisando/validando) e notas de entrevistas no SQLite |
| Fontes e coleta | Consultar origem, últimas execuções e log do processo |
| Exportação | CSV (Excel/Power BI) e JSON, respeitando filtros de busca |
| Motor de coleta | RSS, comunidades Reddit (quando público), Hacker News, Ask HN, GitHub, GitHub Issues, arXiv |

O **score de oportunidade (0–100)** é exclusivamente uma **heurística de priorização**, combinando volume de publicações, presença de relatos/pedidos, diversidade de fontes e engajamento. Não representa probabilidade de sucesso, TAM, mercado em reais nem chance de investimento.

`Dor relatada` / `Pedido`: candidatos extraídos de comunidades, Ask HN e GitHub Issues. `Dor citada em notícia`: notícia menciona um problema, **não é relato direto de comprador**. `Apenas tendência`: sem sinais diretos identificados. A classificação por palavras-chave pode errar e deve ser verificada no link original.

## Comandos adicionais

```bash
python radar.py collect           # coleta e salva fontes públicas
python radar.py digest            # gera boletim dos itens ainda não marcados como enviados
python radar.py run               # coleta e digest
python radar.py loop --every 30   # loop CLI (repetição a cada N minutos)
python radar.py demo              # gera banco de demonstração separado
python dashboard.py --port 8770   # porta diferente
python -m unittest discover -s tests -v
```

### Uso contínuo

Para execução automática sem manter o painel aberto, agende `python radar.py collect` no Agendador de Tarefas do Windows, ou use cron. As coletas alimentam o mesmo SQLite que o dashboard consulta. Recomenda-se começar com **uma coleta a cada 4–6 horas** (respeite limites de API). O dashboard pode permanecer fechado enquanto o agendamento opera.

## Personalização

No `config.yaml`:

- `feeds`: RSS públicos Brasil + global, com pesos de origem;
- `sectors`: categorias e palavras-chave;
- `themes`: tópicos de oportunidade, público, problema, MVP, hipótese de monetização e forma de validação;
- `ask_hn` e `github_issues`: ativação, limites e consultas;
- `digest`: critérios da síntese tradicional.

As informações de temas (`themes`) são **sugestões de modelagem de negócio**, e não observações comprovadas pelas fontes. Um tema somente aparece como oportunidade quando existem publicações compatíveis no banco.

Copie `.env.example` para `.env` para configurar opcionalmente:

- `GITHUB_TOKEN` para ampliar os limites da API do GitHub (não é necessário para início).
- `ANTHROPIC_API_KEY` e `RADAR_MODEL` para síntese opcional do **boletim CLI**. O dashboard e as hipóteses funcionam **sem IA paga**.
- `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` para receber o boletim no Telegram.
- `RADAR_DB` para indicar outro caminho de banco SQLite.

Não publique o arquivo `.env` nem tokens. Por padrão o servidor é **local** (`127.0.0.1`) e não requer cadastro. Não use `--host 0.0.0.0` em redes não confiáveis: o servidor não implementa autenticação e as notas seriam expostas a outras pessoas da rede.

## Limitações / próximos incrementos

1. **Demanda e viabilidade:** os posts não fornecem base estatística representativa. Próximo módulo: entrevistas estruturadas, validação de problema, disposição a pagar, concorrentes, TAM/SAM/SOM e experimentos de MVP.
2. **Clustering semântico:** atualmente o agrupamento funciona por termos e pode perder sinônimos ou trazer falsos positivos. Futuro: classificação semântica/embeddings e revisões humanas.
3. **Detecção de aceleração:** o painel descreve volume em janelas de 7 dias. Um sinal confiável exige coleta consistente durante pelo menos 14 dias (idealmente meses), ajuste por volume de fonte e análise de duplicações.
4. **Cobertura de fontes:** Reddit frequentemente bloqueia RSS; redes sociais e alguns portais têm limites, termos e requisitos de licença. É preferível integrar APIs oficiais ou feeds consentidos.
5. **Competidores, receita e tamanho de mercado:** essas métricas não são preenchidas automaticamente nem inventadas; podem ser adicionadas com fontes específicas e verificação de proveniência.
6. **Segurança/produção:** aplicação projetada para uso local individual; para implantação online, adicionar autenticação, gestão de contas, HTTPS, rate limiting, proteção CSRF, banco hospedado e revisão de conformidade.
7. **Tradução internacional:** títulos e textos originais são preservados. A síntese do digest pode ser em português quando a opção LLM é configurada; a tradução do painel não está automatizada nesta versão.

## Estrutura

```text
radar/
  radar.py          # coletores e boletim
  insights.py       # sinais, entidades e hipóteses
  dashboard.py      # servidor local e APIs
  rss_compat.py     # fallback sem feedparser
  demo_data.py      # exemplos explicitamente fictícios
  config.yaml       # setores, hipóteses e fontes
  web/
    index.html      # interface
    app.css
    app.js
  tests/            # testes locais
  requirements.txt
  .env.example
```

Fontes e referências para a evolução do projeto: [HN Algolia API](https://hn.algolia.com/api), [GitHub REST Search](https://docs.github.com/en/rest/search/search), [Y Combinator — Requests for Startups](https://www.ycombinator.com/rfs). YC publica teses de investimento/inspiração, **não uma confirmação de que compradores pagarão pela solução**.
