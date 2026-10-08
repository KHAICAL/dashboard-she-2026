import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard SHE 2026", layout="wide")

@st.cache_data(ttl=60)
def carregar_dados():
    # Link direto para a exportação CSV do seu Google Sheets (aba Dashboard)
    url_planilha = "https://docs.google.com/spreadsheets/d/11_mLLdGgClBaKvRH9VPHWbm4qw3go66MTwK-dPAzjj0/export?format=csv&gid=687500882"
    df = pd.read_csv(url_planilha, skiprows=2) 
    return df

df = carregar_dados()

st.title("📊 Painel Operacional de Mídia | Campanha SHE 2026")

st.write("Verificação de ligação - Dados em tempo real da folha de cálculo:")
st.dataframe(df)
