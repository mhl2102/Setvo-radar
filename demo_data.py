"""Amostra FICTÍCIA para testar a interface. Nunca é misturada ao banco de produção."""
from datetime import timedelta
from radar import db, item, save, load_config, now

EXAMPLES = [
    ('Comunidade fictícia', 'Ask HN: How do small teams deal with tedious invoice reconciliation?', 'We are struggling with manual review and would love a simple tool.', 'ask', 'global', 15),
    ('Issue fictícia', 'Feature request: monitor API breaking changes automatically', 'Please add webhook alerts when SDK migrations break our integration.', 'issue', 'global', 12),
    ('Portal fictício', 'EXEMPLO: empresa apresenta agente de IA para atendimento interno', 'New agentic AI workflow to automate backoffice tasks.', 'launch', 'brasil', 0),
    ('Comunidade fictícia', 'EXEMPLO: need a reliable inventory planning tool for small wholesalers', 'We are struggling with stockouts and manual forecasting.', 'ask', 'global', 23),
    ('Issue fictícia', 'Feature request: export demand forecasting by warehouse', 'We need inventory planning based on multiple distribution centers.', 'issue', 'global', 10),
    ('Portal fictício', 'EXEMPLO: logística testa alertas de rastreabilidade de entregas', 'Freight visibility and delivery exception alerts tested in last mile.', 'news', 'brasil', 0),
    ('Comunidade fictícia', 'EXEMPLO: rastreio de transportadoras sem atualização em tempo real', 'Problema recorrente: falta de visibility de delivery exception em operação de transporte.', 'community', 'brasil', 22),
    ('Issue fictícia', 'EXEMPLO: missing support for local LLM on-prem enterprise deployments', 'Feature request: self-hosted private AI with data governance.', 'issue', 'global', 8),
    ('Portal fictício', 'EXEMPLO: empresa anuncia solução on-prem com IA privada', 'Regulated enterprise AI and local LLM used in a pilot.', 'news', 'global', 0),
    ('Comunidade fictícia', 'EXEMPLO: small teams need affordable antifraud verification', 'Too expensive to run identity verification and fraud review manually.', 'ask', 'global', 13),
    ('Portal fictício', 'EXEMPLO: deepfake e fraude provocam preocupação com KYC', 'Digital trust identity verification for fintechs.', 'news', 'brasil', 0),
    ('Issue fictícia', 'Feature request: better robot vision sensors for warehouse', 'Robot perception and industrial automation require a simpler setup.', 'issue', 'global', 3),
    ('Portal fictício', 'EXEMPLO: Nvidia expande infraestrutura para data center cooling', 'Liquid cooling and power grid infrastructure bottlenecks.', 'news', 'global', 0),
    ('Portal fictício', 'EXEMPLO: Microsoft, Google e OpenAI publicam novos recursos IA', 'AI agent platforms and copilot productivity workflows.', 'news', 'global', 0),
    ('Portal fictício', 'EXEMPLO: Amazon e Meta discutem expansão de data centers', 'Datacenter power grid energy demand and liquid cooling.', 'news', 'global', 0),
    ('Issue fictícia', 'EXEMPLO: feature request for healthcare administrative workflow', 'Hospital workflow and healthcare paperwork take too much time.', 'issue', 'global', 5),
    ('Comunidade fictícia', 'EXEMPLO: dificuldade de conciliar fluxo de caixa e recebíveis', 'Preciso de uma ferramenta para acompanhar cash flow e capital de giro.', 'ask', 'brasil', 17),
    ('Portal fictício', 'EXEMPLO: Anthropic lança modelo especializado para devtool API', 'Developer tool startup building SDK and integration platform.', 'news', 'global', 0),
    ('Portal fictício', 'EXEMPLO: Apple anuncia novos recursos de segurança', 'Cybersecurity vulnerability management and device protection.', 'news', 'global', 0),
    ('Issue fictícia', 'EXEMPLO: how to test AI tutors in personalized learning', 'Feature request for adaptive learning and student progress evaluation.', 'issue', 'global', 4),
]


def seed_demo():
    cfg = load_config()
    items = []
    for i, (source, title, desc, kind, geo, engagement) in enumerate(EXAMPLES):
        it = item(source, title, f'https://example.com/radar-demo/{i+1}', desc,
                  geo, 2, engagement, kind, now() - timedelta(days=(i*3) % 26))
        it['demo'] = 1
        items.append(it)
    with db() as con:
        return save(con, items, cfg)


if __name__ == '__main__':
    import os
    from radar import HERE
    os.environ['RADAR_DB'] = os.path.join(HERE, 'radar_demo.db')
    print(f'Inseridos {seed_demo()} exemplos fictícios.')
