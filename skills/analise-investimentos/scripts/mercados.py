"""Identifica o mercado de cada ticker: bolsa, país, moeda, índice de referência e símbolo no Yahoo.

Convenção dos tickers (a mesma do Yahoo Finance):
  B3            PETR4, ITUB4, BOVA11 (4 letras + 1 ou 2 dígitos; o sufixo .SA é opcional)
  EUA           AAPL, MSFT, BRK-B (sem sufixo)
  Outros        sufixo da bolsa: ASML.AS (Amsterdã), SAP.DE (Frankfurt), MC.PA (Paris), HSBA.L (Londres),
                7203.T (Tóquio), 0700.HK (Hong Kong), 600519.SS (Xangai), SHOP.TO (Toronto), BHP.AX (Sydney) ...
  Índices       começam com ^ (^GSPC, ^BVSP); câmbio termina em =X (USDBRL=X); futuros em =F (CL=F).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Mercado:
    codigo: str            # "B3", "EUA", ".T" ...
    pais: str              # nome do país na tabela de Damodaran (em inglês)
    moeda: str             # ISO 4217
    benchmark: str         # índice amplo no Yahoo
    nome_benchmark: str
    rf_yahoo: str | None   # rendimento do título de 10 anos no Yahoo (em %), quando existe


B3 = Mercado("B3", "Brazil", "BRL", "^BVSP", "Ibovespa", None)
EUA = Mercado("EUA", "United States", "USD", "^GSPC", "S&P 500", "^TNX")

SUFIXOS: dict[str, Mercado] = {
    ".SA": B3,
    ".TO": Mercado(".TO", "Canada", "CAD", "^GSPTSE", "S&P/TSX", None),
    ".V": Mercado(".V", "Canada", "CAD", "^GSPTSE", "S&P/TSX", None),
    ".MX": Mercado(".MX", "Mexico", "MXN", "^MXX", "IPC México", None),
    ".BA": Mercado(".BA", "Argentina", "ARS", "^MERV", "Merval", None),
    ".SN": Mercado(".SN", "Chile", "CLP", "^IPSA", "IPSA", None),
    ".L": Mercado(".L", "United Kingdom", "GBP", "^FTSE", "FTSE 100", None),
    ".DE": Mercado(".DE", "Germany", "EUR", "^GDAXI", "DAX", None),
    ".F": Mercado(".F", "Germany", "EUR", "^GDAXI", "DAX", None),
    ".PA": Mercado(".PA", "France", "EUR", "^FCHI", "CAC 40", None),
    ".AS": Mercado(".AS", "Netherlands", "EUR", "^AEX", "AEX", None),
    ".MI": Mercado(".MI", "Italy", "EUR", "FTSEMIB.MI", "FTSE MIB", None),
    ".MC": Mercado(".MC", "Spain", "EUR", "^IBEX", "IBEX 35", None),
    ".SW": Mercado(".SW", "Switzerland", "CHF", "^SSMI", "SMI", None),
    ".ST": Mercado(".ST", "Sweden", "SEK", "^OMX", "OMX 30", None),
    ".CO": Mercado(".CO", "Denmark", "DKK", "^OMXC25", "OMX C25", None),
    ".OL": Mercado(".OL", "Norway", "NOK", "OBX.OL", "OBX", None),
    ".T": Mercado(".T", "Japan", "JPY", "^N225", "Nikkei 225", None),
    ".HK": Mercado(".HK", "Hong Kong", "HKD", "^HSI", "Hang Seng", None),
    ".SS": Mercado(".SS", "China", "CNY", "000001.SS", "SSE Composite", None),
    ".SZ": Mercado(".SZ", "China", "CNY", "399001.SZ", "SZSE Component", None),
    ".KS": Mercado(".KS", "Korea", "KRW", "^KS11", "KOSPI", None),
    ".TW": Mercado(".TW", "Taiwan", "TWD", "^TWII", "TAIEX", None),
    ".NS": Mercado(".NS", "India", "INR", "^NSEI", "Nifty 50", None),
    ".BO": Mercado(".BO", "India", "INR", "^BSESN", "Sensex", None),
    ".AX": Mercado(".AX", "Australia", "AUD", "^AXJO", "S&P/ASX 200", None),
    ".SI": Mercado(".SI", "Singapore", "SGD", "^STI", "STI", None),
    ".JO": Mercado(".JO", "South Africa", "ZAR", "^J203.JO", "JSE All Share", None),
}

_B3 = re.compile(r"^[A-Z][A-Z0-9]{3,4}\d{1,2}[A-Z]?$")   # PETR4, BOVA11, B3SA3, TAEE11 ...


def mercado(ticker: str) -> Mercado:
    t = ticker.strip().upper()
    if t.endswith(".SA") or _B3.match(t):
        return B3
    if "." in t:
        suf = t[t.rfind("."):]
        if suf in SUFIXOS:
            return SUFIXOS[suf]
    return EUA


def eh_b3(ticker: str) -> bool:
    return not ticker.startswith("^") and mercado(ticker) is B3


def simbolo_yahoo(ticker: str) -> str:
    """Símbolo no Yahoo: B3 ganha .SA; o resto (EUA, sufixos, índices, câmbio, futuros) fica como está."""
    t = ticker.strip()
    if t.startswith("^") or t.endswith("=X") or t.endswith("=F") or "." in t:
        return t
    if _B3.match(t.upper()):
        return f"{t.upper()}.SA"
    return t.upper()


def par_cambio(de: str, para: str) -> str | None:
    """Símbolo do Yahoo para converter 1 unidade de `de` em `para` (ex.: USD -> BRL = 'USDBRL=X')."""
    de, para = de.upper(), para.upper()
    return None if de == para else f"{de}{para}=X"


# Painel do contexto mundial (todos no Yahoo; valores em pontos, preço ou % para rendimentos)
PAINEL_GLOBAL: dict[str, tuple[str, str]] = {
    "^GSPC": ("Bolsas", "S&P 500 (EUA)"),
    "^IXIC": ("Bolsas", "Nasdaq (EUA)"),
    "^STOXX50E": ("Bolsas", "Euro Stoxx 50 (Europa)"),
    "^FTSE": ("Bolsas", "FTSE 100 (Reino Unido)"),
    "^N225": ("Bolsas", "Nikkei 225 (Japão)"),
    "^HSI": ("Bolsas", "Hang Seng (Hong Kong)"),
    "000001.SS": ("Bolsas", "Xangai (China)"),
    "^NSEI": ("Bolsas", "Nifty 50 (Índia)"),
    "^BVSP": ("Bolsas", "Ibovespa (Brasil)"),
    "EEM": ("Bolsas", "ETF de emergentes (EEM)"),
    "^TNX": ("Juros", "Treasury 10 anos (EUA, % a.a.)"),
    "^IRX": ("Juros", "T-Bill 3 meses (EUA, % a.a.)"),
    "DX-Y.NYB": ("Moedas", "Índice do dólar (DXY)"),
    "EURUSD=X": ("Moedas", "Euro em dólar"),
    "USDJPY=X": ("Moedas", "Dólar em iene"),
    "USDCNY=X": ("Moedas", "Dólar em yuan"),
    "USDBRL=X": ("Moedas", "Dólar em real"),
    "^VIX": ("Risco", "VIX (medo no mercado americano)"),
    "BZ=F": ("Commodities", "Petróleo Brent (US$/barril)"),
    "GC=F": ("Commodities", "Ouro (US$/onça)"),
    "HG=F": ("Commodities", "Cobre (US$/libra)"),
    "ZS=F": ("Commodities", "Soja (centavos de US$/bushel)"),
    "BTC-USD": ("Cripto", "Bitcoin (US$)"),
}
