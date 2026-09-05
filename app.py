import io
import streamlit as st
import pandas as pd
import plotly.graph_objects as px_go
import plotly.express as px

st.set_page_config(
    page_title="Dashboard de Acidentes / Quase-Acidentes",
    page_icon="🦺",
    layout="wide"
)

# Estilização CSS Clean Power BI
st.markdown("""
<style>
    .stApp {
        background-color: #F4F6F9;
        color: #1E293B;
    }
    .header-card {
        background-color: #FFFFFF;
        padding: 18px 24px;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 1px solid #E2E8F0;
        border-left: 6px solid #2D4A3E;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07);
    }
    .header-title {
        color: #0F172A !important;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin: 0;
        text-transform: uppercase;
    }
    .header-subtitle {
        color: #64748B !important;
        font-size: 13px;
        margin: 4px 0 0 0;
        font-weight: 500;
    }
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 14px 6px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07);
        text-align: center;
        border: 1px solid #E2E8F0;
    }
    .kpi-title {
        color: #64748B;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        color: #0F172A;
        font-size: 23px;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

# 1. Gerador da Planilha Modelo Base
@st.cache_data
def gerar_planilha_modelo():
    df_exemplo_acidentes = pd.DataFrame({
        "Data": ["2024-01-15", "2024-02-10", "2024-03-05", "2024-03-22", "2024-04-12", "2024-05-18", "2024-06-02"],
        "Setor": ["Produção", "Manutenção", "Logística", "Produção", "Operações", "Usinagem", "Almoxarifado"],
        "Quantidade de eventos": [2, 4, 7, 5, 9, 12, 8],
        "Tipo": ["Com Afastamento", "Sem Afastamento", "Com Afastamento", "Quase-Acidente", "Com Afastamento", "Sem Afastamento", "Quase-Acidente"],
        "Dias_Perdidos": [400, 2, 100, 3, 300, 10, 5],
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

# 2. Barra Lateral: Metas, Downloads e Upload
with st.sidebar:
    st.header("⚙️ Parâmetros & Metas")
    meta_tf = st.number_input("Meta TF (Taxa Freq.)", min_value=0.0, value=20.0, step=1.0)
    meta_tg = st.number_input("Meta TG (Taxa Grav.)", min_value=0.0, value=200.0, step=10.0)
    
    st.divider()
    st.subheader("📥 Planilha Modelo")
    st.download_button(
        label="⬇️ Baixar Planilha Padrão",
        data=gerar_planilha_modelo(),
        file_name="modelo_indicadores_sst.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    st.subheader("📁 Upload de Dados")
    upload_arquivo = st.file_uploader("Suba sua planilha (.xlsx)", type=["xlsx"])

# 3. Leitura e Preparação dos Dados
if upload_arquivo:
    try:
        df_acidentes = pd.read_excel(upload_arquivo, sheet_name="Acidentes")
        df_hht = pd.read_excel(upload_arquivo, sheet_name="HHT")
    except Exception:
        st.error("Erro ao ler as abas 'Acidentes' e 'HHT'. Verifique seu arquivo.")
        st.stop()
else:
    buffer = gerar_planilha_modelo()
    df_acidentes = pd.read_excel(buffer, sheet_name="Acidentes")
    df_hht = pd.read_excel(buffer, sheet_name="HHT")

# Tratamento de datas
df_acidentes["Data"] = pd.to_datetime(df_acidentes["Data"], errors="coerce")
df_acidentes["Mes_Ano"] = df_acidentes["Data"].dt.strftime("%Y-%m")

# Suporte à contagem agrupada ou individual
col_qtd = next((c for c in ["Quantidade de eventos", "Quantidade", "Qtd", "Eventos"] if c in df_acidentes.columns), None)
if col_qtd:
    df_acidentes[col_qtd] = pd.to_numeric(df_acidentes[col_qtd], errors="coerce").fillna(1)
else:
    col_qtd = "_Qtd"
    df_acidentes[col_qtd] = 1

if "Dias_Perdidos" not in df_acidentes.columns:
    df_acidentes["Dias_Perdidos"] = 0
else:
    df_acidentes["Dias_Perdidos"] = pd.to_numeric(df_acidentes["Dias_Perdidos"], errors="coerce").fillna(0)

# Classificação NBR 14280
cpt_mask = df_acidentes["Tipo"].astype(str).str.contains("Com Afastamento|CAF|CPT", case=False, na=False)
spt_mask = df_acidentes["Tipo"].astype(str).str.contains("Sem Afastamento|SAF|SPT", case=False, na=False)
outros_mask = ~cpt_mask & ~spt_mask

df_acidentes["Qtd_CAF"] = df_acidentes[col_qtd].where(cpt_mask, 0)
df_acidentes["Qtd_SAF"] = df_acidentes[col_qtd].where(spt_mask, 0)
df_acidentes["Qtd_Outros"] = df_acidentes[col_qtd].where(outros_mask, 0)

# 4. Métricas Gerais
total_hht = df_hht["HHT"].sum() if "HHT" in df_hht.columns else 0
total_eventos = int(df_acidentes[col_qtd].sum())
total_caf = int(df_acidentes["Qtd_CAF"].sum())
total_saf = int(df_acidentes["Qtd_SAF"].sum())
total_dp = int(df_acidentes["Dias_Perdidos"].sum())

tf_geral = (total_caf * 1_000_000) / total_hht if total_hht > 0 else 0
tg_geral = (total_dp * 1_000_000) / total_hht if total_hht > 0 else 0

def formata_numero(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} Mi"
    elif n >= 1_000:
        return f"{n/1_000:.1f} Mil"
    return str(int(n))

# 5. Banner de Título Superior (Card Branco Clean)
st.markdown("""
<div class="header-card">
    <div class="header-title">📊 DASHBOARD DE ACIDENTES / QUASE-ACIDENTES</div>
    <div class="header-subtitle">Indicadores de Desempenho em Saúde e Segurança do Trabalho • NBR 14280</div>
</div>
""", unsafe_allow_html=True)

# 6. Cards de Topo
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">HHT Total</div><div class="kpi-value">{formata_numero(total_hht)}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Eventos</div><div class="kpi-value">{total_eventos}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Acidentes CAF</div><div class="kpi-value">{total_caf}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Acidentes SAF</div><div class="kpi-value">{total_saf}</div></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Dias Perdidos</div><div class="kpi-value">{formata_numero(total_dp)}</div></div>', unsafe_allow_html=True)
with c6:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Taxa Freq. (TF)</div><div class="kpi-value">{tf_geral:.1f}</div></div>', unsafe_allow_html=True)
with c7:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Taxa Grav. (TG)</div><div class="kpi-value">{tg_geral:.0f}</div></div>', unsafe_allow_html=True)

st.write("")

# 7. Resumo Mensal
df_mensal_acidentes = df_acidentes.groupby("Mes_Ano").agg(
    CAF=("Qtd_CAF", "sum"),
    SAF=("Qtd_SAF", "sum"),
    Outros=("Qtd_Outros", "sum"),
    Total_Eventos=(col_qtd, "sum"),
    DP=("Dias_Perdidos", "sum")
).reset_index()

df_mensal = pd.merge(df_hht, df_mensal_acidentes, on="Mes_Ano", how="left").fillna(0)
df_mensal = df_mensal.sort_values("Mes_Ano")

df_mensal["TF"] = (df_mensal["CAF"] * 1_000_000) / df_mensal["HHT"].replace(0, 1)
df_mensal["TG"] = (df_mensal["DP"] * 1_000_000) / df_mensal["HHT"].replace(0, 1)

# 8. Gráficos Centrais
g_col1, g_col2 = st.columns(2)

with g_col1:
    fig_tf = px_go.Figure()
    fig_tf.add_trace(px_go.Bar(
        x=df_mensal["Mes_Ano"], y=df_mensal["TF"],
        name="Taxa de Frequência (TF)",
        marker_color="#2D4A3E",
        text=df_mensal["TF"].round(1),
        textposition="outside",
        textfont=dict(color="#0F172A", size=12)
    ))
    fig_tf.add_trace(px_go.Scatter(
        x=df_mensal["Mes_Ano"], y=[meta_tf]*len(df_mensal),
        name="Meta (TF)",
        mode="lines",
        line=dict(color="#D97706", width=3)
    ))
    fig_tf.update_layout(
        title="<b>Taxa de Frequência (TF) e Meta por Mês/Ano</b>",
        title_font=dict(color="#0F172A", size=15),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=20),
        xaxis=dict(tickfont=dict(color="#0F172A"), showgrid=False),
        yaxis=dict(tickfont=dict(color="#0F172A"), gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color="#0F172A"))
    )
    st.plotly_chart(fig_tf, use_container_width=True)

with g_col2:
    fig_tg = px_go.Figure()
    fig_tg.add_trace(px_go.Bar(
        x=df_mensal["Mes_Ano"], y=df_mensal["TG"],
        name="Taxa de Gravidade (TG)",
        marker_color="#2D4A3E",
        text=df_mensal["TG"].round(0).astype(int),
        textposition="outside",
        textfont=dict(color="#0F172A", size=12)
    ))
    fig_tg.add_trace(px_go.Scatter(
        x=df_mensal["Mes_Ano"], y=[meta_tg]*len(df_mensal),
        name="Meta (TG)",
        mode="lines",
        line=dict(color="#D97706", width=3)
    ))
    fig_tg.update_layout(
        title="<b>Taxa de Gravidade (TG) e Meta por Mês/Ano</b>",
        title_font=dict(color="#0F172A", size=15),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=45, b=20),
        xaxis=dict(tickfont=dict(color="#0F172A"), showgrid=False),
        yaxis=dict(tickfont=dict(color="#0F172A"), gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color="#0F172A"))
    )
    st.plotly_chart(fig_tg, use_container_width=True)

st.write("")

# 9. Tabela Mensal + Setores + Tipos
inf1, inf2, inf3 = st.columns([1.5, 1.3, 1.2])

with inf1:
    st.markdown("#### 📅 Resumo Mensal Consolidado")
    df_tabela_view = df_mensal[["Mes_Ano", "HHT", "CAF", "SAF", "Outros", "Total_Eventos", "TF", "DP", "TG"]].copy()
    df_tabela_view.columns = ["Mês/Ano", "HHT", "CAF", "SAF", "Outros", "Total", "TF", "DP", "TG"]
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
            title_font=dict(color="#0F172A"),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=45, b=20),
            xaxis=dict(tickfont=dict(color="#0F172A"), showgrid=True, gridcolor="#E2E8F0"),
            yaxis=dict(tickfont=dict(color="#0F172A")),
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
            color_discrete_sequence=["#2D4A3E", "#D97706", "#94A3B8", "#475569"]
        )
        fig_tipo.update_layout(
            title_font=dict(color="#0F172A"),
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=45, b=20),
            legend=dict(orientation="v", yanchor="middle", y=0.5, font=dict(color="#0F172A"))
        )
        st.plotly_chart(fig_tipo, use_container_width=True)

st.write("")

# 10. Partes do Corpo e Agentes Causadores
detalhe_col1, detalhe_col2 = st.columns(2)

with detalhe_col1:
    if "Parte_Corpo" in df_acidentes.columns:
        filtro_corpo = df_acidentes[~df_acidentes["Parte_Corpo"].astype(str).str.lower().isin(["nenhum", "nan", ""])]
        if not filtro_corpo.empty:
            dados_corpo = filtro_corpo.groupby("Parte_Corpo")[col_qtd].sum().reset_index()
            dados_corpo = dados_corpo.sort_values(col_qtd, ascending=True)
            fig_corpo = px.bar(
                dados_corpo, y="Parte_Corpo", x=col_qtd,
                orientation='h',
                title="<b>🩹 Partes do Corpo Mais Atingidas</b>",
                text=col_qtd,
                color_discrete_sequence=["#0284C7"]
            )
            fig_corpo.update_layout(
                title_font=dict(color="#0F172A"),
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                margin=dict(l=20, r=20, t=45, b=20),
                xaxis=dict(tickfont=dict(color="#0F172A"), showgrid=True, gridcolor="#E2E8F0"),
                yaxis=dict(tickfont=dict(color="#0F172A")),
                xaxis_title=None, yaxis_title=None
            )
            st.plotly_chart(fig_corpo, use_container_width=True)

with detalhe_col2:
    col_agente = next((c for c in ["Agente", "Agente Causador", "Agente_Causador", "Fonte_Lesao"] if c in df_acidentes.columns), None)
    if col_agente:
        filtro_agente = df_acidentes[~df_acidentes[col_agente].astype(str).str.lower().isin(["nenhum", "nan", ""])]
        if not filtro_agente.empty:
            dados_agente = filtro_agente.groupby(col_agente)[col_qtd].sum().reset_index()
            dados_agente = dados_agente.sort_values(col_qtd, ascending=True)
            fig_agente = px.bar(
                dados_agente, y=col_agente, x=col_qtd,
                orientation='h',
                title=f"<b>⚠️ Agentes Causadores Mais Ofensores</b>",
                text=col_qtd,
                color_discrete_sequence=["#DC2626"]
            )
            fig_agente.update_layout(
                title_font=dict(color="#0F172A"),
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                margin=dict(l=20, r=20, t=45, b=20),
                xaxis=dict(tickfont=dict(color="#0F172A"), showgrid=True, gridcolor="#E2E8F0"),
                yaxis=dict(tickfont=dict(color="#0F172A")),
                xaxis_title=None, yaxis_title=None
            )
            st.plotly_chart(fig_agente, use_container_width=True)
