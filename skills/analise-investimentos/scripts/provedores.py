"""Várias fontes de preços e de dados macro, em cadeia: se uma falha, tenta a próxima.

Preços diários (ordem padrão; mude com ANALISE_FONTES_PRECO="yahoo,stooq,alphavantage,brapi,b3"):
  yahoo         sem chave; preços ajustados por proventos e desdobramentos; qualquer bolsa
  stooq         sem chave; EUA, Reino Unido, Alemanha, Japão, Hong Kong e índices (fechamento, sem ajuste
                por proventos)
  alphavantage  precisa de ALPHAVANTAGE_API_KEY (gratuita em alphavantage.co); qualquer bolsa grande,
                inclusive B3 (PETR4.SAO)
  brapi         B3; precisa de BRAPI_TOKEN (gratuito em brapi.dev)
  b3            B3 oficial (COTAHIST), sem chave, ajustado pelos eventos corporativos da B3

Macro mundial: FRED (Federal Reserve de St. Louis), sem chave, como reserva do painel do Yahoo.

Cada série devolvida registra de qual fonte veio (proveniência). Fontes sem ajuste por proventos
subestimam o retorno total de quem paga muito dividendo: isso é anotado.
"""
from __future__ import annotations

import io
import os

import pandas as pd

import fontes as fx
import mercados as mk

ORDEM_PADRAO = ["yahoo", "stooq", "alphavantage", "brapi", "b3"]
AJUSTADAS = {"yahoo", "b3"}           # fontes com ajuste por proventos


def ordem() -> list[str]:
    v = os.environ.get("ANALISE_FONTES_PRECO")
    return [x.strip().lower() for x in v.split(",") if x.strip()] if v else ORDEM_PADRAO


# ---------------------------------------------------------------- Stooq
_STOOQ_SUF = {mk.EUA: "us", ".L": "uk", ".DE": "de", ".F": "de", ".T": "jp", ".HK": "hk"}
_STOOQ_INDICES = {"^GSPC": "^spx", "^IXIC": "^ndq", "^N225": "^nkx", "^FTSE": "^ftm", "^GDAXI": "^dax",
                  "^HSI": "^hsi", "^STOXX50E": "^sx5e"}


def simbolo_stooq(s: str) -> str | None:
    s = s.upper()
    if s in _STOOQ_INDICES:
        return _STOOQ_INDICES[s]
    if s.startswith("^") or s.endswith("=X") or s.endswith("=F") or mk.eh_b3(s):
        return None
    m = mk.mercado(s)
    base = s.split(".")[0] if "." in s else s
    if m is mk.EUA:
        return f"{base.replace('-', '.').lower()}.us"
    suf = _STOOQ_SUF.get(m.codigo)
    if not suf:
        return None
    if suf == "hk":
        base = base.lstrip("0") or "0"
    return f"{base.lower()}.{suf}"


def stooq(s: str, anos: int) -> pd.Series:
    sym = simbolo_stooq(s)
    if not sym:
        raise fx.FonteIndisponivel(f"Stooq não cobre {s}")
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    txt = fx._get(url, tentativas=1, timeout=30).text
    if not txt.lower().startswith("date"):
        raise fx.FonteIndisponivel(f"Stooq sem dados para {sym}")
    d = pd.read_csv(io.StringIO(txt), parse_dates=["Date"]).set_index("Date")["Close"].astype(float)
    d = d[d.index >= d.index.max() - pd.DateOffset(years=anos)]
    fx.PROV.add("Stooq — fechamentos diários (sem ajuste por proventos)", url, sym)
    return d


# ---------------------------------------------------------------- Alpha Vantage
_AV_SUF = {"B3": "SAO", ".L": "LON", ".DE": "DEX", ".TO": "TRT", ".V": "TRV", ".PA": "PAR", ".AS": "AMS",
           ".SS": "SHH", ".SZ": "SHZ", ".NS": "NSE", ".BO": "BSE"}


def simbolo_alphavantage(s: str) -> str | None:
    s = s.upper()
    if s.startswith("^") or s.endswith("=X") or s.endswith("=F"):
        return None
    m = mk.mercado(s)
    if m is mk.EUA:
        return s.replace("-", ".")
    base = s.replace(".SA", "").split(".")[0] if m is not mk.B3 else s.replace(".SA", "")
    suf = _AV_SUF.get(m.codigo)
    return f"{base}.{suf}" if suf else None


def alphavantage(s: str, anos: int) -> pd.Series:
    chave = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not chave:
        raise fx.FonteIndisponivel("ALPHAVANTAGE_API_KEY não definida")
    sym = simbolo_alphavantage(s)
    if not sym:
        raise fx.FonteIndisponivel(f"Alpha Vantage não cobre {s}")
    url = "https://www.alphavantage.co/query"
    js = None
    for tamanho in ("full", "compact"):     # 'full' pode exigir plano pago; 'compact' = ~100 pregões
        js = fx._get(url, {"function": "TIME_SERIES_DAILY", "symbol": sym, "outputsize": tamanho,
                           "apikey": chave}, tentativas=1, timeout=30).json()
        if "Time Series (Daily)" in js:
            break
    serie = (js or {}).get("Time Series (Daily)")
    if not serie:
        msg = (js or {}).get("Note") or (js or {}).get("Information") or (js or {}).get("Error Message") or "sem dados"
        raise fx.FonteIndisponivel(f"Alpha Vantage: {str(msg)[:120]}")
    d = pd.Series({pd.Timestamp(k): float(v["4. close"]) for k, v in serie.items()}).sort_index()
    d = d[d.index >= d.index.max() - pd.DateOffset(years=anos)]
    fx.PROV.add("Alpha Vantage — fechamentos diários (sem ajuste por proventos)", url, sym)
    return d


# ---------------------------------------------------------------- brapi (B3)
def brapi(s: str, anos: int) -> pd.Series:
    if not mk.eh_b3(s):
        raise fx.FonteIndisponivel("brapi só cobre a B3")
    token = os.environ.get("BRAPI_TOKEN")
    if not token:
        raise fx.FonteIndisponivel("BRAPI_TOKEN não definido")
    t = s.upper().replace(".SA", "")
    url = f"https://brapi.dev/api/quote/{t}"
    js = fx._get(url, {"range": f"{min(anos, 10)}y", "interval": "1d", "token": token}, tentativas=1, timeout=30).json()
    hist = ((js.get("results") or [{}])[0]).get("historicalDataPrice") or []
    if not hist:
        raise fx.FonteIndisponivel(f"brapi sem histórico para {t} (o plano gratuito pode limitar o período)")
    d = pd.Series({pd.to_datetime(h["date"], unit="s").normalize(): float(h.get("adjustedClose") or h["close"])
                   for h in hist if h.get("close") is not None}).sort_index()
    fx.PROV.add("brapi — histórico B3", url, t)
    return d


# ---------------------------------------------------------------- B3 oficial e Yahoo (um símbolo)
def b3_oficial(s: str, anos: int) -> pd.Series:
    if not (mk.eh_b3(s) or s.upper() == "^BVSP"):
        raise fx.FonteIndisponivel("COTAHIST só cobre a B3")
    import b3
    t = "BOVA11" if s.upper() == "^BVSP" else s.upper().replace(".SA", "")
    d = b3.precos_ajustados([t], anos)
    if t not in d:
        raise fx.FonteIndisponivel(f"COTAHIST sem {t}")
    fx.PROV.add("B3 — COTAHIST oficial", b3.COTAHIST_URL.format(ano="<ANO>"),
                t + (" (aproxima o Ibovespa)" if t == "BOVA11" else ""))
    return d[t].dropna()


def yahoo(s: str, anos: int) -> pd.Series:
    df, falhas = fx._precos_yahoo([s], anos)
    if df is None or s.upper() not in df:
        raise fx.FonteIndisponivel(f"Yahoo sem {s}")
    return df[s.upper()].dropna()


PROVEDORES = {"yahoo": yahoo, "stooq": stooq, "alphavantage": alphavantage, "brapi": brapi, "b3": b3_oficial}


def serie(s: str, anos: int, pular: set[str] = frozenset()) -> tuple[pd.Series, str, list[str]]:
    """Primeira fonte que responder. Devolve (série, fonte usada, falhas anteriores)."""
    falhas = []
    for nome in ordem():
        if nome in pular or nome not in PROVEDORES:
            continue
        try:
            d = PROVEDORES[nome](s, anos)
            if len(d) >= 2:
                return d, nome, falhas
            falhas.append(f"{nome}: série curta")
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{nome}: {str(e)[:80]}")
    raise fx.FonteIndisponivel(f"{s}: nenhuma fonte respondeu ({'; '.join(falhas)})")


def precos(simbolos: list[str], anos: int = 5) -> tuple[pd.DataFrame, dict[str, str]]:
    """Tabela de preços com fonte por símbolo. Símbolos sem nenhuma fonte ficam de fora (e são listados)."""
    cols, origem = {}, {}
    for s in simbolos:
        try:
            d, nome, falhas = serie(s, anos)
            cols[s.upper()] = d
            origem[s.upper()] = nome
            if falhas:
                fx.PROV.add("Preços — fontes que falharam antes", "", f"{s}: {'; '.join(falhas)}")
        except fx.FonteIndisponivel as e:
            origem[s.upper()] = f"FALHOU ({str(e)[:100]})"
    if not cols:
        raise fx.FonteIndisponivel(f"Sem preços para nenhum de {simbolos}")
    df = pd.DataFrame(cols).sort_index()
    return df[~df.index.duplicated()], origem


def conferir_ultimo_preco(s: str, anos: int = 1, tolerancia: float = 0.02) -> dict:
    """Compara o último fechamento em duas fontes diferentes (conferência cruzada)."""
    d1, f1, _ = serie(s, anos)
    try:
        d2, f2, _ = serie(s, anos, pular={f1})
    except fx.FonteIndisponivel:
        return {"ticker": s, "fonte_1": f1, "preco_1": float(d1.iloc[-1]), "data_1": str(d1.index[-1].date()),
                "conferido": False, "obs": "só uma fonte disponível"}
    data = min(d1.index[-1], d2.index[-1])
    p1, p2 = float(d1[:data].iloc[-1]), float(d2[:data].iloc[-1])
    dif = p2 / p1 - 1
    return {"ticker": s, "data": str(data.date()), "fonte_1": f1, "preco_1": p1, "fonte_2": f2, "preco_2": p2,
            "diferenca": dif, "conferido": abs(dif) <= tolerancia,
            "obs": "ok" if abs(dif) <= tolerancia else
            "DIVERGÊNCIA: confirmar na bolsa (pode ser ajuste por provento/desdobramento numa das fontes)"}


# ---------------------------------------------------------------- FRED (macro mundial, sem chave)
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}"
# símbolo do painel -> (série do FRED, observação)
FRED_PAINEL = {
    "^TNX": ("DGS10", ""), "^IRX": ("DTB3", ""), "^VIX": ("VIXCLS", ""), "BZ=F": ("DCOILBRENTEU", "Brent spot"),
    "^GSPC": ("SP500", ""), "^IXIC": ("NASDAQCOM", ""), "USDBRL=X": ("DEXBZUS", ""), "USDJPY=X": ("DEXJPUS", ""),
    "USDCNY=X": ("DEXCHUS", ""), "EURUSD=X": ("DEXUSEU", ""),
    "DX-Y.NYB": ("DTWEXBGS", "índice amplo do dólar do Fed, escala diferente do DXY"),
}


def fred(serie_id: str, anos: int = 2) -> pd.Series:
    url = FRED_URL.format(id=serie_id)
    txt = fx._get(url, tentativas=2, timeout=30).text
    d = pd.read_csv(io.StringIO(txt))
    d.columns = ["data", "valor"]
    d["data"] = pd.to_datetime(d["data"])
    s = pd.to_numeric(d["valor"], errors="coerce")
    s.index = d["data"]
    s = s.dropna()
    s = s[s.index >= s.index.max() - pd.DateOffset(years=anos)]
    fx.PROV.add("FRED (St. Louis Fed)", url, serie_id)
    return s
