import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Afya · Status de autorizações de rádio", page_icon="📻", layout="wide")

# ------------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------------
SHEET_ID = "11_mLLdGgClBaKvRH9VPHWbm4qw3go66MTwK-dPAzjj0"
GID_RADIO = "1406362772"
ANO = 2026
ALTURA_PAINEL = 2600  # altura da área do painel em pixels

# nome interno -> cabeçalho na planilha
COLS = {
    "t": "SHE ou MED",
    "u": "UNIDADE",
    "sol": "Solicitação",
    "por": "Solicitante",
    "mr": "Mídia Responsável",
    "praca": "Praça de compra",
    "radio": "Rádio",
    "veic": "Veiculação",
    "st": "Status",
    "det": "Detalhes",
}

# status da planilha -> status do painel
STATUS_TROCA = {
    "resolvido": "Veiculando",
    "pi em execução": "PI em execução",
    "": "Sem status",
}

# ordem = ordem da tabela (em aberto primeiro, veiculando por último)
STATUS_BASE = [
    ["Erro Cadastro VBS", "#A3001B"],
    ["Aguardando definição/resposta do cliente", "#E0A100"],
    ["Cadastro pendente no veículo", "#EF7A1A"],
    ["PI a fazer", "#7B2D91"],
    ["PI em execução", "#B0457E"],
    ["Autorização não prioritária", "#8F8A9E"],
    ["Sem status", "#C9C2C7"],
    ["Aguardando confirmação do veículo/emissora", "#8EDB9F"],
    ["Veiculando com Pendência de Ajuste", "#2D6CDF"],
    ["Veiculando", "#1F8A70"],
]
CORES_EXTRAS = ["#5E35B1", "#00838F", "#6D4C41", "#AD1457", "#455A64"]

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
         "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
MES_CURTO = ["", "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# ------------------------------------------------------------------
# LEITURA DA PLANILHA
# ------------------------------------------------------------------
def inicio(veic, det):
    """dd/mm do início: 'Início em 07/10' dos Detalhes, senão a 1ª data da Veiculação,
    senão o 1º mês escrito por extenso (vira dia 01)."""
    d = str(det).lower()
    if re.search(r"in[ií]cio", d):
        m = re.search(r"(\d{1,2})/(\d{1,2})", d)
        if m:
            return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}"
    v = str(veic).lower()
    m = re.search(r"(\d{1,2})/(\d{1,2})", v)
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}"
    achados = [(v.find(n), num) for n, num in MESES.items() if n in v]
    if achados:
        return f"01/{min(achados)[1]:02d}"
    return ""


def data_curta(txt):
    m = re.search(r"(\d{1,2})/(\d{1,2})", str(txt))
    if not m or not 1 <= int(m.group(2)) <= 12:
        return str(txt)
    return f"{int(m.group(1)):02d}/{MES_CURTO[int(m.group(2))]}"


@st.cache_data(ttl=300)
def carregar():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_RADIO}"
    bruto = pd.read_csv(url, header=None, dtype=str).fillna("")

    alvo = COLS["u"].strip().lower()
    linha = next(i for i, r in bruto.iterrows() if any(str(c).strip().lower() == alvo for c in r))
    cab = [str(c).strip() for c in bruto.iloc[linha]]
    pos = {}
    for chave, nome in COLS.items():
        if nome not in cab:
            raise ValueError(f"Coluna '{nome}' não encontrada na planilha.")
        pos[chave] = cab.index(nome)

    dados = []
    for _, r in bruto.iloc[linha + 1:].iterrows():
        g = {k: str(r.iloc[i]).strip() for k, i in pos.items()}
        if not g["u"] and not g["radio"]:
            continue
        st_norm = g["st"].lower()
        g["st"] = STATUS_TROCA.get(st_norm, g["st"])
        g["ini"] = inicio(g["veic"], g["det"])
        g["sol"] = data_curta(g["sol"])
        g["por"] = g["por"].split(" ")[0] if g["por"] else ""
        letras = re.findall(r"[A-Za-zÀ-ú]", g["mr"])
        g["mr"] = letras[0].upper() if letras else ""
        g["t"] = g["t"].upper().replace(" ", "")
        g["tim"] = ""
        dados.append(g)

    atualizado = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    return dados, atualizado


def montar_status(dados):
    status = [list(s) for s in STATUS_BASE]
    conhecidos = {s for s, _ in status}
    novos = sorted({d["st"] for d in dados} - conhecidos)
    for i, s in enumerate(novos):
        status.insert(-3, [s, CORES_EXTRAS[i % len(CORES_EXTRAS)]])
    usados = {d["st"] for d in dados} | {"Veiculando"}
    return [s for s in status if s[0] in usados]


def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ------------------------------------------------------------------
# PÁGINA
# ------------------------------------------------------------------
st.markdown(
    """<style>
    header[data-testid="stHeader"], footer, #MainMenu {display:none;}
    .block-container {padding: 0 !important; max-width: 100% !important;}
    iframe {display:block;}
    </style>""",
    unsafe_allow_html=True,
)

try:
    dados, atualizado = carregar()
except Exception as erro:
    st.error(f"Não foi possível ler a planilha: {erro}. Confira se ela está compartilhada como "
             "'Qualquer pessoa com o link' e se os cabeçalhos não mudaram.")
    st.stop()

modelo = (Path(__file__).parent / "painel.html").read_text(encoding="utf-8")
pagina = (modelo
          .replace("__DATA__", js(dados))
          .replace("__STATUS__", js(montar_status(dados)))
          .replace("__ATUALIZADO__", atualizado))

components.html(pagina, height=ALTURA_PAINEL, scrolling=True)
