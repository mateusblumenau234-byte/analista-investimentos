# Créditos e inspirações

Nenhum código destes projetos foi copiado. As ideias abaixo foram reescritas, adaptadas à B3 e testadas
aqui. Licenças segundo os próprios repositórios (MIT, salvo indicação).

| Projeto | Ideia aproveitada |
|---|---|
| [coffeefuelbump/csv-data-summarizer-claude-skill](https://github.com/coffeefuelbump/csv-data-summarizer-claude-skill) | resumo automático das tabelas, dados faltando e gráficos (`scripts/explorar_dados.py`) |
| [quant-sentiment-ai/claude-equity-research](https://github.com/quant-sentiment-ai/claude-equity-research) | tese com caso otimista e pessimista, gatilhos para mudar de opinião e catalisadores |
| [liangdabiao/claude-data-analysis](https://github.com/liangdabiao/claude-data-analysis) | etapa de checagem de qualidade dos dados antes da análise |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | rigor estatístico: propagação de incerteza por Monte Carlo e cuidado com séries temporais |
| [Thysrael/Horizon](https://github.com/Thysrael/Horizon) | radar de notícias: coleta de várias fontes, remoção de duplicadas, pontuação e briefing (`scripts/noticias.py`) |
| [flyryan/ai-news-aggregator](https://github.com/flyryan/ai-news-aggregator) (Apache-2.0) | detectar a mesma história repetida em vários veículos |
| [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) | boas práticas de construção de skills e agentes |

Segurança: o artigo da Snyk sobre riscos de SKILL.md com acesso a shell
(<https://snyk.io/pt-BR/articles/skill-md-shell-access/>) orientou a seção "Segurança" do `SKILL.md`
e a decisão de não incorporar código de terceiros.

Avaliados e não usados: Folo (leitor de RSS com licença AGPL e sem API para agentes), aibrief.fyi (site sem
RSS ou API pública), alirezarezvani/claude-skills `finance` (foco em finanças internas de empresa, como
orçamento e previsão; o código não pôde ser revisado).

Integração opcional: [Composio](https://docs.composio.dev/docs/claude-code-plugin) (plugin oficial deles para
Claude Code). A skill não instala o Composio; só usa as ferramentas dele quando o investidor já o instalou e
conectou, por exemplo o toolkit Alpha Vantage.
