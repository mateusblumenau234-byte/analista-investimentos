---
description: Mostra e atualiza a carteira (posições, compras, vendas) e o desempenho
argument-hint: [ex.: comprei 100 PETR4 a 38,50]
---
Use as ferramentas do servidor MCP `analista`.
- Sem argumentos: chame `carteira`, cote as posições com `cotacao` e mostre posições, resultado sobre o
  preço médio, alocação por classe contra o alvo do perfil, alertas ativos e o que está desatualizado.
- Com uma operação em $ARGUMENTS: confirme ativo, quantidade e preço com o investidor e só então chame
  `registrar_operacao` (venda = cotas negativas) ou `registrar_posicao`. Depois gere o `painel`.
Nunca invente quantidades ou preços.
