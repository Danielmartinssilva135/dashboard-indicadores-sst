import io
import streamlit as st
import pandas as pd
import plotly.graph_objects as px_go
import plotly.express as px

st.set_page_config(
    page_title="KPIs de SST - Gestão Executiva",
    page_icon="📊",
    layout="wide"
)

# Estilização CSS para transformar o Streamlit no layout limpo (Power BI Style)
st.markdown("""
<style>
    /* Fundo da aplicação */
    .stApp {
        background-color: #F4F6F9;
        color: #262730;
    }
    /* Estilo dos Cards de KPIs */
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -1px rgba(0,0,0,0.04);
        text-align: center;
        border: 1px solid #E2E8F0;
    }
    .kpi-title {
        color: #64748B;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        color: #0F172A;
        font-size: 28px;
        font-weight: 700;
    }
    /* Container dos gráficos */
    div[data-testid="stVerticalBlock"] > div:has(div.kpi-card) {
        gap: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 1. Gerador de Planilha Modelo
@st.cache_data
def gerar_planilha_modelo():
    df_exemplo_acidentes = pd.DataFrame({
        "Data": ["2025-01-15", "2025-02-10", "2025-02-20", "2025-03-05", "2025-04-12", "2025-05-18", "2025-06-02"],
        "Setor": ["Laminação", "Aciaria", "Qualidade", "Logística", "Laminação", "Aciaria", "Manutenção"],
        "Quantidade de eventos": [1, 1, 1, 1, 1, 1, 1],
        "Tipo": ["Acidente CAF", "Acidente SAF", "Acidente CAF", "Incidente", "Acidente CAF", "Desvio", "Acidente CAF"],
        "Dias_Perdidos": [120, 0, 150, 0, 120, 0, 200],
        "Parte_Corpo": ["Mãos/Dedos", "Olhos", "Pés/Tornozelo", "Nenhum", "Braço", "Nenhum", "Pernas"],
        "Agente": ["Prensa", "Partícula Volante", "Paleteira", "Piso Irregular", "Tubulação", "Sem EPI", "Guindaste"]
    })

    df_exemplo_hht = pd.DataFrame({
        "Mes_Ano": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"],
        "HHT": [400000, 450000, 450000, 550000, 500000, 600000]
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_exemplo_acidentes.to_excel(writer, sheet_name="Acidentes", index=False)
        df_exemplo_hht.to_excel(writer, sheet_name="HHT", index=False)
    buffer.seek(0)
    return buffer

# 2. Barra Lateral: Metas, Download e Upload
with st.sidebar:
    st.header("⚙️ Parâmetros & Metas")
    meta_tf = st.number_input("Meta TF (Taxa de Freq.)", min_value=0.0, value=2.0, step=0.1)
    meta_tg = st.number_input("Meta TG (Taxa de Grav.)", min_value=0.0, value=150.0, step=10.0)
    
    st.divider()
    st.subheader("📥 Arquivo Modelo")
    st.download_button(
        label="⬇️ Baixar Planilha Padrão",
        data=gerar_planilha_modelo(),
        file_name="modelo_indicadores_sst.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    st.subheader("📁 Upload de Dados")
    upload_arquivo = st.file_uploader("Suba sua planilha (.xlsx)", type=["xlsx"])

# 3. Leitura dos Dados
if upload_arquivo:
    try:
        df_acidentes = pd.read_excel(upload_arquivo, sheet_name="Acidentes")
        df_hht = pd.read_excel(upload_arquivo, sheet_name="HHT")
    except Exception:
        st.error("Erro na leitura das abas 'Acidentes' e 'HHT'. Verifique o arquivo.")
        st.stop()
else:
    buffer = gerar_planilha_modelo()
    df_acidentes = pd.read_excel(buffer, sheet_name="Acidentes")
    df_hht = pd.read_excel(buffer, sheet_name="HHT")

# Tratamento e suporte a eventos agrupados ou individuais
df_acidentes["Data"] = pd.to_datetime(df_acidentes["Data"], errors="coerce")
df_acidentes["Mes_Ano"] = df_acidentes["Data"].dt.strftime("%Y-%m")

col_qtd = next((c for c in ["Quantidade de eventos", "Quantidade", "Qtd", "Eventos"] if c in df_acidentes.columns), None)
if col_qtd:
    df_acidentes[col_qtd] = pd.to_numeric(df_acidentes[col_qtd], errors="coerce").fillna(1)
else:
    col_qtd = "_Qtd"
    df_acidentes[col_qtd] = 1

# 4. Cálculos Totais
total_hht = df_hht["HHT"].sum() if "HHT" in df_hht.columns else 0
cpt_mask = df_acidentes["Tipo"].astype(str).str.contains("Com Afastamento|CAF|CPT", case=False, na=False)
total_caf = int(df_acidentes[cpt_mask][col_qtd].sum())
total_dp = int(df_acidentes["Dias_Perdidos"].sum()) if "Dias_Perdidos" in df_acidentes.columns else 0

tf_geral = (total_caf * 1_000_000) / total_hht if total_hht > 0 else 0
tg_geral = (total_dp * 1_000_000) / total_hht if total_hht > 0 else 0

# Formatação visual abreviada para os KPIs de topo
def formata_numero(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} Mi"
    elif n >= 1_000:
        return f"{n/1_000:.1f} Mil"
    return str(int(n))

# 5. Linha de KPIs de Topo (Power BI Cards)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Horas Trabalhadas</div><div class="kpi-value">{formata_numero(total_hht)}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Acidentes CAF</div><div class="kpi-value">{total_caf}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Dias Perdidos</div><div class="kpi-value">{formata_numero(total_dp)}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Taxa de Frequência (TF)</div><div class="kpi-value">{tf_geral:.1f}</div></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Taxa de Gravidade (TG)</div><div class="kpi-value">{tg_geral:.0f}</div></div>', unsafe_allow_html=True)

st.write("")

# 6. Agrupamento Mensal para Gráficos e Tabela
df_mensal_acidentes = df_acidentes[cpt_mask].groupby("Mes_Ano").agg(
    CAF=(col_qtd, "sum"),
    DP=("Dias_Perdidos", "sum")
).reset_index()

df_mensal = pd.merge(df_hht, df_mensal_acidentes, on="Mes_Ano", how="left").fillna(0)
df_mensal = df_mensal.sort_values("Mes_Ano")

df_mensal["TF"] = (df_mensal["CAF"] * 1_000_000) / df_mensal["HHT"].replace(0, 1)
df_mensal["TG"] = (df_mensal["DP"] * 1_000_000) / df_mensal["HHT"].replace(0, 1)

# 7. Gráficos Centrais (Barras Verdes + Linha de Meta Laranja)
g_col1, g_col2 = st.columns(2)

with g_col1:
    fig_tf = px_go.Figure()
    fig_tf.add_trace(px_go.Bar(
        x=df_mensal["Mes_Ano"], y=df_mensal["TF"],
        name="Taxa de Frequência (TF)",
        marker_color="#2D4A3E",
        text=df_mensal["TF"].round(1),
        textposition="outside"
    ))
    fig_tf.add_trace(px_go.Scatter(
        x=df_mensal["Mes_Ano"], y=[meta_tf]*len(df_mensal),
        name="Meta (TF)",
        mode="lines",
        line=dict(color="#D97706", width=3)
    ))
    fig_tf.update_layout(
        title="<b>Taxa de Frequência (TF) e Meta (TF) por Mês/Ano</b>",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_tf, use_container_width=True)

with g_col2:
    fig_tg = px_go.Figure()
    fig_tg.add_trace(px_go.Bar(
        x=df_mensal["Mes_Ano"], y=df_mensal["TG"],
        name="Taxa de Gravidade (TG)",
        marker_color="#2D4A3E",
        text=df_mensal["TG"].round(0).astype(int),
        textposition="outside"
    ))
    fig_tg.add_trace(px_go.Scatter(
        x=df_mensal["Mes_Ano"], y=[meta_tg]*len(df_mensal),
        name="Meta (TG)",
        mode="lines",
        line=dict(color="#D97706", width=3)
    ))
    fig_tg.update_layout(
        title="<b>Taxa de Gravidade (TG) e Meta (TG) por Mês/Ano</b>",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_tg, use_container_width=True)

# 8. Linha Inferior: Tabela Resumo + Barras por Setor + Rosca de Tipos
inf1, inf2, inf3 = st.columns([1.2, 1.4, 1.2])

with inf1:
    st.markdown("**Resumo Mensal de Indicadores**")
    df_tabela_view = df_mensal[["Mes_Ano", "HHT", "CAF", "TF", "DP", "TG"]].copy()
    df_tabela_view["TF"] = df_tabela_view["TF"].round(1)
    df_tabela_view["TG"] = df_tabela_view["TG"].round(0).astype(int)
    st.dataframe(df_tabela_view, hide_index=True, use_container_width=True)

with inf2:
    col_depto = "Setor" if "Setor" in df_acidentes.columns else "Departamento"
    if col_depto in df_acidentes.columns:
        depto_data = df_acidentes.groupby(col_depto)[col_qtd].sum().reset_index()
        depto_data = depto_data.sort_values(col_qtd, ascending=True)
        fig_depto = px.bar(
            depto_data, y=col_depto, x=col_qtd,
            orientation='h',
            title=f"<b>Ocorrências por {col_depto}</b>",
            text=col_qtd,
            color_discrete_sequence=["#2D4A3E"]
        )
        fig_depto.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=45, b=20),
            xaxis_title=None, yaxis_title=None
        )
        st.plotly_chart(fig_depto, use_container_width=True)

with inf3:
    if "Tipo" in df_acidentes.columns:
        tipo_data = df_acidentes.groupby("Tipo")[col_qtd].sum().reset_index()
        fig_tipo = px.pie(
            tipo_data, names="Tipo", values=col_qtd,
            hole=0.55,
            title="<b>Ocorrências por Tipo</b>",
            color_discrete_sequence=["#2D4A3E", "#D97706", "#D9C3B0", "#64748B"]
        )
        fig_tipo.update_layout(
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=45, b=20),
            legend=dict(orientation="v", yanchor="middle", y=0.5)
        )
        st.plotly_chart(fig_tipo, use_container_width=True)
