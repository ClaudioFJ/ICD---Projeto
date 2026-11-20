"""Data app — Desigualdade, diversidade e saneamento na RMSP (Censo 2022).

Parte 2 do projeto de Introdução à Ciência de Dados (Tema 2).
Executar com:  streamlit run app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modelo import cenario, montar_X, treinar
from indicadores import (INDICADORES, SM_2022, SUBREGIOES, calcular_indicadores,
                         resumo, validar_base)

PASTA = Path(__file__).parent
ARQ_DADOS = PASTA / "data" / "rmsp_censo2022_tratado.csv"
ARQ_GEO = PASTA / "data" / "rmsp_municipios.geojson"
ARQ_RESULTADOS = PASTA / "data" / "resultados_modelo.json"  # gerados no notebook da Parte 3
ARQ_PREVISOES = PASTA / "data" / "rmsp_previsoes.csv"
ARQ_BRASIL = PASTA / "data" / "brasil_modelagem.csv"

# Cores fixas por sub-região: a cor acompanha a sub-região, nunca a posição,
# então filtrar não repinta as que sobram.
CORES_SUB = {"Capital": "#2e6aa8", "Norte": "#1b7f4c", "Leste": "#c58a00",
             "Sudeste": "#c0504d", "Sudoeste": "#7b5ea7", "Oeste": "#2a9db5"}
SIMBOLOS_SUB = {"Capital": "circle", "Norte": "square", "Leste": "diamond",
                "Sudeste": "triangle-up", "Sudoeste": "cross", "Oeste": "star"}
# Paleta institucional (validada para daltonismo nos pares adjacentes)
MARINHO, VERDE, AZUL = "#0f2c4c", "#1b7f4c", "#2e6aa8"
OCRE, TERRACOTA = "#c58a00", "#c0504d"
RAMPA_VERDE = ["#e3f1e8", "#bfe0cb", "#8fc9a6", "#5aad7f", "#2e8f5e", "#1b6b40", "#0f4d2e"]
CINZA = "#e6eaef"
TEXTO = "#1a2433"
TEXTO_2 = "#56606e"

st.set_page_config(page_title="RMSP · Desigualdade e saneamento (Censo 2022)",
                   page_icon="📊", layout="wide")

# Ajustes visuais que o config.toml não cobre: filete verde sob o título e
# borda colorida à esquerda dos cartões de KPI.
st.markdown("""
<style>
h1 { border-bottom: 3px solid #1b7f4c; padding-bottom: .4rem !important; margin-bottom: .8rem !important; color: #0f2c4c; }
h2, h3 { color: #0f2c4c; }
div[data-testid="stMetric"] {
    border-left: 4px solid #1b7f4c !important; background: #f7f9fb; border-radius: 4px;
}
section[data-testid="stSidebar"] div[data-testid="stMetric"] {
    background: transparent; border-left-color: #4fbf85 !important;
}
button[data-baseweb="tab"] p { font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def br(valor: float, fmt: str) -> str:
    """Formata número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    s = fmt.format(valor)
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def layout_padrao(fig: go.Figure, altura: int = 420, **kw) -> go.Figure:
    fig.update_layout(
        height=altura, template="plotly_white", separators=",.",
        font=dict(family="Source Sans, Source Sans Pro, sans-serif", size=13, color=TEXTO),
        margin=dict(l=10, r=10, t=40, b=10), hoverlabel=dict(bgcolor="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None), **kw)
    fig.update_xaxes(gridcolor="#edf1f5", zeroline=False, linecolor="#c3ccd6")
    fig.update_yaxes(gridcolor="#edf1f5", zeroline=False)
    return fig


@st.cache_data
def carregar_base(conteudo: bytes | None) -> pd.DataFrame:
    """Lê a base tratada (arquivo do projeto ou CSV enviado) e calcula os indicadores."""
    if conteudo is None:
        base = pd.read_csv(ARQ_DADOS)
    else:
        from io import BytesIO
        base = pd.read_csv(BytesIO(conteudo))
    faltando = validar_base(base)
    if faltando:
        raise ValueError("Colunas ausentes: " + ", ".join(faltando))
    return calcular_indicadores(base)


@st.cache_data
def carregar_geojson() -> dict:
    return json.loads(ARQ_GEO.read_text(encoding="utf-8"))


@st.cache_data
def carregar_resultados() -> dict:
    return json.loads(ARQ_RESULTADOS.read_text(encoding="utf-8"))


@st.cache_data
def carregar_previsoes() -> pd.DataFrame:
    return pd.read_csv(ARQ_PREVISOES)


@st.cache_data
def carregar_brasil() -> pd.DataFrame:
    return pd.read_csv(ARQ_BRASIL)


@st.cache_resource(show_spinner="Treinando o modelo do simulador...")
def treinar_modelo():
    """Treina uma vez por sessão do servidor; o mesmo modelo é reaproveitado."""
    return treinar(carregar_brasil(), carregar_resultados())


# ----------------------------------------------------------------------------
# Barra lateral: fonte dos dados e filtros globais
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("Filtros")

    with st.expander("Fonte dos dados", expanded=False):
        st.caption("Por padrão o app usa a base tratada na Parte 1 "
                   "(`data/rmsp_censo2022_tratado.csv`). Envie outra versão do "
                   "mesmo arquivo para atualizar todos os números.")
        enviado = st.file_uploader("CSV tratado (opcional)", type="csv")

    try:
        ind = carregar_base(enviado.getvalue() if enviado else None)
        origem = f"arquivo enviado ({enviado.name})" if enviado else "base da Parte 1"
    except Exception as erro:  # base enviada fora do formato esperado
        st.error(f"Não foi possível usar o arquivo enviado. {erro}. Voltando à base padrão.")
        ind = carregar_base(None)
        origem = "base da Parte 1"

    sub_sel = st.multiselect(
        "Sub-regiões", options=SUBREGIOES, default=SUBREGIOES,
        help="Sub-regiões oficiais da RMSP (Lei Complementar Estadual 1.139/2011).")

    rmin, rmax = int(ind["renda_pc_mediana"].min()), int(ind["renda_pc_mediana"].max()) + 1
    faixa_renda = st.slider(
        "Renda mediana per capita (R$)", min_value=rmin, max_value=rmax,
        value=(rmin, rmax), step=10,
        help=f"Renda domiciliar per capita mediana de 2022. 1 salário mínimo = R$ {SM_2022:,}".replace(",", "."))

    filtro = ind[ind["sub_regiao"].isin(sub_sel)
                 & ind["renda_pc_mediana"].between(*faixa_renda)]

    st.divider()
    st.metric("Municípios na seleção", f"{len(filtro)} de {len(ind)}")
    st.caption(f"Fonte: {origem}. Censo Demográfico 2022 e PIB dos Municípios 2023 (IBGE).")

rmsp = resumo(ind)
sel = resumo(filtro)
selecao_completa = len(filtro) == len(ind)

# ----------------------------------------------------------------------------
# Cabeçalho
# ----------------------------------------------------------------------------
st.title("Desigualdade, diversidade e saneamento na Região Metropolitana de São Paulo")
st.markdown(
    "Painel interativo com os indicadores calculados na Parte 1 do projeto para os "
    "**39 municípios da RMSP**, a partir do **Censo Demográfico 2022** do IBGE. "
    "Use os filtros da barra lateral para recortar sub-regiões ou faixas de renda: "
    "os KPIs, os gráficos e a ficha do município são recalculados para a seleção.")

if filtro.empty:
    st.warning("Nenhum município atende aos filtros. Inclua ao menos uma sub-região ou amplie a faixa de renda.")
    st.stop()

aba_geral, aba_explorar, aba_muni, aba_modelo, aba_sobre = st.tabs(
    ["Visão geral", "Explorar indicadores", "Ficha do município",
     "Modelagem preditiva", "Sobre os dados"])


# ----------------------------------------------------------------------------
# Aba 1 — Visão geral (KPIs)
# ----------------------------------------------------------------------------
def kpi(coluna, rotulo, chave, fmt, pior_quando_maior, ajuda, sufixo_delta=""):
    valor = sel[chave]
    delta, cor = None, "off"
    if not selecao_completa:
        dif = valor - rmsp[chave]
        delta = br(dif, "{:+" + fmt[2:].replace("%", "")) + sufixo_delta + " vs. RMSP"
        if pior_quando_maior is not None:
            cor = "inverse" if pior_quando_maior else "normal"
    coluna.metric(rotulo, br(valor, fmt), delta=delta, delta_color=cor, help=ajuda, border=True)


with aba_geral:
    titulo = "RMSP completa" if selecao_completa else f"Seleção: {sel['municipios']} municípios"
    st.subheader(f"{titulo} · {br(sel['populacao_mi'], '{:.2f}')} milhões de habitantes")
    if not selecao_completa:
        st.caption("A seta indica a diferença em relação à RMSP inteira. Verde = situação melhor, "
                   "vermelho = pior. Composição racial não tem melhor ou pior, por isso fica em cinza.")

    st.markdown("**Renda e diversidade**")
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Renda mediana per capita", "renda_mediana_sm", "{:.2f}", False,
        "I2 · renda domiciliar per capita mediana em salários mínimos (média ponderada pela população).",
        " SM")
    kpi(c2, "Razão média/mediana da renda", "media_mediana", "{:.2f}", True,
        "I1 · quanto maior, mais a renda está concentrada no topo.")
    kpi(c3, "População negra", "pct_negra", "{:.1f}%", None,
        "I3 · pretos + pardos sobre a população total.", " p.p.")
    kpi(c4, "IVSA médio", "ivsa_medio", "{:.2f}", True,
        "I7 · índice de vulnerabilidade socioambiental (0 = melhor, 1 = pior município da RMSP).")

    st.markdown("**Saneamento e educação**")
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Domicílios com água da rede", "pct_agua_rede", "{:.1f}%", False,
        "I4 · rede geral como forma principal de abastecimento.", " p.p.")
    kpi(c2, "Domicílios com esgoto adequado", "pct_esgoto_adequado", "{:.1f}%", False,
        "I4 · rede geral ou fossa séptica.", " p.p.")
    parcela = 100 * sel["dom_esg_inadequado"] / rmsp["dom_esg_inadequado"]
    c3.metric("Domicílios com esgoto inadequado", br(sel["dom_esg_inadequado"], "{:,.0f}"),
              delta=None if selecao_completa else br(parcela, "{:.0f}") + "% do total da RMSP",
              delta_color="off", border=True,
              help="I4 · fossa rudimentar, vala, rio/córrego ou sem banheiro. Número absoluto, "
                   "por isso a comparação é a parcela do total da região.")
    kpi(c4, "Analfabetismo (15 anos ou mais)", "analfabetismo", "{:.2f}%", True,
        "I5 · 100 − taxa de alfabetização (média ponderada pela população).", " p.p.")

    st.divider()
    st.subheader("O que os dados mostram")
    a, b = st.columns(2)
    a.markdown(
        "**1. A renda é mais concentrada onde há mais renda.** Na capital, a renda média "
        "per capita (R$ 2.713) é o dobro da mediana (R$ 1.340). Nos demais municípios a "
        "mediana fica perto de 1 salário mínimo e a distribuição é mais homogênea.\n\n"
        "**2. Raça e território se sobrepõem.** Os municípios com mais de 57% de população "
        "negra (Francisco Morato, Itapevi, Itaquaquecetuba, Embu das Artes) têm renda "
        "mediana abaixo de R$ 1.000. É uma associação entre municípios, não entre pessoas.")
    b.markdown(
        "**3. O saneamento tem duas faces.** Em percentual, o pior déficit está nas áreas de "
        "mananciais: em Juquitiba, só cerca de 60% dos domicílios têm água da rede. Em números "
        "absolutos, dos cerca de 405 mil domicílios com esgoto inadequado, 157 mil estão na capital.\n\n"
        "**4. A riqueza produzida nem sempre fica com os moradores.** Em Cajamar, o PIB per "
        "capita é 15 vezes a renda anual de quem mora lá.")
    st.caption("Achados calculados com a RMSP completa (Parte 1). A aba **Explorar indicadores** "
               "permite verificar cada um deles na seleção atual.")


# ----------------------------------------------------------------------------
# Aba 2 — Explorar indicadores (mapa, ranking, dispersão, saneamento)
# ----------------------------------------------------------------------------
with aba_explorar:
    chave_ind = st.selectbox(
        "Indicador exibido no mapa e no ranking", options=list(INDICADORES),
        format_func=lambda k: INDICADORES[k]["nome"])
    meta = INDICADORES[chave_ind]
    st.caption(meta["desc"])
    leitura = {True: "Quanto maior, pior.", False: "Quanto maior, melhor.",
               None: "Indicador de composição: maior não é melhor nem pior."}[meta["pior_quando_maior"]]

    col_mapa, col_rank = st.columns([1.15, 1])

    # Mapa coroplético: todos os municípios em cinza ao fundo, seleção colorida
    geo = carregar_geojson()
    hover_vals = filtro[chave_ind].map(lambda v: br(v, meta["fmt"]))
    fig_mapa = go.Figure()
    fig_mapa.add_trace(go.Choroplethmap(
        geojson=geo, featureidkey="properties.cod_ibge", locations=ind["cod_ibge"],
        z=[0] * len(ind), colorscale=[[0, CINZA], [1, CINZA]], showscale=False,
        marker_line_color="white", marker_line_width=0.8, text=ind["municipio"],
        hovertemplate="%{text}<br>fora da seleção<extra></extra>"))
    fig_mapa.add_trace(go.Choroplethmap(
        geojson=geo, featureidkey="properties.cod_ibge", locations=filtro["cod_ibge"],
        z=filtro[chave_ind], colorscale=RAMPA_VERDE, marker_line_color="white",
        marker_line_width=0.8, customdata=list(zip(filtro["municipio"], filtro["sub_regiao"], hover_vals)),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                      + meta["nome"].split(" · ")[1] + ": %{customdata[2]}<extra></extra>",
        colorbar=dict(title=None, thickness=10, len=0.8)))
    # Fundo branco sem mapa-base: não depende de servidor de tiles externo
    layout_padrao(fig_mapa, altura=520)
    fig_mapa.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                           map=dict(style="white-bg", center=dict(lat=-23.62, lon=-46.62), zoom=7.9))
    col_mapa.markdown("**Mapa dos municípios**")
    col_mapa.plotly_chart(fig_mapa, width="stretch")
    col_mapa.caption(f"Tons mais escuros = valores maiores. {leitura} Cinza = fora da seleção.")

    # Ranking (barras horizontais, cor fixa por sub-região)
    rank = filtro.sort_values(chave_ind, ascending=True)
    fig_rank = go.Figure()
    for sub in SUBREGIOES:
        d = rank[rank["sub_regiao"] == sub]
        if d.empty:
            continue
        fig_rank.add_trace(go.Bar(
            x=d[chave_ind], y=d["municipio"], orientation="h", name=sub,
            marker=dict(color=CORES_SUB[sub], cornerradius=3),
            customdata=d[chave_ind].map(lambda v: br(v, meta["fmt"])),
            hovertemplate="<b>%{y}</b><br>%{customdata}<extra>" + sub + "</extra>"))
    layout_padrao(fig_rank, altura=max(360, 16 * len(rank) + 120), bargap=0.25)
    col_rank.markdown("**Ranking da seleção**")
    fig_rank.update_yaxes(categoryorder="array", categoryarray=rank["municipio"].tolist(),
                          tickfont=dict(size=11), gridcolor="rgba(0,0,0,0)", automargin=True)
    fig_rank.update_layout(margin=dict(l=150))
    col_rank.plotly_chart(fig_rank, width="stretch")

    st.divider()

    # Dispersão raça × renda
    st.subheader("Raça e renda no território")
    fig_disp = go.Figure()
    for sub in SUBREGIOES:
        d = filtro[filtro["sub_regiao"] == sub]
        if d.empty:
            continue
        fig_disp.add_trace(go.Scatter(
            x=d["I3_pct_negra"], y=d["renda_pc_mediana"], mode="markers", name=sub,
            marker=dict(color=CORES_SUB[sub], symbol=SIMBOLOS_SUB[sub], opacity=0.85,
                        size=8 + 32 * (d["populacao_2022"] / ind["populacao_2022"].max()) ** 0.5,
                        line=dict(color="white", width=1.5)),
            customdata=list(zip(d["municipio"], d["populacao_2022"].map(lambda v: br(v, "{:,.0f}")))),
            hovertemplate="<b>%{customdata[0]}</b><br>População negra: %{x:.1f}%<br>"
                          "Renda mediana: R$ %{y:,.0f}<br>Habitantes: %{customdata[1]}<extra>"
                          + sub + "</extra>"))
    fig_disp.add_hline(y=SM_2022, line_dash="dot", line_color=TEXTO_2,
                       annotation_text="1 salário mínimo", annotation_position="top left",
                       annotation_font_color=TEXTO_2)
    layout_padrao(fig_disp, altura=460)
    fig_disp.update_xaxes(title="% população negra (pretos + pardos)", ticksuffix="%")
    fig_disp.update_yaxes(title="Renda domiciliar per capita mediana (R$)", tickprefix="R$ ")
    c_graf, c_txt = st.columns([2.2, 1])
    c_graf.plotly_chart(fig_disp, width="stretch")
    with c_txt:
        if len(filtro) >= 5:
            # Spearman = correlação de Pearson entre os postos (ranks). Calculado assim
            # para não depender do scipy, que o pandas exige no method="spearman".
            rho = filtro["I3_pct_negra"].rank().corr(filtro["renda_pc_mediana"].rank())
            st.metric("Correlação de Spearman na seleção", br(rho, "{:+.2f}"),
                      help="Vai de −1 a +1. Negativa: onde há mais população negra, a renda mediana é menor.",
                      border=True)
        else:
            st.info("Selecione pelo menos 5 municípios para calcular a correlação.")
        st.markdown(
            "Cada marcador é um município; o tamanho é proporcional à população. "
            "Na RMSP completa a correlação é cerca de **−0,57**: municípios com maior "
            "proporção de população negra tendem a ter renda mediana menor.")
        st.caption("Associação entre municípios, não entre indivíduos (falácia ecológica). "
                   "A base não cruza renda com cor ou raça da pessoa.")

    st.divider()

    # Saneamento: percentual × absoluto
    st.subheader("As duas faces do déficit de saneamento")
    modo = st.radio(
        "Medir o déficit em", ["% dos domicílios", "Número de domicílios"], horizontal=True,
        help="Em percentual aparecem os municípios pequenos de mananciais; em números absolutos, a mancha urbana.")
    san = filtro.assign(
        sem_agua=filtro["dom_total"] - filtro["dom_agua_rede"],
        sem_esgoto=filtro["dom_esg_inadequado"],
        sem_lixo=filtro["dom_total"] - filtro["dom_lixo_coletado"])
    if modo == "% dos domicílios":
        for c in ["sem_agua", "sem_esgoto", "sem_lixo"]:
            san[c] = 100 * san[c] / san["dom_total"]
        ordem, fmt_san, eixo = "I4_deficit", "{:.1f}%", "% dos domicílios (componentes empilhados)"
    else:
        ordem, fmt_san, eixo = "sem_esgoto", "{:,.0f}", "domicílios (componentes empilhados)"
    top = san.nlargest(12, ordem).iloc[::-1]
    fig_san = go.Figure()
    for col, nome, cor in [("sem_agua", "Sem água da rede geral", AZUL),
                           ("sem_esgoto", "Esgoto inadequado", TERRACOTA),
                           ("sem_lixo", "Sem coleta de lixo", OCRE)]:
        fig_san.add_trace(go.Bar(
            x=top[col], y=top["municipio"], orientation="h", name=nome,
            marker=dict(color=cor, line=dict(color="white", width=2)),
            customdata=top[col].map(lambda v: br(v, fmt_san)),
            hovertemplate="<b>%{y}</b><br>" + nome + ": %{customdata}<extra></extra>"))
    layout_padrao(fig_san, altura=440, barmode="stack", bargap=0.25)
    fig_san.update_layout(legend_traceorder="normal")
    fig_san.update_xaxes(title=eixo)
    fig_san.update_yaxes(gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_san, width="stretch")
    st.caption("Até 12 municípios da seleção com maior déficit. Água fora da rede inclui poços, que nem "
               "sempre são inadequados; esgoto inadequado inclui fossa rudimentar, vala, rio ou córrego e "
               "domicílios sem banheiro.")

    st.download_button(
        "Baixar indicadores da seleção (CSV)",
        filtro.drop(columns=["log_populacao", "log_pib_pc"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name="rmsp_indicadores_selecao.csv", mime="text/csv")


# ----------------------------------------------------------------------------
# Aba 3 — Ficha do município
# ----------------------------------------------------------------------------
with aba_muni:
    nomes = sorted(filtro["municipio"])
    padrao = nomes.index("São Paulo") if "São Paulo" in nomes else 0
    nome = st.selectbox("Município", nomes, index=padrao,
                        help="A lista mostra apenas os municípios que passam nos filtros da barra lateral.")
    m = ind[ind["municipio"] == nome].iloc[0]
    pos = int(ind["I7_ivsa"].rank(ascending=False)[ind["municipio"] == nome].iloc[0])

    st.subheader(nome)
    st.markdown(f"Sub-região **{m['sub_regiao']}** · {br(m['populacao_2022'], '{:,.0f}')} habitantes "
                f"(2022) · porte {m['porte_pop']} · **{pos}º mais vulnerável** pelo IVSA entre os 39 municípios.")

    def kpi_muni(coluna, rotulo, valor, ref, fmt, pior_quando_maior, unidade=""):
        cor = "off" if pior_quando_maior is None else ("inverse" if pior_quando_maior else "normal")
        coluna.metric(rotulo, br(valor, fmt), delta=br(valor - ref, "{:+" + fmt[2:].replace("%", "")) + unidade + " vs. RMSP",
                      delta_color=cor, border=True)

    c = st.columns(4)
    kpi_muni(c[0], "Renda mediana per capita (SM)", m["I2_mediana_sm"], rmsp["renda_mediana_sm"], "{:.2f}", False)
    kpi_muni(c[1], "Razão média/mediana", m["I1_media_mediana"], rmsp["media_mediana"], "{:.2f}", True)
    kpi_muni(c[2], "População negra", m["I3_pct_negra"], rmsp["pct_negra"], "{:.1f}%", None, " p.p.")
    kpi_muni(c[3], "IVSA", m["I7_ivsa"], rmsp["ivsa_medio"], "{:.2f}", True)
    c = st.columns(4)
    kpi_muni(c[0], "Água da rede", m["pct_agua_rede"], rmsp["pct_agua_rede"], "{:.1f}%", False, " p.p.")
    kpi_muni(c[1], "Esgoto adequado", m["pct_esgoto_adequado"], rmsp["pct_esgoto_adequado"], "{:.1f}%", False, " p.p.")
    kpi_muni(c[2], "Analfabetismo 15+", m["I5_analfabetismo"], rmsp["analfabetismo"], "{:.2f}%", True, " p.p.")
    c[3].metric("PIB per capita ÷ renda anual", br(m["I6_pib_renda"], "{:.1f}×"),
                help="I6 · quantas vezes a riqueza produzida supera a renda dos moradores.", border=True)

    # Dimensões do IVSA: município × média da RMSP
    dims = {"dim_renda": "Renda", "dim_ambiente": "Saneamento", "dim_educacao": "Educação"}
    fig_dim = go.Figure()
    fig_dim.add_trace(go.Bar(
        x=list(dims.values()), y=[m[k] for k in dims], name=nome,
        marker=dict(color=VERDE, cornerradius=4),
        hovertemplate="%{x}: %{y:.2f}<extra>" + nome + "</extra>"))
    fig_dim.add_trace(go.Bar(
        x=list(dims.values()), y=[ind[k].mean() for k in dims], name="Média dos 39 municípios",
        marker=dict(color=AZUL, cornerradius=4),
        hovertemplate="%{x}: %{y:.2f}<extra>Média RMSP</extra>"))
    layout_padrao(fig_dim, altura=360, barmode="group", bargap=0.35, bargroupgap=0.08)
    fig_dim.update_yaxes(range=[0, 1.05])
    g1, g2 = st.columns([1.3, 1])
    g1.markdown("**Componentes do IVSA** (0 = melhor, 1 = pior da RMSP)")
    g1.plotly_chart(fig_dim, width="stretch")
    with g2:
        st.markdown("**Leitura**")
        pior = max(dims, key=lambda k: m[k] - ind[k].mean())
        st.markdown(f"A dimensão em que {nome} mais se afasta da média é **{dims[pior].lower()}** "
                    f"({br(m[pior], '{:.2f}')} contra {br(ind[pior].mean(), '{:.2f}')}).")
        st.markdown(f"- Domicílios com esgoto inadequado: **{br(m['dom_esg_inadequado'], '{:,.0f}')}**\n"
                    f"- Renda média per capita: **R$ {br(m['renda_pc_media'], '{:,.0f}')}**\n"
                    f"- Renda mediana per capita: **R$ {br(m['renda_pc_mediana'], '{:,.0f}')}**\n"
                    f"- PIB per capita 2023: **R$ {br(m['pib_pc_2023'], '{:,.0f}')}**")


# ----------------------------------------------------------------------------
# Aba 4 — Modelagem preditiva (Parte 3)
# ----------------------------------------------------------------------------
with aba_modelo:
    if not (ARQ_RESULTADOS.exists() and ARQ_PREVISOES.exists() and ARQ_BRASIL.exists()):
        st.info("Os resultados da Parte 3 ainda não estão na pasta `data/`. Rode o notebook "
                "`rmsp_parte3_modelagem.ipynb` e copie `resultados_modelo.json`, `rmsp_previsoes.csv` "
                "e `brasil_modelagem.csv` para cá.", icon="🛠️")
    else:
        info = carregar_resultados()
        metr = pd.DataFrame(info["metricas"]).set_index("modelo")
        escolhido = info["modelo_escolhido"]
        m_esc = metr.loc[escolhido]

        st.subheader("O saneamento da RMSP está onde o perfil dos municípios indica?")
        st.markdown(
            "Um modelo de regressão prevê o **% de domicílios com esgoto adequado** (rede geral ou fossa "
            "séptica) a partir do perfil do município: renda, alfabetização, porte, PIB, composição racial e "
            "estado. Como a RMSP tem só 39 municípios, o modelo foi treinado com os "
            f"**{br(info['n_total'], '{:,.0f}')} municípios do Brasil** e depois aplicado à região. A diferença entre o "
            "observado e o previsto mostra **quem está pior do que o seu perfil explica**.")

        st.markdown(f"Modelo escolhido: **{escolhido}**, o de menor erro médio na validação cruzada entre "
                    f"{len(metr) - 1} modelos testados (mais uma linha de base).")
        c = st.columns(4)
        c[0].metric("Municípios no treino e teste", br(info["n_total"], "{:,.0f}"), border=True,
                    help="Todos os municípios do Brasil com dados do Censo 2022.")
        c[1].metric("Erro médio no teste (MAE)", br(m_esc["MAE_teste"], "{:.1f}") + " p.p.",
                    delta=br(m_esc["MAE_teste"] - metr.loc["Linha de base (média)", "MAE_teste"], "{:+.1f}")
                    + " p.p. vs. prever a média", delta_color="inverse", border=True,
                    help=f"Avaliado em {info['n_teste']:,} municípios que o modelo não viu no treino.".replace(",", "."))
        c[2].metric("R² no teste", br(m_esc["R2_teste"], "{:.2f}"), border=True,
                    help="Fração da variação entre municípios explicada pelo modelo (0 a 1).")
        c[3].metric("Erro médio na RMSP", br(info["mae_oof_rmsp"], "{:.1f}") + " p.p.",
                    border=True, help="Média nos 39 municípios. Previsão fora da amostra: cada município foi previsto por um modelo "
                                      "que não o viu no treino.")

        with st.expander("Comparação dos modelos e como foram avaliados"):
            tab = metr[["MAE_cv", "R2_cv", "MAE_teste", "RMSE_teste", "R2_teste"]].copy()
            esp = pd.DataFrame(info["espacial"]).set_index("modelo")
            tab = tab.join(esp)
            st.dataframe(tab, width="stretch", column_config={
                "MAE_cv": st.column_config.NumberColumn("MAE validação", format="%.2f"),
                "R2_cv": st.column_config.NumberColumn("R² validação", format="%.2f"),
                "MAE_teste": st.column_config.NumberColumn("MAE teste", format="%.2f"),
                "RMSE_teste": st.column_config.NumberColumn("RMSE teste", format="%.2f"),
                "R2_teste": st.column_config.NumberColumn("R² teste", format="%.2f"),
                "MAE_uf_nova": st.column_config.NumberColumn("MAE estado novo", format="%.2f"),
                "R2_uf_nova": st.column_config.NumberColumn("R² estado novo", format="%.2f")})
            st.caption(
                f"Treino: {info['n_treino']:,} municípios, com validação cruzada de 5 partes para comparar "
                f"modelos e ajustar hiperparâmetros. Teste: {info['n_teste']:,} municípios separados no "
                "início e usados uma única vez. \"Estado novo\": validação agrupada por UF, em que o modelo "
                "prevê estados inteiros que não viu. O erro maior mostra que parte do saneamento depende de "
                "fatores estaduais.".replace(",", "."))

        st.divider()
        prev = carregar_previsoes()
        prev_sel = prev[prev["cod_ibge"].isin(filtro["cod_ibge"])]
        st.subheader("Déficit inesperado na seleção")
        abaixo = (prev_sel["residuo"] < 0).sum()
        k = st.columns(3)
        k[0].metric("Municípios abaixo do esperado", f"{abaixo} de {len(prev_sel)}", border=True)
        k[1].metric("Domicílios em déficit inesperado", br(prev_sel["dom_deficit_inesperado"].sum(), "{:,.0f}"),
                    border=True, help="Domicílios sem esgoto adequado além do que o modelo prevê para o perfil "
                                      "de cada município (soma só onde o observado está abaixo do previsto).")
        k[2].metric("Diferença média (observado − previsto)", br(prev_sel["residuo"].mean(), "{:+.1f}") + " p.p.",
                    border=True)

        g1, g2 = st.columns([1, 1.15])
        # Previsto x observado
        fig_po = go.Figure()
        fig_po.add_trace(go.Scatter(x=[55, 100], y=[55, 100], mode="lines", name="Observado = previsto",
                                    line=dict(color=TEXTO_2, dash="dot", width=1.5), hoverinfo="skip"))
        for sub in SUBREGIOES:
            d = prev_sel[prev_sel["sub_regiao"] == sub]
            if d.empty:
                continue
            fig_po.add_trace(go.Scatter(
                x=d["previsto"], y=d["pct_esgoto_adequado"], mode="markers", name=sub,
                marker=dict(color=CORES_SUB[sub], symbol=SIMBOLOS_SUB[sub], size=11,
                            line=dict(color="white", width=1.5)),
                customdata=list(zip(d["municipio"], d["residuo"].map(lambda v: br(v, "{:+.1f}")))),
                hovertemplate="<b>%{customdata[0]}</b><br>Previsto: %{x:.1f}%<br>Observado: %{y:.1f}%"
                              "<br>Diferença: %{customdata[1]} p.p.<extra>" + sub + "</extra>"))
        layout_padrao(fig_po, altura=460)
        fig_po.update_xaxes(title="Previsto pelo modelo (% esgoto adequado)", ticksuffix="%")
        fig_po.update_yaxes(title="Observado no Censo 2022", ticksuffix="%")
        g1.markdown("**Previsto × observado**")
        g1.plotly_chart(fig_po, width="stretch")
        g1.caption("Abaixo da linha pontilhada: o município tem menos esgoto adequado do que o perfil indica.")

        # Resíduos ordenados
        d = prev_sel.sort_values("residuo", ascending=False)
        fig_res = go.Figure(go.Bar(
            x=d["residuo"], y=d["municipio"], orientation="h",
            marker=dict(color=[TERRACOTA if v < 0 else VERDE for v in d["residuo"]], cornerradius=3),
            customdata=list(zip(d["pct_esgoto_adequado"], d["previsto"],
                                d["dom_deficit_inesperado"].map(lambda v: br(v, "{:,.0f}")))),
            hovertemplate="<b>%{y}</b><br>Observado: %{customdata[0]:.1f}%<br>Previsto: %{customdata[1]:.1f}%"
                          "<br>Diferença: %{x:+.1f} p.p.<br>Domicílios em déficit inesperado: %{customdata[2]}"
                          "<extra></extra>"))
        layout_padrao(fig_res, altura=max(360, 16 * len(d) + 80), bargap=0.25, showlegend=False)
        fig_res.update_xaxes(title="Observado − previsto (p.p.)")
        fig_res.update_yaxes(tickfont=dict(size=11), gridcolor="rgba(0,0,0,0)", automargin=True)
        fig_res.update_layout(margin=dict(l=150))
        g2.markdown("**Quem está abaixo do esperado** (terracota) **e acima** (verde)")
        g2.plotly_chart(fig_res, width="stretch")

        st.markdown(
            "**Leitura (RMSP completa).** Os maiores déficits inesperados estão nas franjas da metrópole (Santa Isabel, "
            "Mairiporã, Embu-Guaçu, Juquitiba, Pirapora do Bom Jesus), em áreas de mananciais e de expansão "
            "periurbana. Ali a renda e a escolaridade fariam esperar uma cobertura bem maior. Cotia e Santana de "
            "Parnaíba, municípios de renda alta, também ficam abaixo do esperado, provavelmente por causa dos "
            "condomínios e loteamentos fora da rede. São bons candidatos a priorização de investimento e a "
            "investigação das causas.")

        st.divider()
        st.subheader("O que mais pesa na previsão")
        imp = pd.DataFrame(info["importancia"]).sort_values("aumento_MAE")
        fig_imp = go.Figure(go.Bar(
            x=imp["aumento_MAE"], y=imp["variavel"], orientation="h",
            error_x=dict(type="data", array=imp["dp"], color=TEXTO_2, thickness=1),
            marker=dict(color=VERDE, cornerradius=3),
            hovertemplate="%{y}: +%{x:.2f} p.p. no erro<extra></extra>"))
        layout_padrao(fig_imp, altura=340, showlegend=False)
        fig_imp.update_xaxes(title="Quanto o erro médio (MAE) piora ao embaralhar a variável (p.p.)")
        fig_imp.update_yaxes(gridcolor="rgba(0,0,0,0)")
        i1, i2 = st.columns([1.4, 1])
        i1.plotly_chart(fig_imp, width="stretch")
        i2.markdown(
            "O **estado** é a variável mais importante: companhia de saneamento, investimento histórico e "
            "regulação variam de UF para UF. Em seguida vêm **alfabetização**, **renda** e **porte** do "
            "município. A composição racial pesa pouco *depois* que renda e escolaridade entram no modelo.")
        i2.caption("Importância por permutação, medida no conjunto de teste (10 repetições; a barra fina é "
                   "o desvio-padrão).")

        st.divider()
        st.subheader("Simulador de cenários")
        st.markdown(
            "Escolha um município e altere renda e alfabetização para ver como a previsão do modelo muda. "
            "**Atenção:** o modelo mede associação, não causa. O resultado indica o nível de saneamento de "
            "municípios brasileiros com aquele perfil, não o efeito garantido de uma política.")
        s1, s2 = st.columns([1, 1.3])
        with s1:
            nomes_sim = sorted(prev_sel["municipio"])
            nome_sim = st.selectbox("Município simulado", nomes_sim,
                                    index=nomes_sim.index("Juquitiba") if "Juquitiba" in nomes_sim else 0)
            var_renda = st.slider("Variação da renda per capita (%)", -30, 100, 20, step=5,
                                  help="Aplicada à renda média e à mediana (a concentração de renda não muda).")
            var_alfab = st.slider("Variação da alfabetização 15+ (p.p.)", 0.0, 5.0, 0.0, step=0.5, format="%.1f")
        modelo_sim, colunas_sim = treinar_modelo()
        brasil = carregar_brasil()
        linha = brasil[brasil["cod_ibge"] == prev_sel.loc[prev_sel["municipio"] == nome_sim, "cod_ibge"].iloc[0]].iloc[0]
        nova = cenario(linha, var_renda, var_alfab)
        X_atual = montar_X(pd.DataFrame([linha]), info["numericas"], colunas_sim)
        X_novo = montar_X(pd.DataFrame([nova]), info["numericas"], colunas_sim)
        p_atual = float(np.clip(modelo_sim.predict(X_atual)[0], 0, 100))
        p_novo = float(np.clip(modelo_sim.predict(X_novo)[0], 0, 100))
        with s2:
            r = st.columns(3)
            r[0].metric("Observado (2022)", br(linha["pct_esgoto_adequado"], "{:.1f}%"), border=True)
            r[1].metric("Previsto hoje", br(p_atual, "{:.1f}%"), border=True)
            r[2].metric("Previsto no cenário", br(p_novo, "{:.1f}%"),
                        delta=br(p_novo - p_atual, "{:+.1f}") + " p.p.", border=True)
            st.markdown(
                f"Renda mediana: R$ {br(linha['renda_pc_mediana'], '{:,.0f}')} → "
                f"**R$ {br(linha['renda_pc_mediana'] * (1 + var_renda / 100), '{:,.0f}')}**  ·  "
                f"Alfabetização: {br(linha['taxa_alfab_15m'], '{:.1f}')}% → "
                f"**{br(nova['taxa_alfab_15m'], '{:.1f}')}%**")
            st.caption("No simulador, o modelo é treinado com todos os municípios do Brasil, por isso a previsão "
                       "do perfil atual pode diferir um pouco da previsão fora da amostra usada nos gráficos "
                       "acima. Modelos de árvore não extrapolam: além da faixa de renda observada no Brasil, a "
                       "previsão para de mudar.")


# ----------------------------------------------------------------------------
# Aba 5 — Sobre os dados
# ----------------------------------------------------------------------------
with aba_sobre:
    st.subheader("Fonte dos dados")
    st.markdown(
        "Base municipal montada a partir de **tabelas oficiais do IBGE**: Censo Demográfico 2022, "
        "PIB dos Municípios 2023 e Estimativas de População. Todos os números podem ser conferidos "
        "no [SIDRA](https://sidra.ibge.gov.br/tabela) pelos códigos de tabela abaixo.")
    st.dataframe(pd.DataFrame({
        "Conteúdo": ["População, PIB per capita, renda média e mediana, cor ou raça, alfabetização",
                     "Domicílios por forma de abastecimento de água",
                     "Domicílios por tipo de esgotamento sanitário",
                     "Domicílios por destino do lixo"],
        "Tabelas SIDRA": ["4714, 6579, 5938, 10295, 9605, 9543", "6803", "6805", "6892"],
        "Arquivo de origem": [
            "github.com/caioapolonio/eleicoes-2026 (apenas colunas do IBGE)",
            "github.com/zxcortes/Saneamento-censo-2022-Analise_de_Dados",
            "github.com/zxcortes/Saneamento-censo-2022-Analise_de_Dados",
            "github.com/zxcortes/Saneamento-censo-2022-Analise_de_Dados"],
    }), hide_index=True, width="stretch")

    st.subheader("Pré-processamento (Parte 1)")
    st.markdown(
        "1. Seleção das variáveis do IBGE e descarte das colunas eleitorais.\n"
        "2. Conversão dos símbolos do SIDRA: `-` vira 0; `X`, `..` e `...` viram dado ausente.\n"
        "3. Junção das quatro fontes pelo código IBGE de 7 dígitos, com checagem 1:1.\n"
        "4. Recorte dos 39 municípios e das 6 sub-regiões oficiais da RMSP.\n"
        "5. Checagens de consistência (cor ou raça soma 100%, totais de domicílios iguais nas três tabelas).\n"
        "6. Variáveis categóricas derivadas (porte, faixa de renda, grupo racial majoritário).")

    st.subheader("Indicadores")
    st.dataframe(pd.DataFrame(
        [{"Indicador": v["nome"], "Como é calculado": v["desc"]} for v in INDICADORES.values()]),
        hide_index=True, width="stretch")
    st.caption("Os KPIs de grupos de municípios são ponderados pela população ou calculados sobre o total de "
               "domicílios. A normalização do IVSA usa sempre os 39 municípios, então o índice de um município "
               "não muda quando os filtros mudam.")

    st.subheader("Dados da seleção atual")
    colunas = ["municipio", "sub_regiao", "populacao_2022", "renda_pc_mediana", "I1_media_mediana",
               "I3_pct_negra", "pct_agua_rede", "pct_esgoto_adequado", "dom_esg_inadequado",
               "I5_analfabetismo", "I6_pib_renda", "I7_ivsa"]
    st.dataframe(
        filtro[colunas].sort_values("I7_ivsa", ascending=False), hide_index=True, width="stretch",
        column_config={
            "municipio": "Município", "sub_regiao": "Sub-região",
            "populacao_2022": st.column_config.NumberColumn("População", format="localized"),
            "renda_pc_mediana": st.column_config.NumberColumn("Renda mediana (R$)", format="%.0f"),
            "I1_media_mediana": st.column_config.NumberColumn("Média/mediana", format="%.2f"),
            "I3_pct_negra": st.column_config.NumberColumn("% negra", format="%.1f"),
            "pct_agua_rede": st.column_config.NumberColumn("% água rede", format="%.1f"),
            "pct_esgoto_adequado": st.column_config.NumberColumn("% esgoto adequado", format="%.1f"),
            "dom_esg_inadequado": st.column_config.NumberColumn("Dom. esgoto inadequado", format="localized"),
            "I5_analfabetismo": st.column_config.NumberColumn("% analfabetismo", format="%.2f"),
            "I6_pib_renda": st.column_config.NumberColumn("PIB/renda", format="%.1f"),
            "I7_ivsa": st.column_config.ProgressColumn("IVSA", min_value=0, max_value=1, format="%.2f"),
        })
