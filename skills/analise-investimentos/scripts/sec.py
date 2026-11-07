"""Empresas dos EUA: demonstrações anuais (10-K) a partir do XBRL da SEC -> tabela e indicadores.

Fonte: data.sec.gov/api/xbrl/companyfacts (gratuita, oficial, sem chave). A SEC pede um User-Agent com
nome e e-mail de contato: defina a variável de ambiente SEC_USER_AGENT="Seu Nome seu@email.com".

Empresas de outros países (Europa, Ásia etc.) não têm uma base gratuita padronizada: os números vêm do
relatório anual no site de RI, pesquisado na web pelo agente, sempre com fonte.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

# conta -> lista de tags us-gaap, na ordem de preferência
TAGS = {
    "receita_liquida": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                        "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "lucro_bruto": ["GrossProfit"],
    "ebit": ["OperatingIncomeLoss"],
    "lucro_liquido": ["NetIncomeLoss", "ProfitLoss"],
    "despesa_juros": ["InterestExpense", "InterestExpenseNonoperating"],
    "ir": ["IncomeTaxExpenseBenefit"],
    "lair": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
             "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "Depreciation"],
    "fco": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "dividendos_pagos": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "recompra_acoes": ["PaymentsForRepurchaseOfCommonStock"],
    "ativo_total": ["Assets"],
    "ativo_circulante": ["AssetsCurrent"],
    "passivo_circulante": ["LiabilitiesCurrent"],
    "passivo_total": ["Liabilities"],
    "patrimonio_liquido": ["StockholdersEquity",
                           "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "caixa": ["CashAndCashEquivalentsAtCarryingValue",
              "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "investimentos_cp": ["ShortTermInvestments", "MarketableSecuritiesCurrent"],
    "divida_lp": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "divida_cp": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings"],
    "acoes": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}
FLUXOS = {"receita_liquida", "lucro_bruto", "ebit", "lucro_liquido", "despesa_juros", "ir", "lair", "da", "fco",
          "capex", "dividendos_pagos", "recompra_acoes", "acoes"}


def _serie_anual(facts: dict, tag: str, fluxo: bool) -> pd.Series:
    """Valores anuais do 10-K para uma tag: um por ano fiscal (pelo fim do período), versão mais recente."""
    g = facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not g:
        return pd.Series(dtype=float)
    unidades = g.get("units", {})
    itens = unidades.get("USD") or unidades.get("shares") or next(iter(unidades.values()), [])
    linhas = []
    for x in itens:
        if not str(x.get("form", "")).startswith("10-K") or x.get("fp") != "FY":
            continue
        fim = dt.date.fromisoformat(x["end"])
        if fluxo:
            if "start" not in x:
                continue
            dias = (fim - dt.date.fromisoformat(x["start"])).days
            if not 330 <= dias <= 400:
                continue
        linhas.append((fim.year if fim.month > 3 else fim.year - 1, x.get("filed", ""), float(x["val"])))
    if not linhas:
        return pd.Series(dtype=float)
    df = pd.DataFrame(linhas, columns=["ano", "filed", "val"]).sort_values(["ano", "filed"])
    return df.groupby("ano")["val"].last()


def tabela_anual_sec(facts: dict, anos: int = 8) -> pd.DataFrame:
    """Contas (linhas) × anos (colunas), em US$."""
    dados = {}
    for conta, tags in TAGS.items():
        for tag in tags:
            s = _serie_anual(facts, tag, conta in FLUXOS)
            if len(s):
                dados[conta] = s
                break
    t = pd.DataFrame(dados).T
    if t.empty:
        raise ValueError("Nenhuma conta us-gaap reconhecida nos dados da SEC")
    cols = sorted(t.columns)[-anos:]
    return t[cols]


def indicadores_sec(t: pd.DataFrame) -> pd.DataFrame:
    """Mesmos nomes de fundamentos.indicadores, para o resto do motor e para explorar_dados.py."""
    T = t.T.astype(float)
    g = lambda c: T[c] if c in T else pd.Series(np.nan, index=T.index)  # noqa: E731
    i = pd.DataFrame(index=T.index)
    i["receita_liquida"] = g("receita_liquida")
    i["crescimento_receita"] = i["receita_liquida"].pct_change(fill_method=None)
    i["lucro_liquido"] = g("lucro_liquido")
    i["lucro_controladores"] = g("lucro_liquido")
    i["margem_bruta"] = g("lucro_bruto") / i["receita_liquida"]
    i["margem_ebit"] = g("ebit") / i["receita_liquida"]
    i["ebitda"] = g("ebit") + g("da").fillna(0)
    i["margem_ebitda"] = i["ebitda"] / i["receita_liquida"]
    i["margem_liquida"] = i["lucro_liquido"] / i["receita_liquida"]
    pl_medio = (g("patrimonio_liquido") + g("patrimonio_liquido").shift()) / 2
    at_medio = (g("ativo_total") + g("ativo_total").shift()) / 2
    i["roe"] = i["lucro_liquido"] / pl_medio
    i["roa"] = i["lucro_liquido"] / at_medio
    i["aliquota_efetiva"] = g("ir") / g("lair")
    aliq = i["aliquota_efetiva"].clip(0, 0.4).fillna(0.21)
    i["nopat"] = g("ebit") * (1 - aliq)
    i["divida_bruta"] = g("divida_lp").fillna(0) + g("divida_cp").fillna(0)
    i["caixa_e_aplicacoes"] = g("caixa").fillna(0) + g("investimentos_cp").fillna(0)
    i["divida_liquida"] = i["divida_bruta"] - i["caixa_e_aplicacoes"]
    i["capital_investido"] = g("patrimonio_liquido") + i["divida_liquida"]
    ci_medio = (i["capital_investido"] + i["capital_investido"].shift()) / 2
    i["roic"] = i["nopat"] / ci_medio
    i["divida_liquida_ebitda"] = i["divida_liquida"] / i["ebitda"]
    i["divida_liquida_pl"] = i["divida_liquida"] / g("patrimonio_liquido")
    i["liquidez_corrente"] = g("ativo_circulante") / g("passivo_circulante")
    i["cobertura_juros"] = g("ebit") / g("despesa_juros")
    i["fco"] = g("fco")
    i["capex"] = g("capex")
    i["fcf"] = i["fco"] - i["capex"].fillna(0)
    i["fco_sobre_lucro"] = i["fco"] / i["lucro_liquido"]
    i["accruals"] = i["lucro_liquido"] - i["fco"]
    i["accruals_sobre_ativo"] = i["accruals"] / at_medio
    i["dividendos_pagos"] = g("dividendos_pagos")
    i["payout_caixa"] = i["dividendos_pagos"] / i["lucro_liquido"]
    i["acoes_diluidas"] = g("acoes")
    i["lpa"] = i["lucro_liquido"] / i["acoes_diluidas"]
    i["vpa"] = g("patrimonio_liquido") / i["acoes_diluidas"]
    return i


def multiplos_sec(ind: pd.DataFrame, preco: float) -> dict:
    """Múltiplos com o último 10-K. Quantidade de ações: média diluída do ano (confirmar no 10-Q mais recente)."""
    u = ind.iloc[-1]
    acoes = u.get("acoes_diluidas")
    if not acoes or np.isnan(acoes):
        raise ValueError("Quantidade de ações indisponível no XBRL")
    mcap = preco * acoes
    ev = mcap + (u["divida_liquida"] if pd.notna(u["divida_liquida"]) else 0)
    pos = lambda x: x if pd.notna(x) and x > 0 else None  # noqa: E731
    return {
        "ano_base": int(ind.index[-1]), "preco": preco, "acoes": acoes, "valor_mercado": mcap, "enterprise_value": ev,
        "p_l": mcap / u["lucro_liquido"] if pos(u["lucro_liquido"]) else None,
        "p_vp": preco / u["vpa"] if pos(u["vpa"]) else None,
        "ev_ebitda": ev / u["ebitda"] if pos(u["ebitda"]) else None,
        "p_fcf": mcap / u["fcf"] if pos(u["fcf"]) else None,
        "dividend_yield_caixa": u["dividendos_pagos"] / mcap if pd.notna(u["dividendos_pagos"]) else None,
        "lpa": u["lpa"], "vpa": u["vpa"],
        "observacoes": ["Base: último 10-K (SEC XBRL), em US$.",
                        "Ações = média diluída do exercício; confirme a quantidade atual no 10-Q.",
                        "Dívida = dívida de longo prazo + parcela de curto prazo (sem arrendamentos)."],
    }
