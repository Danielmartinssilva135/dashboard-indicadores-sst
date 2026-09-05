import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de SST - Indicadores", layout="wide")

st.title("🦺 Painel de Gestão e Indicadores de SST")
st.caption("Cálculo automatizado de TF, TG (NBR 14280) e Análise de Ocorrências")

# 1. Função para carregar dados de demonstração caso o usuário não envie arquivo
@st.cache_data
def carregar_dados_exemplo():
    dados_acidentes = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-15", "2024-02-10", "2024-03-05", "2024-03-22", "2024-04-12"]),
        "Setor": ["Produção", "Manutenção", "Logística", "Produção", "Operações"],
        "Tipo": ["Com Afastamento", "Sem Afastamento", "Com Afastamento", "Quase-Acidente", "Com Afastamento"],
        "Dias_Perdidos": [12, 0, 5, 0, 8],
        "Parte_Corpo": ["Mãos/Dedos", "Olhos", "Pés/Tornozelo", "Nenhum", "Braço"],
        "Agente": ["Máquina Puncionadeira", "Partícula Volante", "Paleteira Manual", "Piso Escorregadio", "Tubulação"]
    })
    
    dados_hht = pd.DataFrame({
        "Mes_Ano": ["2024-01", "2024-02", "2024-03", "2024-04"],
        "HHT": [52000, 48000, 51000, 50000]
    })
    return dados_acidentes, dados_hht

# 2. Barra Lateral: Upload de Dados e Filtros
st.sidebar.header("📁 Entrada de Dados")
upload_arquivo = st.sidebar.file_uploader("Suba sua planilha (.xlsx com abas 'Acidentes' e 'HHT')", type=["xlsx"])

if upload_arquivo:
    df_acidentes = pd.read_excel(upload_arquivo, sheet_name="Acidentes")
    df_acidentes["Data"] = pd.to_datetime(df_acidentes["Data"])
    df_hht = pd.read_excel(upload_arquivo, sheet_name="HHT")
else:
    st.sidebar.info("Exibindo dados de exemplo. Envie uma planilha para analisar seus próprios dados.")
    df_acidentes, df_hht = carregar_dados_exemplo()

# Filtro por Setor
setores = ["Todos"] + sorted(df_acidentes["Setor"].unique().tolist())
setor_selecionado = st.sidebar.selectbox("Filtrar por Setor:", setores)

if setor_selecionado != "Todos":
    df_filtrado = df_acidentes[df_acidentes["Setor"] == setor_selecionado]
else:
    df_filtrado = df_acidentes

# 3. Cálculos Normativos (NBR 14280)
total_hht = df_hht["HHT"].sum()
total_com_afastamento = len(df_filtrado[df_filtrado["Tipo"] == "Com Afastamento"])
total_sem_afastamento = len(df_filtrado[df_filtrado["Tipo"] == "Sem Afastamento"])
total_dias_perdidos = df_filtrado["Dias_Perdidos"].sum()

# Fórmulas: TF = (N / HHT) * 1.000.000 | TG = (Dias / HHT) * 1.000.000
taxa_frequencia = (total_com_afastamento * 1_000_000) / total_hht if total_hht > 0 else 0
taxa_gravidade = (total_dias_perdidos * 1_000_000) / total_hht if total_hht > 0 else 0

# 4. Cartões de Métricas (KPIs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Taxa de Frequência (TF)", f"{taxa_frequencia:.2f}", help="NBR 14280: Acidentes CPT x 1.000.000 / HHT")
col2.metric("Taxa de Gravidade (TG)", f"{taxa_gravidade:.2f}", help="NBR 14280: Dias Perdidos x 1.000.000 / HHT")
col3.metric("Acidentes com Afastamento", total_com_afastamento)
col4.metric("Total Dias Perdidos", int(total_dias_perdidos))

st.divider()

# 5. Gráficos Analíticos
graf_col1, graf_col2 = st.columns(2)

with graf_col1:
    fig_setores = px.bar(
        df_filtrado["Setor"].value_counts().reset_index(),
        x="Setor",
        y="count",
        title="Ocorrências por Setor",
        labels={"count": "Qtd Ocorrências", "Setor": "Setor"},
        color="count",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig_setores, use_container_width=True)

with graf_col2:
    fig_corpo = px.pie(
        df_filtrado[df_filtrado["Parte_Corpo"] != "Nenhum"],
        names="Parte_Corpo",
        title="Partes do Corpo Mais Atingidas",
        hole=0.4
    )
    st.plotly_chart(fig_corpo, use_container_width=True)

# 6. Tabela Detalhada com Opção de Download
st.subheader("📋 Registro Detalhado das Ocorrências")
st.dataframe(df_filtrado, use_container_width=True)