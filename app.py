import io
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Dashboard de SST - Indicadores",
    page_icon="🦺",
    layout="wide"
)

st.title("🦺 Painel de Gestão e Indicadores de SST")
st.caption("Cálculo automatizado de TF, TG (NBR 14280) e Análise de Ocorrências")

# 1. Função para gerar a planilha modelo .xlsx em memória para download imediato
@st.cache_data
def gerar_planilha_modelo():
    df_exemplo_acidentes = pd.DataFrame({
        "Data": ["2024-01-15", "2024-02-10", "2024-03-05", "2024-03-22", "2024-04-12", "2024-05-18", "2024-06-02"],
        "Setor": ["Produção", "Manutenção", "Logística", "Produção", "Operações", "Usinagem", "Almoxarifado"],
        "Tipo": ["Com Afastamento", "Sem Afastamento", "Com Afastamento", "Quase-Acidente", "Com Afastamento", "Sem Afastamento", "Quase-Acidente"],
        "Dias_Perdidos": [12, 0, 5, 0, 8, 0, 0],
        "Parte_Corpo": ["Mãos/Dedos", "Olhos", "Pés/Tornozelo", "Nenhum", "Braço", "Mãos/Dedos", "Nenhum"],
        "Agente": ["Máquina Puncionadeira", "Partícula Volante", "Paleteira Manual", "Piso Escorregadio", "Tubulação", "Rebarba Metálica", "Queda de Caixa"]
    })

    df_exemplo_hht = pd.DataFrame({
        "Mes_Ano": ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"],
        "HHT": [52000, 48000, 51000, 50000, 53000, 49500]
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_exemplo_acidentes.to_excel(writer, sheet_name="Acidentes", index=False)
        df_exemplo_hht.to_excel(writer, sheet_name="HHT", index=False)
    buffer.seek(0)
    return buffer

# 2. Barra Lateral: Instruções e Download do Modelo
st.sidebar.header("📥 1. Baixar Modelo")
st.sidebar.write("Baixe a planilha padrão, preencha com os dados da sua empresa e envie abaixo:")

planilha_modelo_bytes = gerar_planilha_modelo()
st.sidebar.download_button(
    label="⬇️ Baixar Planilha Modelo (.xlsx)",
    data=planilha_modelo_bytes,
    file_name="modelo_indicadores_sst.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.sidebar.divider()

# 3. Barra Lateral: Upload do Usuário
st.sidebar.header("📁 2. Enviar seus Dados")
upload_arquivo = st.sidebar.file_uploader("Envie a planilha preenchida (.xlsx)", type=["xlsx"])

if upload_arquivo:
    try:
        df_acidentes = pd.read_excel(upload_arquivo, sheet_name="Acidentes")
        df_acidentes["Data"] = pd.to_datetime(df_acidentes["Data"])
        df_hht = pd.read_excel(upload_arquivo, sheet_name="HHT")
        st.sidebar.success("✅ Dados carregados com sucesso!")
    except Exception as e:
        st.sidebar.error("❌ Erro ao ler o arquivo. Certifique-se de manter as abas 'Acidentes' e 'HHT' conforme o modelo.")
        st.stop()
else:
    st.sidebar.info("💡 Exibindo dados de demonstração. Baixe o modelo acima para analisar a realidade da sua empresa.")
    modelo_buffer = gerar_planilha_modelo()
    df_acidentes = pd.read_excel(modelo_buffer, sheet_name="Acidentes")
    df_acidentes["Data"] = pd.to_datetime(df_acidentes["Data"])
    df_hht = pd.read_excel(modelo_buffer, sheet_name="HHT")

st.sidebar.divider()

# 4. Filtro por Setor
st.sidebar.header("🔍 Filtros")
lista_setores = ["Todos"] + sorted(df_acidentes["Setor"].dropna().unique().tolist())
setor_selecionado = st.sidebar.selectbox("Filtrar por Setor:", lista_setores)

if setor_selecionado != "Todos":
    df_filtrado = df_acidentes[df_acidentes["Setor"] == setor_selecionado]
else:
    df_filtrado = df_acidentes

# 5. Cálculos Normativos (NBR 14280)
total_hht = df_hht["HHT"].sum()
total_com_afastamento = len(df_filtrado[df_filtrado["Tipo"] == "Com Afastamento"])
total_sem_afastamento = len(df_filtrado[df_filtrado["Tipo"] == "Sem Afastamento"])
total_quase_acidente = len(df_filtrado[df_filtrado["Tipo"] == "Quase-Acidente"])
total_dias_perdidos = df_filtrado["Dias_Perdidos"].sum()

# Fórmulas: TF = (N / HHT) * 1.000.000  |  TG = (Dias / HHT) * 1.000.000
taxa_frequencia = (total_com_afastamento * 1_000_000) / total_hht if total_hht > 0 else 0
taxa_gravidade = (total_dias_perdidos * 1_000_000) / total_hht if total_hht > 0 else 0

# 6. Cartões de Métricas Principais (KPIs)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Taxa Frequência (TF)", f"{taxa_frequencia:.2f}", help="NBR 14280: (Acidentes CPT x 1.000.000) / HHT")
col2.metric("Taxa Gravidade (TG)", f"{taxa_gravidade:.2f}", help="NBR 14280: (Dias Perdidos x 1.000.000) / HHT")
col3.metric("Com Afastamento", total_com_afastamento)
col4.metric("Sem Afastamento", total_sem_afastamento)
col5.metric("Dias Perdidos", int(total_dias_perdidos))

st.divider()

# 7. Gráficos Analíticos
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
    dados_corpo = df_filtrado[df_filtrado["Parte_Corpo"] != "Nenhum"]
    if not dados_corpo.empty:
        fig_corpo = px.pie(
            dados_corpo,
            names="Parte_Corpo",
            title="Partes do Corpo Mais Atingidas",
            hole=0.4
        )
        st.plotly_chart(fig_corpo, use_container_width=True)
    else:
        st.info("Nenhuma lesão com parte do corpo registrada no filtro atual.")

# 8. Tabela de Registros
st.subheader("📋 Registro Detalhado das Ocorrências")
df_exibicao = df_filtrado.copy()
df_exibicao["Data"] = df_exibicao["Data"].dt.strftime("%d/%m/%Y")
st.dataframe(df_exibicao, use_container_width=True)
