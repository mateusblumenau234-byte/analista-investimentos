---
description: Análise completa de um ativo de qualquer bolsa, com conselho de 3 analistas, nota e relatório
argument-hint: TICKER [motivo: comprar | manter | vender | aportar]
---
Analise $ARGUMENTS seguindo a skill `analise-investimentos` do começo ao fim, usando as ferramentas do
servidor MCP `analista` sempre que existirem para a etapa:

1. `carteira` e `resumo_do_ativo`: leia o perfil, a posição e o histórico; pergunte só o que faltar.
2. `analisar_ativo` (coleta quantitativa e exploração), `painel_mundial`, `serie_bcb`/`focus` quando o ativo
   for da B3, e `noticias` com `brasil=True` para ativos da B3.
3. Se ferramentas do Composio estiverem conectadas (MCP em connect.composio.dev), busque também as notícias
   com sentimento do Alpha Vantage e passe a resposta em `extras_composio` da ferramenta `noticias`;
   confira cotação e calendário de resultados por lá. Só ferramentas de leitura.
4. Pesquisa qualitativa na web (RI, regulador, release oficial), como manda a skill.
5. Conselho: rode em paralelo e de forma independente os agentes `analista-valor`, `analista-macro` e
   `analista-risco`, passando a pasta da análise. Cada um grava `parecer_<id>.json`.
6. `nota_final`, redação do relatório, `relatorio_html`, e `registrar_analise` depois que o investidor ler.
7. Ofereça alertas úteis (`criar_alerta`) ligados aos gatilhos que os analistas apontaram.

Não é recomendação de investimento; diga isso no fim.
