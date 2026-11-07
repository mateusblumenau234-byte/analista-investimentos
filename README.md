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
Na primeira análise o Claude instala as bibliotecas Python da skill (`requirements.txt`: numpy, pandas,
requests, markdown, matplotlib).

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
- só executa os próprios scripts (`skills/analise-investimentos/scripts/`), que você pode ler;
- acessa a rede para baixar dados públicos (CVM, SEC, B3, Banco Central, Tesouro, Yahoo, Damodaran,
  Crossref, Google Notícias) e as páginas que o Claude pesquisa;
- não lê credenciais nem arquivos fora do projeto e da pasta da memória;
- não incorpora código de outras skills (créditos e inspirações em `references/creditos.md`).

Encontrou um problema de segurança? Abra uma issue.

## Desenvolvimento
```bash
pip install -r skills/analise-investimentos/requirements.txt
python -m pytest skills/analise-investimentos/tests -q
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
