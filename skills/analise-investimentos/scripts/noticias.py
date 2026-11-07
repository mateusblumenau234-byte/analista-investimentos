#!/usr/bin/env python3
"""Radar de notícias: empresa, setor e contexto mundial, com rumores separados de fatos.

Uso:
  python noticias.py --empresa "Apple" --ticker AAPL [--setor "smartphones"] [--dias 30] \
      [--idiomas pt,en] [--consulta "Apple tarifas China"] --saida relatorios/AAPL_2026-11-07

Fonte: busca do Google Notícias em RSS (pública, sem chave), em português e inglês.
Etapas, inspiradas no Horizon (Thysrael, MIT): coleta de várias consultas -> remoção de duplicadas
(mesma manchete em veículos diferentes) -> classificação por tipo -> pontuação por relevância,
recência e confiabilidade da fonte -> briefing em Markdown.

A classificação é por palavras-chave e serve para ORGANIZAR a leitura. O agente deve abrir as
notícias importantes, confirmar fatos na fonte primária (RI, regulador, comunicado oficial) e tratar
tudo marcado como RUMOR como não confirmado.

Grava: noticias.md (briefing) e noticias.json (itens com pontuação).
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

URL = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
IDIOMAS = {"pt": ("pt-BR", "BR", "BR:pt-419"), "en": ("en-US", "US", "US:en")}

# contexto mundial: o que move mercados no mundo todo
CONSULTAS_GLOBAIS = {
    "pt": ["Federal Reserve juros", "inflação Estados Unidos", "economia China", "petróleo OPEP",
           "tarifas guerra comercial", "Banco Central Europeu", "mercados emergentes fluxo estrangeiro",
           "geopolítica mercados", "Copom Selic"],
    "en": ["Federal Reserve rate expectations", "US inflation CPI", "China economy stimulus", "oil OPEC",
           "tariffs trade war", "ECB rates", "emerging markets flows", "geopolitical risk markets",
           "Bank of Japan", "earnings season outlook"],
}

# Brasil: risco político e fiscal, com checagem. Consultas institucionais, sem nomes de pessoas,
# para continuarem valendo quando o governo mudar.
CONSULTAS_BRASIL = ["Planalto governo federal economia", "presidente da República mercado financeiro",
                    "arcabouço fiscal meta primário", "dívida pública risco fiscal", "Congresso votação economia",
                    "STF decisão impacto empresas", "Copom Banco Central decisão", "estatais interferência governo",
                    "pesquisa eleitoral mercado", "reforma tributária", "checagem fake news economia governo"]

TIPOS = {
    "rumor": r"\brumor|\brumou?r|reportedly|people familiar|sources? (?:said|say)|according to sources|in talks|"
             r"considering|weighs?|exploring|fontes? (?:dizem|afirmam|ouvidas)|segundo pessoas|"
             r"estaria|avalia |estuda |negocia|em negocia[cç][aã]o|especula",
    "expectativa": r"consensus|estimates?|expect|forecast|guidance|outlook|price target|upgrade|downgrade|"
                   r"rating|projeç|expectativ|estimativ|preço-alvo|preco-alvo|recomenda|eleva|rebaixa|"
                   r"consenso|perspectiva|previs|fedwatch|futures|implied",
    "resultado": r"earnings|results|quarter|revenue|profit|lucro|receita|balanço|balanco|resultado|trimestre|"
                 r"\b[1-4]q\d{2}\b|\b[1-4]t\d{2}\b|dividend|provento|jcp|buyback|recompra",
    "regulacao_juridico": r"regulat|antitrust|lawsuit|probe|investigat|fine[ds]?\b|sanction|sec |cvm|cade|"
                          r"processo|multa|investiga|justiça|tribunal|ban\b|tarif",
    "gestao_governanca": r"\bceo\b|\bcfo\b|resign|appoint|board|chairman|renúncia|renuncia|nomeia|conselho|"
                         r"presidente|diretor|governança|governanca",
    "fusao_aquisicao": r"acquir|merger|takeover|deal|stake|ipo\b|follow-on|aquisi|fusão|fusao|compra de|"
                       r"venda de|oferta de ações|oferta de acoes",
    "checagem": r"checagem|fact.?check|é falso|e falso|é enganoso|enganos|fato ou fake|verificamos|comprova|"
                r"aos fatos|agência lupa|agencia lupa|estadão verifica|estadao verifica|boato|fake news|desinforma",
    "politica_fiscal": r"planalto|presidente|governo federal|ministro|congresso|câmara|camara|senado|stf|"
                       r"eleiç|eleic|pesquisa eleitoral|fiscal|arcabouço|arcabouco|dívida pública|divida publica|"
                       r"estatal|estatais|reforma",
    "macro": r"inflation|inflação|inflacao|rates?|juros|gdp|pib|recession|recessão|recessao|fed\b|ecb|"
             r"central bank|banco central|selic|treasury|yield|dólar|dolar|currency|câmbio|cambio|oil|petróleo",
}

DESMENTIDO = (r"\bden(?:y|ies|ied)\b|refut|dismiss|\bfalse\b|fake|baseless|not true|no plans|rules? out|"
              r"desment|\bnega\b|negou|refuta|sem fundamento|não procede|nao procede|descarta|boato falso|"
              r"é falso|e falso|é enganoso|fake news|fato ou fake")
CONFIRMADO = (r"\bconfirm|announc|officially|signs? (?:deal|agreement)|completes?|agreed to|"
              r"confirma|anuncia|fato relevante|comunicado oficial|assina|conclui|aprovad")

# Escala de credibilidade do rumor (o agente revisa e dá a palavra final; ver references/contexto_global.md)
NIVEIS = {
    "real": "REAL: confirmado oficialmente",
    "provavel": "PODE ACONTECER (provável): fonte de referência e/ou vários veículos independentes",
    "possivel": "PODE ACONTECER (possível): uma fonte, sem confirmação nem desmentido",
    "improvavel": "CHANCE QUASE NULA: fonte fraca, sem eco em outros veículos",
    "desmentido": "CHANCE QUASE NULA: desmentido por envolvidos ou autoridade",
}

FONTES_TIER = {  # 3 = agência/jornal financeiro de referência; 2 = imprensa econômica; 1 = demais
    3: ["reuters", "bloomberg", "financial times", "wall street journal", "wsj", "valor econômico", "valor economico",
        "the economist", "nikkei", "associated press", "ap news", "cnbc", "barron", "estadão", "estadao",
        "folha", "o globo", "caixin", "sec.gov", "cvm", "banco central", "agência brasil", "agencia brasil",
        "g1", "uol", "bbc", "poder360", "jota", "agência lupa", "agencia lupa", "aos fatos", "comprova",
        "estadão verifica", "estadao verifica", "fato ou fake"],
    2: ["infomoney", "money times", "exame", "brazil journal", "e-investidor", "investing.com", "marketwatch",
        "yahoo finance", "seeking alpha", "business insider", "fortune", "forbes", "the motley fool",
        "bloomberg línea", "bloomberg linea", "neofeed", "investnews", "seu dinheiro"],
}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\s+-\s+[^-]+$", "", t)          # remove " - Nome do Veículo" do fim da manchete
    return re.sub(r"[^a-z0-9 ]", " ", t)


def _tokens(t: str) -> set[str]:
    return {w for w in _norm(t).split() if len(w) > 3}


def classificar(titulo: str) -> list[str]:
    t = titulo.lower()
    tipos = [k for k, rx in TIPOS.items() if re.search(rx, t)]
    return tipos or ["geral"]


def tier(fonte: str) -> int:
    f = (fonte or "").lower()
    for n in (3, 2):
        if any(x in f for x in FONTES_TIER[n]):
            return n
    return 1


def parse_rss(xml_texto: str, consulta: str, escopo: str) -> list[dict]:
    itens = []
    try:
        raiz = ET.fromstring(xml_texto)
    except ET.ParseError:
        return itens
    for it in raiz.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        if not titulo:
            continue
        fonte_el = it.find("source")
        fonte = (fonte_el.text if fonte_el is not None else "") or ""
        data = None
        if it.findtext("pubDate"):
            try:
                data = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(dt.timezone.utc)
            except (TypeError, ValueError):
                pass
        itens.append({"titulo": titulo, "link": it.findtext("link") or "", "fonte": fonte.strip(),
                      "data": data.isoformat() if data else None, "consulta": consulta, "escopo": escopo})
    return itens


def deduplicar(itens: list[dict], limiar: float = 0.6) -> list[dict]:
    """Junta manchetes quase iguais (Jaccard das palavras >= limiar); guarda a de fonte mais confiável."""
    grupos: list[dict] = []
    for it in sorted(itens, key=lambda x: (-tier(x["fonte"]), x["data"] or ""), reverse=False):
        tk = _tokens(it["titulo"])
        for g in grupos:
            inter = len(tk & g["_tk"])
            uni = len(tk | g["_tk"]) or 1
            if it["link"] == g["link"] or inter / uni >= limiar:
                # conta só veículos diferentes (a mesma matéria pode voltar em várias consultas)
                if it["fonte"] and it["fonte"] != g["fonte"] and it["fonte"] not in g["outras_fontes"]:
                    g["outras_fontes"].append(it["fonte"])
                break
        else:
            grupos.append({**it, "_tk": tk, "outras_fontes": []})
    for g in grupos:
        g.pop("_tk")
    return grupos


def pontuar(it: dict, termos: list[str], agora: dt.datetime) -> float:
    t = _norm(it["titulo"])
    relev = sum(1 for x in termos if x and _norm(x).strip() in t)
    dias = 30.0
    if it.get("data"):
        dias = max((agora - dt.datetime.fromisoformat(it["data"])).total_seconds() / 86400, 0)
    recencia = max(0.0, 1 - dias / 30)
    eco = min(len(it.get("outras_fontes", [])), 5) * 0.3     # mesma notícia em vários veículos
    tipos_peso = {"resultado": 1.0, "fusao_aquisicao": 1.0, "regulacao_juridico": 0.8, "expectativa": 0.8,
                  "gestao_governanca": 0.6, "rumor": 0.5, "macro": 0.5, "geral": 0.0}
    tipo = max(tipos_peso.get(x, 0) for x in it["tipos"])
    return round(2 * min(relev, 2) + 2 * recencia + 0.7 * tier(it["fonte"]) + eco + tipo, 2)


def _raizes(titulo: str, ignorar: set[str]) -> set[str]:
    """Raízes de 5 letras das palavras distintivas (sem o nome da empresa, que aparece em tudo)."""
    return {w[:5] for w in _tokens(titulo) if w not in ignorar}


def mesma_historia(a: str, b: str, ignorar: set[str] = frozenset(), limiar: float = 0.4) -> bool:
    ra, rb = _raizes(a, ignorar), _raizes(b, ignorar)
    if not ra or not rb:
        return False
    return len(ra & rb) / min(len(ra), len(rb)) >= limiar


def nivel_rumor(it: dict, todos: list[dict], ignorar: set[str] = frozenset()) -> str:
    """Classificação automática inicial de um rumor. O agente confirma ou corrige lendo as matérias."""
    titulo = it["titulo"].lower()
    if re.search(DESMENTIDO, titulo):
        return "desmentido"
    if re.search(CONFIRMADO, titulo):
        return "real"
    for o in todos:                       # outra manchete da mesma história que desmente ou confirma
        if o is it:
            continue
        if mesma_historia(it["titulo"], o["titulo"], ignorar):
            if re.search(DESMENTIDO, o["titulo"].lower()):
                return "desmentido"
            if re.search(CONFIRMADO, o["titulo"].lower()) and "rumor" not in o.get("tipos", []):
                return "real"
    eco = len(it.get("outras_fontes", []))
    if tier(it["fonte"]) == 3 or eco >= 2:
        return "provavel"
    if tier(it["fonte"]) == 2 or eco == 1:
        return "possivel"
    return "improvavel"


def coletar(consultas: list[tuple[str, str, str]], dias: int, baixar) -> list[dict]:
    """consultas: (texto, idioma, escopo). `baixar(url) -> str` é injetável para testes offline."""
    itens = []
    for texto, idioma, escopo in consultas:
        hl, gl, ceid = IDIOMAS[idioma]
        url = URL.format(q=quote(f"{texto} when:{dias}d"), hl=hl, gl=gl, ceid=ceid)
        try:
            itens += parse_rss(baixar(url), texto, escopo)
        except Exception as e:  # noqa: BLE001
            itens.append({"erro": f"{texto} ({idioma}): {type(e).__name__}"})
    return itens


def briefing(itens: list[dict], titulo: str, erros: list[str]) -> str:
    md = [f"# Radar de notícias: {titulo}", "",
          f"Coletado em {dt.datetime.now():%d/%m/%Y %H:%M}. Fonte: Google Notícias (RSS). Classificação automática "
          "por palavras-chave, para organizar a leitura: **abra as notícias importantes e confirme na fonte primária**.",
          "", "Legenda: [EXPECTATIVA] = projeções, consenso, recomendações · (+N) = mesma notícia em N outros veículos.",
          "", "Rumores (classificação automática inicial; o agente dá a palavra final):",
          *(f"- {v}" for v in NIVEIS.values()), ""]

    def linha(it):
        tags = " ".join(f"[{t.upper()}]" for t in it["tipos"] if t in ("rumor", "expectativa"))
        if it.get("nivel_rumor"):
            tags += f" **{NIVEIS[it['nivel_rumor']].split(':')[0]}** ({it['nivel_rumor']})"
        d = it["data"][:10] if it.get("data") else "s/d"
        extra = f" (+{len(it['outras_fontes'])})" if it["outras_fontes"] else ""
        return f"- {d} · **{it['fonte'] or 'fonte?'}**{extra} · {tags} [{it['titulo']}]({it['link']}) · nota {it['pontuacao']}"

    secoes = [("Empresa: fatos (resultados, aquisições, regulação, gestão)",
               lambda x: x["escopo"] == "empresa" and "rumor" not in x["tipos"] and "expectativa" not in x["tipos"]),
              ("Empresa: expectativas do mercado (consenso, recomendações, guidance)",
               lambda x: x["escopo"] == "empresa" and "expectativa" in x["tipos"] and "rumor" not in x["tipos"]),
              ("Empresa: rumores, por credibilidade (rumor mexe no preço mesmo sendo falso)",
               lambda x: x["escopo"] == "empresa" and "rumor" in x["tipos"]),
              ("Rumores do setor e do mundo", lambda x: x["escopo"] != "empresa" and "rumor" in x["tipos"]),
              ("Brasil: política, fiscal e instituições (separar fato, versão e desinformação)",
               lambda x: x["escopo"] == "brasil" and "rumor" not in x["tipos"]),
              ("Setor e concorrentes", lambda x: x["escopo"] == "setor" and "rumor" not in x["tipos"]),
              ("Contexto mundial (juros, inflação, China, petróleo, geopolítica, fluxos)",
               lambda x: x["escopo"] == "global" and "rumor" not in x["tipos"]),
              ("Outras consultas", lambda x: x["escopo"] == "extra")]
    for nome, filtro in secoes:
        sel = sorted([x for x in itens if filtro(x)], key=lambda x: -x["pontuacao"])[:15]
        md += [f"## {nome}", *([linha(x) for x in sel] or ["- Nada encontrado."]), ""]
    md += ["## O que o agente precisa fazer com isto",
           "1. Ler as 5 a 10 notícias de maior nota da empresa e as 5 do contexto mundial.",
           "2. Confirmar cada fato relevante na fonte primária (RI, regulador, comunicado) antes de usar.",
           "3. Rumores: para cada um relevante, confirmar ou corrigir o nível (REAL / PODE ACONTECER / CHANCE QUASE "
           "NULA), medir quanto o preço já reagiu e dizer o que muda na tese se virar verdade. Mesmo os de chance "
           "quase nula entram se mexeram no preço (risco de volatilidade e de reversão).",
           "4. Expectativas: registrar consenso e data; comparar com o que o preço já embute (reverse DCF).",
           "5. Brasil: para cada fato político ou fiscal, conferir na fonte oficial (Diário Oficial, Planalto, Câmara, "
           "Senado, STF, TSE, Tesouro, BCB, IFI) e em agências de checagem; ouvir veículos de linhas editoriais "
           "diferentes; avaliar só o efeito econômico, sem tomar partido (references/contexto_global.md).", ""]
    if erros:
        md += ["## Falhas na coleta", *(f"- {e}" for e in erros)]
    return "\n".join(md)


def _baixar_http(url: str) -> str:
    import requests
    r = requests.get(url, timeout=30, headers={"User-Agent": "analise-investimentos/1.0 (radar de noticias)"})
    r.raise_for_status()
    return r.text


def main(argv: list[str] | None = None, baixar=_baixar_http) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--empresa", required=True, help='Nome usado pela imprensa, ex.: "Banco do Brasil"')
    ap.add_argument("--ticker")
    ap.add_argument("--setor", help='Ex.: "bancos brasileiros" ou "semiconductors"')
    ap.add_argument("--consulta", action="append", default=[], help="Consulta extra (pode repetir)")
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--idiomas", default="pt,en")
    ap.add_argument("--sem-global", action="store_true", help="Não busca o contexto mundial")
    ap.add_argument("--brasil", action="store_true",
                    help="Inclui política, fiscal e instituições do Brasil (use para ativos da B3 ou investidor em R$)")
    ap.add_argument("--saida", default=".")
    a = ap.parse_args(argv)

    idiomas = [i.strip() for i in a.idiomas.split(",") if i.strip() in IDIOMAS]
    cons = []
    for i in idiomas:
        cons.append((a.empresa, i, "empresa"))
        if a.ticker:
            cons.append((f"{a.ticker} {a.empresa}" if i == "en" else a.ticker, i, "empresa"))
        if a.setor:
            cons.append((a.setor, i, "setor"))
        if not a.sem_global:
            cons += [(q, i, "global") for q in CONSULTAS_GLOBAIS[i]]
    if a.brasil:
        cons += [(q, "pt", "brasil") for q in CONSULTAS_BRASIL]
    cons += [(q, idiomas[0] if idiomas else "pt", "extra") for q in a.consulta]

    brutos = coletar(cons, a.dias, baixar)
    erros = [x["erro"] for x in brutos if "erro" in x]
    validos = [x for x in brutos if "erro" not in x]
    itens = []
    for escopo in ("empresa", "setor", "brasil", "global", "extra"):   # deduplica dentro de cada escopo
        itens += deduplicar([x for x in validos if x["escopo"] == escopo])
    agora = dt.datetime.now(dt.timezone.utc)
    termos = [a.empresa, a.ticker or ""] + a.empresa.split()
    for it in itens:
        it["tipos"] = classificar(it["titulo"])
        it["pontuacao"] = pontuar(it, termos if it["escopo"] == "empresa" else [it["consulta"]], agora)
    for it in itens:
        if "rumor" in it["tipos"]:
            it["nivel_rumor"] = nivel_rumor(it, itens, {w for t in termos for w in _tokens(t)})

    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)
    (out / "noticias.json").write_text(json.dumps(sorted(itens, key=lambda x: -x["pontuacao"]), ensure_ascii=False,
                                                  indent=1), encoding="utf-8")
    (out / "noticias.md").write_text(briefing(itens, a.ticker or a.empresa, erros), encoding="utf-8")
    print(f"OK -> {out / 'noticias.md'}: {len(itens)} notícias únicas de {len(validos)} coletadas; {len(erros)} falhas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
