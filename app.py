import io
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Dashboard Inteligente de SST",
    page_icon="🦺",
    layout="wide"
)

st.title("🦺 Painel Dinâmico de Indicadores de SST")
st.caption("Auto-ajustável para qualquer formato de planilha com cálculos da NBR 14280")

# 1. Planilha modelo base
@st.cache_data
def gerar_planilha_modelo():
    df_exemplo_acidentes = pd.DataFrame({
        "Data": ["2024-01-15", "2024-02-10", "2024-03-05", "2024-03-22", "2024-04-12", "2024-05-18"],
        "Setor": ["Produção", "Manutenção", "Logística", "Produção", "Operações", "Usinagem"],
        "Tipo": ["Com Afastamento", "Sem Afastamento", "Com Afastamento", "Quase-Acidente", "Com Afastamento", "Sem Afastamento"],
        "Dias_Perdidos": [12, 0, 5, 0, 8, 0],
        "Parte_Corpo": ["Mãos/Dedos", "Olhos", "Pés/Tornozelo", "Nenhum", "Braço", "Mãos/Dedos"],
        "Agente": ["Máquina Puncionadeira", "Partícula Volante", "Paleteira Manual", "Piso Escorregadio", "Tubulação", "Rebarba Metálica"],
        "Turno": ["1º Turno", "2º Turno", "1º Turno", "3º Turno", "1º Turno", "2º Turno"]
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

# 2. Barra Lateral: Download e Upload
st.sidebar.header("📥 1. Baixar Modelo Base")
st.sidebar.download_button(
    label="⬇️ Baixar Planilha Modelo (.xlsx)",
    data=gerar_planilha_modelo(),
    file_name="modelo_indicadores_sst.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.sidebar.divider()
st.sidebar.header("📁 2. Enviar Dados")
upload_arquivo = st.sidebar.file_uploader("Suba sua planilha (.xlsx)", type=["xlsx"])

if upload_arquivo:
    try:
        df_acidentes = pd.read_excel(upload_arquivo, sheet_name="Acidentes")
        df_hht = pd.read_excel(upload_arquivo, sheet_name="HHT")
        st.sidebar.success("✅ Planilha carregada e adaptada!")
    except Exception:
        st.sidebar.error("❌ A planilha precisa ter as abas 'Acidentes' e 'HHT'.")
        st.stop()
else:
    st.sidebar.info("💡 Exibindo dados de exemplo. Adicione quantas colunas quiser na sua planilha!")
    modelo_buffer = gerar_planilha_modelo()
    df_acidentes = pd.read_excel(modelo_buffer, sheet_name="Acidentes")
    df_hht = pd.read_excel(modelo_buffer, sheet_name="HHT")

# Padronização de datas se houver coluna Data
if "Data" in df_acidentes.columns:
    df_acidentes["Data"] = pd.to_datetime(df_acidentes["Data"], errors="coerce")

# 3. FILTROS DINÂMICOS NA BARRA LATERAL
st.sidebar.divider()
st.sidebar.header("🔍 Filtros Dinâmicos")

df_filtrado = df_acidentes.copy()

# Identifica automaticamente colunas categóricas (texto) para criar filtros
colunas_categoricas = [c for c in df_acidentes.columns if df_acidentes[c].dtype == 'object' and c not in ["Data"]]

filtros_selecionados = {}
for col in colunas_categoricas:
    valores_unicos = ["Todos"] + sorted([str(v) for v in df_acidentes[col].dropna().unique().tolist()])
    escolha = st.sidebar.selectbox(f"Filtrar por {col}:", valores_unicos, key=f"filtro_{col}")
    if escolha != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col].astype(str) == escolha]

# 4. CARTÕES DE MÉTRICAS (KPIs)
total_hht = df_hht["HHT"].sum() if "HHT" in df_hht.columns else 0
total_ocorrencias = len(df_filtrado)

# Verificação segura de colunas para cálculo
if "Tipo" in df_filtrado.columns:
    total_com_afastamento = len(df_filtrado[df_filtrado["Tipo"].str.contains("Com Afastamento|CPT", case=False, na=False)])
    total_sem_afastamento = len(df_filtrado[df_filtrado["Tipo"].str.contains("Sem Afastamento|SPT", case=False, na=False)])
else:
    total_com_afastamento = 0
    total_sem_afastamento = 0

total_dias_perdidos = df_filtrado["Dias_Perdidos"].sum() if "Dias_Perdidos" in df_filtrado.columns else 0

taxa_frequencia = (total_com_afastamento * 1_000_000) / total_hht if total_hht > 0 else 0
taxa_gravidade = (total_dias_perdidos * 1_000_000) / total_hht if total_hht > 0 else 0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Taxa Frequência (TF)", f"{taxa_frequencia:.2f}")
kpi2.metric("Taxa Gravidade (TG)", f"{taxa_gravidade:.2f}")
kpi3.metric("Total Ocorrências", total_ocorrencias)
kpi4.metric("Com Afastamento", total_com_afastamento)
kpi5.metric("Dias Perdidos", int(total_dias_perdidos))

st.divider()

# 5. EVOLUÇÃO TEMPORAL AUTOMÁTICA (Se houver Data)
if "Data" in df_filtrado.columns and df_filtrado["Data"].notna().any():
    df_tempo = df_filtrado.dropna(subset=["Data"]).copy()
    df_tempo["Ano_Mes"] = df_tempo["Data"].dt.to_period("M").astype(str)
    contagem_tempo = df_tempo.groupby("Ano_Mes").size().reset_index(name="Quantidade")
    
    fig_linha = px.line(
        contagem_tempo, x="Ano_Mes", y="Quantidade",
        markers=True,
        title="📈 Evolução Mensal das Ocorrências",
        labels={"Ano_Mes": "Mês/Ano", "Quantidade": "Total Ocorrências"}
    )
    st.plotly_chart(fig_linha, use_container_width=True)

# 6. GRÁFICOS DINÂMICOS (Gera automaticamente para QUALQUER coluna de texto)
st.subheader("📊 Análises Estratégicas")

# Pega até 4 colunas categóricas para gerar gráficos em pares
colunas_graficos = [c for c in colunas_categoricas if c not in ["Tipo"]]

if colunas_graficos:
    for i in range(0, len(colunas_graficos), 2):
        g1, g2 = st.columns(2)
        
        col_atual_1 = colunas_graficos[i]
        with g1:
            dados_1 = df_filtrado[col_atual_1].value_counts().reset_index()
            dados_1.columns = [col_atual_1, "Qtd"]
            fig1 = px.bar(dados_1, x=col_atual_1, y="Qtd", title=f"Distribuição por {col_atual_1}", color="Qtd", color_continuous_scale="Blues")
            st.plotly_chart(fig1, use_container_width=True)
            
        if i + 1 < len(colunas_graficos):
            col_atual_2 = colunas_graficos[i + 1]
            with g2:
                dados_2 = df_filtrado[col_atual_2].value_counts().reset_index()
                dados_2.columns = [col_atual_2, "Qtd"]
                fig2 = px.pie(dados_2, names=col_atual_2, values="Qtd", title=f"Proporção por {col_atual_2}", hole=0.35)
                st.plotly_chart(fig2, use_container_width=True)

# 7. Tabela de Registros
st.subheader("📋 Base de Dados Completa")
df_tabela = df_filtrado.copy()
if "Data" in df_tabela.columns:
    df_tabela["Data"] = df_tabela["Data"].dt.strftime("%d/%m/%Y")
st.dataframe(df_tabela, use_container_width=True)
