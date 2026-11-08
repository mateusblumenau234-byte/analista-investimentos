---
description: "Análise completa de um ativo de qualquer bolsa, com conselho de 3 analistas, nota e relatório"
argument-hint: "TICKER [motivo: comprar | manter | vender | aportar]"
---
Analise $ARGUMENTS seguindo a skill `analise-investimentos`, **em no máximo 5 minutos** (orçamento por etapa na
seção "Tempo" da skill), com as ferramentas do servidor MCP `analista`. Chamadas independentes sempre juntas:

1. `carteira` e `resumo_do_ativo`: leia o perfil, a posição e o histórico; pergunte só o que faltar.
2. Na mesma mensagem: `analisar_ativo`, `noticias` (com `brasil=True` para ativos da B3) e `painel_mundial`.
3. Se ferramentas do Composio estiverem conectadas (MCP em connect.composio.dev), busque também as notícias
   com sentimento do Alpha Vantage e passe a resposta em `extras_composio` da ferramenta `noticias`;
   confira cotação e calendário de resultados por lá. Só ferramentas de leitura.
4. No máximo 4 buscas na web em paralelo (release do último trimestre no RI, fato relevante, consenso).
5. Conselho: rode na mesma mensagem, de forma independente, os agentes `analista-valor`, `analista-macro` e
   `analista-risco`, passando a pasta da análise. Cada um grava `parecer_<id>.json`.
6. `nota_final`, redação do relatório, `relatorio_html`, e `registrar_analise` depois que o investidor ler.
7. Ofereça alertas úteis (`criar_alerta`) ligados aos gatilhos que os analistas apontaram.

Não é recomendação de investimento; diga isso no fim.
