---
description: "Abre o app Analista (homebroker com conversa) dentro do Claude"
---
Leia `~/.analise-investimentos/app.json`. Se tiver `url`, abra com a ferramenta Artifact (`action: "open"`).
Se não tiver, publique `servidor/app/analista.html` deste plugin como Artifact com as capacidades
`sample` e `mcp` (servidor `host:plugin_analise-investimentos_analista`, ferramentas carteira, cotacoes_rapidas,
historico, noticias, analise_ao_vivo, analisar_ativo, mundo, focus), grave o link em `app.json` e abra.
Responda com uma linha dizendo que o app está aberto ao lado.
