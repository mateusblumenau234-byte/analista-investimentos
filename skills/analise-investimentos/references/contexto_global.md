# Contexto mundial, expectativas, rumores e Brasil

Nenhuma ação vive isolada. Antes de concluir, o analista responde: **o que está movendo o mundo agora,
o que o mercado já espera e o que ainda pode surpreender?** Toda informação recebe um rótulo:

| Rótulo | Significado | Exemplo |
|---|---|---|
| **FATO** | confirmado em fonte primária ou oficial | decisão do banco central publicada, fato relevante, lei sancionada |
| **EXPECTATIVA** | o que o mercado projeta, com fonte e data | consenso de lucro, Focus, probabilidade de corte de juros nos futuros |
| **RUMOR** | relato não confirmado, sempre com nível de credibilidade (abaixo) | "fontes dizem que a empresa negocia uma aquisição" |
| **VERSÃO** | afirmação de parte interessada (governo, oposição, empresa, sindicato) | declaração de ministro, nota de partido, release otimista |
| **DESINFORMAÇÃO** | afirmação desmentida por fonte primária ou agência de checagem | número falso sobre a economia circulando em rede social |

## 1. Painel mundial (automático em `analisar.py`, seção 7b)
Bolsas (EUA, Europa, Japão, Hong Kong, China, Índia, Brasil, emergentes), Treasury de 10 anos e 3 meses,
dólar (DXY e moedas principais), VIX, petróleo, ouro, cobre, soja e bitcoin, com variação em 1, 3 e 12 meses.
Para cada movimento forte, explicar a causa com notícias datadas.

## 2. Perguntas que o relatório responde sobre o mundo
1. **Juros globais**: o Fed, o BCE, o Banco do Japão e o banco central local estão cortando, parados ou subindo?
   O que os futuros de juros embutem (CME FedWatch para o Fed; Focus e curva DI para o Brasil)?
2. **Crescimento**: EUA, China e Europa acelerando ou desacelerando (PMIs, PIB, emprego)? Há risco de recessão?
3. **Inflação**: cedendo ou voltando? Isso muda o caminho dos juros?
4. **Dólar e fluxos**: dólar forte tira dinheiro de emergentes; dólar fraco devolve. Como estão os fluxos
   estrangeiros para a bolsa do país do ativo?
5. **Commodities**: petróleo, minério, cobre, grãos. Quem ganha e quem perde com o movimento atual?
6. **Geopolítica e comércio**: guerras, sanções, tarifas, eleições importantes, tensão EUA e China.
7. **Apetite a risco**: VIX, spreads de crédito, valuation da bolsa americana (CAPE de Shiller).
8. **Canal de transmissão até a empresa**: por qual caminho cada fator chega na receita, no custo, na dívida
   ou no custo de capital desta empresa. Diferenciar correlação de causa.

## 3. Expectativas do mercado (o que o preço já embute)
- Consenso de analistas: lucro e receita esperados, recomendações e preço-alvo médio, com data.
- Guidance da própria empresa e histórico de entregar ou não o que promete.
- Juros e inflação esperados: Focus (Brasil), FedWatch e Treasuries (EUA), curva de juros local.
- Volatilidade implícita de opções quando disponível (o mercado espera movimento grande?).
- **Reverse DCF** (`valuation.premissas_implicitas_no_preco`): qual crescimento o preço atual exige.
Regra: o que já é esperado já está no preço. Só a **diferença** entre o que vai acontecer e o que se
espera move a cotação. O relatório diz onde o analista diverge do consenso e por quê.

## 4. Rumores: considerar sempre, classificar sempre
Rumores mexem com preços mesmo quando são falsos. Por isso nunca são ignorados, mas também nunca são
tratados como fato. Cada rumor relevante recebe um nível:

| Nível | Critério | Como entra no relatório |
|---|---|---|
| **REAL** | confirmado oficialmente (fato relevante, comunicado, regulador) | passa a ser FATO |
| **PODE ACONTECER: provável** | agência ou jornal de referência com fontes próprias, e/ou vários veículos independentes, sem desmentido | cenário com impacto estimado; catalisador ou risco |
| **PODE ACONTECER: possível** | uma fonte razoável, sem confirmação nem desmentido | cenário alternativo, peso menor |
| **CHANCE QUASE NULA: improvável** | fonte fraca, sem eco, contradiz fatos conhecidos ou é economicamente implausível | citado só se mexeu no preço |
| **CHANCE QUASE NULA: desmentido** | negado pelos envolvidos ou por autoridade, ou checado como falso | citado só se mexeu no preço; alerta de reversão |

Para cada rumor relevante, registrar:
1. Origem (quem publicou primeiro), data e se outros veículos confirmaram com apuração própria.
2. Se houve confirmação ou desmentido oficial.
3. **Reação do mercado**: variação do preço e do volume no dia e nos dias seguintes. Um rumor de chance quase
   nula que derrubou a ação 8% é uma oportunidade ou um risco de volatilidade, e precisa aparecer.
4. O que muda na tese se virar verdade (efeito no valor por ação, quando der para estimar).
`noticias.py` faz uma classificação inicial automática; o analista lê as matérias e dá a palavra final.
"Chance zero" não existe em mercado: usar "chance quase nula" e explicar o motivo.

## 5. Brasil: protocolo reforçado
O Brasil exige mais cuidado que mercados maduros: polarização política forte, volume alto de desinformação,
peso do Estado na economia (estatais, bancos públicos, crédito direcionado) e histórico de mudanças de
regra. O analista **não toma partido**. Avalia somente o efeito econômico e de mercado, com o mesmo rigor
para qualquer governo, partido ou candidato.

### 5.1 O que acompanhar
- **Presidência e ministérios**: decisões e propostas com efeito em gastos, impostos, estatais, preços
  administrados (combustíveis, energia), crédito público e regulação. Separar o que foi **assinado ou
  publicado** do que foi apenas **declarado**.
- **Fiscal**: cumprimento do arcabouço e da meta de resultado primário, trajetória da dívida bruta
  (Tesouro, BCB), relatórios da IFI (Senado), Lei Orçamentária, contingenciamentos.
- **Congresso**: o que foi votado, em que fase está cada proposta (comissão, plenário, sanção), chance real
  de aprovação (tamanho da base, calendário, histórico). Proposta apresentada não é lei.
- **STF e tribunais**: decisões com efeito tributário, trabalhista ou regulatório para a empresa ou o setor.
- **Banco Central**: decisões e atas do Copom, comunicação sobre inflação e expectativas (Focus).
- **Eleições**: em ano eleitoral e no ano anterior, pesquisas registradas no TSE de institutos diferentes,
  propostas econômicas oficiais registradas pelos candidatos e reação do mercado (juros futuros, dólar,
  CDS, bolsa). Pesquisa é retrato, não previsão.
- **Estatais e setores regulados**: mudanças de diretoria, política de preços e dividendos, agências
  reguladoras (ANEEL, ANP, ANATEL, ANS, ANVISA).
- **Termômetros do mercado**: curva de juros futuros (DI), dólar, CDS de 5 anos, fluxo estrangeiro na B3.

### 5.2 Como separar o que é verdade
1. **Fonte primária primeiro**: Diário Oficial da União, Planalto, sites da Câmara e do Senado (tramitação),
   STF, TSE, Tesouro Nacional, Banco Central, IBGE, IFI, CVM e o RI da empresa.
2. **Agências de checagem** para afirmações que circulam: Agência Lupa, Aos Fatos, Estadão Verifica,
   Fato ou Fake (g1), Projeto Comprova.
3. **Veículos de linhas editoriais diferentes**: ler pelo menos dois com perfis distintos sobre o mesmo
   tema político. Se só um lado noticia, tratar como VERSÃO até haver confirmação.
4. **Desconfiar de**: prints, vídeos cortados, números sem fonte, "fontes do governo" ou "fontes da
   oposição" sem documento, conteúdo que só circula em redes sociais ou aplicativos de mensagem.
5. **Declaração não é decisão**: fala de autoridade entra como VERSÃO; vira FATO quando publicada,
   votada ou executada.
6. **Medir pelo mercado**: se uma notícia política fosse relevante e verdadeira, juros futuros, dólar e CDS
   reagiriam. Reação nula sugere que o mercado não deu crédito ou já esperava.

### 5.3 Como entra no relatório
- Seção de riscos: risco político e fiscal com probabilidade qualitativa (baixa, média, alta), impacto
  e horizonte, citando fontes de linhas diferentes.
- Cenários: o que acontece com a empresa em um cenário fiscal pior e em um melhor (juros, câmbio,
  demanda, regulação), com números do motor (`valuation.dcf_fcff(p, sobrescrever={...})`).
- Linguagem neutra: sem adjetivos sobre pessoas ou partidos; descrever medidas e efeitos.
- Nunca recomendar voto nem associar a análise a preferência política.

## 6. Outros países
Cada mercado tem a sua versão do item 5: banco central, política fiscal, eleições e regulação. Para
ações fora do Brasil e dos EUA, pesquisar: banco central local e expectativas de juros, título de 10
anos (Rf), inflação, câmbio contra o dólar, risco-país (Damodaran) e regras para investidores estrangeiros.

## 7. Fontes mundiais (WebSearch e WebFetch)
| Tema | Fontes |
|---|---|
| Notícias e mercados | Reuters, Bloomberg, Financial Times, WSJ, CNBC, Nikkei Asia, Caixin, AP |
| Bancos centrais | federalreserve.gov, ecb.europa.eu, boj.or.jp, pbc.gov.cn, bcb.gov.br |
| Expectativas de juros | CME FedWatch, curva de Treasuries (treasury.gov), Focus (BCB), curva DI (B3) |
| Dados econômicos | FRED (St. Louis Fed), BLS, BEA, Eurostat, NBS (China), IBGE |
| Agenda | calendários econômicos (Investing.com, Trading Economics), datas de resultados no RI |
| Empresas dos EUA | SEC EDGAR (10-K, 10-Q, 8-K, Form 4 de insiders), RI da empresa |
| Empresas de outros países | relatório anual no RI, reguladores locais (FCA, AMF, BaFin, JPX, HKEX) |
| Risco-país e prêmio | Damodaran (ctryprem), CDS soberanos |
| Brasil | seção 5.2 |
