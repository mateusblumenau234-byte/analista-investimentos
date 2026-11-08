# Analista de investimentos para Claude Code

Plugin do **Claude Code** que funciona como um analista de investimentos pessoal para **ações, ETFs, FIIs e
REITs de qualquer bolsa do mundo** (B3, EUA, Europa, Ásia e outras). Você manda um ticker e ele:

1. **Conhece você antes de analisar.** No primeiro uso faz uma entrevista de perfil (país, moeda, objetivo,
   horizonte, aportes, reação a quedas, alocação alvo, regras pessoais) e pede sua carteira. Depois, só
   pergunta o que mudou: se você já tem o ativo, se comprou algo, quanto vai aportar e o motivo.
2. **Lê o mundo em tempo real.**
   - Demonstrações oficiais: **CVM** (B3) e **SEC** (EUA). Outros países: relatório anual no site de RI.
   - **Painel mundial**: bolsas, Treasuries, dólar e moedas, VIX, petróleo, ouro, cobre, soja e bitcoin.
   - **Radar de notícias** em português e inglês: empresa, setor, contexto global (Fed, inflação, China,
     petróleo, tarifas, geopolítica) e expectativas do mercado (consenso, recomendações, juros esperados).
   - **Rumores considerados, nunca ignorados**, porque mexem no preço mesmo quando falsos. Cada um recebe
     um nível: **REAL**, **PODE ACONTECER** (provável ou possível) ou **CHANCE QUASE NULA** (improvável ou
     desmentido), com a reação que já causou no preço.
   - **Brasil com protocolo reforçado**: presidência, fiscal, Congresso, STF, Banco Central e eleições, com
     separação entre FATO, VERSÃO e DESINFORMAÇÃO, checagem em fontes oficiais e agências de checagem e
     leitura de veículos de linhas editoriais diferentes. Sem tomar partido: só o efeito econômico.
3. **Calcula com fórmulas registradas** (`references/formulas.md`): indicadores, qualidade dos lucros,
   múltiplos, CAPM e WACC por país, DCF com sensibilidade e reverse DCF, Gordon, DDM, lucro residual para
   bancos e Markowitz na **sua** carteira, convertida para a sua moeda.
4. **Explora os dados antes de concluir**: alertas de qualidade e gráficos em preto e cinza.
5. **Escreve um relatório de 20 seções** com um conselho de três analistas independentes (valor, macro e
   risco), nota de 0 a 10 e a separação entre dado observado, estimativa, premissa, interpretação e conclusão.
6. **Grava a memória** para a próxima vez.

## O app: mais que uma skill
O plugin instala também um **servidor MCP** (`servidor/analista.py`) que roda no seu computador e dá ao
Claude ferramentas próprias, em qualquer conversa, sem depender de scripts soltos:

| Ferramenta | O que faz |
|---|---|
| `carteira`, `resumo_do_ativo` | perfil, posições, alertas, último monitor e histórico de análises |
| `registrar_posicao`, `registrar_operacao`, `registrar_analise` | carteira persistente (compras, vendas, preço médio) |
| `cotacao`, `painel_mundial`, `serie_bcb`, `focus` | cotações de qualquer bolsa com conferência em duas fontes, mundo, Selic, IPCA, Focus |
| `noticias` | radar de notícias e rumores, com as notícias do Composio quando conectado |
| `analisar_ativo`, `valuation_dcf`, `nota_final`, `relatorio_html` | coleta completa, DCF com cenários, nota e relatório |
| `monitorar`, `criar_alerta`, `alertas`, `remover_alerta` | monitor da carteira e alertas de preço, variação e rumor |
| `painel` | painel visual em HTML: patrimônio no tempo, alocação, posições, alertas e análises |

Comandos: `/analisar TICKER`, `/carteira`, `/monitor`, `/painel` e `/alerta`. O conselho de três analistas
virou três agentes independentes (`analista-valor`, `analista-macro`, `analista-risco`), que rodam em
paralelo sem ver o parecer um do outro.

**Rodar sozinho**: o monitor cota a carteira, grava o patrimônio do dia, confere os alertas e varre notícias
e rumores de cada posição. Agende uma tarefa diária no Claude (app desktop: Tarefas agendadas) com o pedido
"rode /monitor e me avise do que importa", ou rode `python skills/analise-investimentos/scripts/monitor.py`
pelo Agendador de Tarefas do Windows ou pelo cron.

O painel fica em `~/.analise-investimentos/painel.html` e o banco do app em
`~/.analise-investimentos/dados/estado.db`. Os dois ficam só no seu computador.

## Instalação

Requisitos: [Claude Code](https://code.claude.com) e Python 3.10 ou mais novo.

No Claude Code:
```
/plugin install analise-investimentos --marketplace mateusblumenau234-byte/analista-investimentos
```
Ou em dois passos:
```
/plugin marketplace add mateusblumenau234-byte/analista-investimentos
/plugin install analise-investimentos@analista-investimentos
```
Instale as bibliotecas Python antes do primeiro uso (o servidor MCP precisa delas para iniciar):
```bash
pip install -r skills/analise-investimentos/requirements.txt
```
(numpy, pandas, requests, markdown, matplotlib e mcp). Depois reinicie o Claude Code e confira em `/mcp` que o
servidor `analista` está conectado.

### Fontes de dados extras (opcionais, gratuitas)
Sem nenhuma chave o analista já usa Yahoo, Stooq, FRED, CVM, B3 e Banco Central. Com chaves gratuitas,
ganha mais fontes de reserva e de conferência:
```bash
export ALPHAVANTAGE_API_KEY="sua-chave"   # alphavantage.co (ações do mundo, B3 inclusive)
export BRAPI_TOKEN="seu-token"            # brapi.dev (B3)
```
No Windows (PowerShell), para ficar salvo: `setx ALPHAVANTAGE_API_KEY "sua-chave"` e abra um terminal novo.

### Composio (opcional)
O analista usa o [Composio](https://composio.dev) quando ele está conectado ao Claude, por exemplo o toolkit
Alpha Vantage (cotações, balanços, notícias com sentimento, opções, commodities, dados econômicos). O jeito
mais simples, que funciona também no Windows, é adicionar o servidor MCP deles:
```
claude mcp add --transport http composio https://connect.composio.dev/mcp
```
e autorizar em `/mcp`. Há também o [plugin oficial](https://github.com/ComposioHQ/composio-plugin-cc)
(`/plugin marketplace add ComposioHQ/composio-plugin-cc`).

As notícias trazidas pelo Composio entram no radar de notícias (`noticias.py --extras arquivo.json`):
passam pela mesma remoção de duplicadas, classificação de rumores e pontuação, e aparecem marcadas
"via Composio", com o sentimento quando o Alpha Vantage informa.

O Composio é um serviço de terceiros: ao conectar um aplicativo, você dá acesso a ele. Conecte só o que for usar.

Para analisar ações dos EUA, a SEC pede identificação. Defina uma vez:
```bash
export SEC_USER_AGENT="Seu Nome seu@email.com"
```

## Como usar
> analisa AAPL
>
> analisa PETR4
>
> analisa ASML.AS e compara com a minha carteira

Tickers seguem o padrão do Yahoo Finance: `PETR4` (B3), `AAPL` (EUA), `ASML.AS` (Amsterdã), `SAP.DE`
(Frankfurt), `HSBA.L` (Londres), `7203.T` (Tóquio), `0700.HK` (Hong Kong), `600519.SS` (Xangai),
`SHOP.TO` (Toronto). Lista completa em `skills/analise-investimentos/scripts/mercados.py`.

## Privacidade
Perfil, carteira e histórico ficam em `~/.analise-investimentos/dados/`, na sua pasta pessoal, **fora de
qualquer repositório**. Para guardar em outro lugar, defina `ANALISE_DADOS`. Os relatórios vão para
`relatorios/` na pasta onde você está e estão no `.gitignore` deste projeto.

## Segurança
Skills e plugins rodam comandos no seu computador, então **leia o código antes de instalar qualquer um**,
inclusive este. Este plugin:
- só executa os próprios scripts (`skills/analise-investimentos/scripts/`) e o próprio servidor MCP
  (`servidor/analista.py`), que você pode ler;
- acessa a rede para baixar dados públicos (CVM, SEC, B3, Banco Central, Tesouro, Yahoo, Damodaran,
  Crossref, Google Notícias) e as páginas que o Claude pesquisa;
- não lê credenciais nem arquivos fora do projeto e da pasta da memória;
- não incorpora código de outras skills (créditos e inspirações em `references/creditos.md`).

Encontrou um problema de segurança? Abra uma issue.

## Desenvolvimento
```bash
pip install -r skills/analise-investimentos/requirements.txt
python -m pytest skills/analise-investimentos/tests -q
claude mcp add analista -- python servidor/analista.py   # usar o servidor fora do plugin
claude plugin validate .
```
Abrindo este repositório como projeto, `.claude/settings.json` libera buscas na web e a execução dos
scripts e testes sem pedir autorização a cada vez. Apague o arquivo se preferir aprovar um por um.

## Aviso
Material educacional e de pesquisa. **Não constitui recomendação de investimento.** Dados podem estar
atrasados ou errados; confira nas fontes primárias antes de decidir. Rumores são classificados
automaticamente e depois revisados, mas podem estar errados. Modelos são sensíveis às premissas e
retorno passado não garante retorno futuro.

## Licença
MIT. Veja `LICENSE`.
