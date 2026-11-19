"""Cálculo dos indicadores da Parte 1 (mesmas fórmulas do notebook).

Separado do app.py para que a Parte 3 (modelagem) possa reutilizar as mesmas
funções sem duplicar código.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SM_2022 = 1212  # salário mínimo de 2022 (referência do Censo)

SUBREGIOES = ["Capital", "Norte", "Leste", "Sudeste", "Sudoeste", "Oeste"]

# Colunas mínimas que a base tratada precisa ter (saída do notebook da Parte 1)
COLUNAS_OBRIGATORIAS = [
    "cod_ibge", "municipio", "sub_regiao", "populacao_2022", "pib_pc_2023",
    "renda_pc_media", "renda_pc_mediana", "pct_branca", "pct_preta", "pct_parda",
    "pct_amarela", "pct_indigena", "taxa_alfab_15m", "dom_total", "dom_agua_rede",
    "dom_esg_rede", "dom_esg_fossa_septica", "dom_esg_rudimentar", "dom_esg_vala",
    "dom_esg_corpo_dagua", "dom_sem_banheiro", "dom_lixo_coletado", "porte_pop",
]

# Catálogo dos indicadores municipais exibidos no app.
# pior_quando_maior: define a cor do delta no st.metric e a leitura do ranking.
INDICADORES = {
    "I7_ivsa": dict(nome="I7 · IVSA (vulnerabilidade socioambiental)", fmt="{:.2f}", pior_quando_maior=True,
                    desc="Média de 3 dimensões normalizadas de 0 a 1 entre os 39 municípios: renda, ambiente e educação. 0 = melhor da RMSP, 1 = pior."),
    "I2_mediana_sm": dict(nome="I2 · Renda mediana per capita (SM)", fmt="{:.2f}", pior_quando_maior=False,
                          desc="Renda domiciliar per capita mediana dividida pelo salário mínimo de 2022 (R$ 1.212)."),
    "I1_media_mediana": dict(nome="I1 · Razão média/mediana da renda", fmt="{:.2f}", pior_quando_maior=True,
                             desc="Renda média ÷ renda mediana. Quanto maior, mais a renda se concentra no topo."),
    "I3_pct_negra": dict(nome="I3 · % população negra", fmt="{:.1f}%", pior_quando_maior=None,
                         desc="Pretos + pardos sobre a população total. Indicador de composição, sem leitura de melhor ou pior."),
    "I3_diversidade_simpson": dict(nome="I3 · Diversidade racial (Simpson)", fmt="{:.2f}", pior_quando_maior=None,
                                   desc="1 − Σp² sobre as 5 categorias de cor ou raça. 0 = um único grupo; 0,8 = máximo."),
    "I4_deficit": dict(nome="I4 · Déficit de saneamento (%)", fmt="{:.1f}%", pior_quando_maior=True,
                       desc="100 − média de (% água da rede, % esgoto adequado, % lixo coletado)."),
    "dom_esg_inadequado": dict(nome="I4 · Domicílios com esgoto inadequado", fmt="{:,.0f}", pior_quando_maior=True,
                               desc="Fossa rudimentar, vala, rio/córrego ou sem banheiro (número absoluto)."),
    "I5_analfabetismo": dict(nome="I5 · Analfabetismo 15+ (%)", fmt="{:.1f}%", pior_quando_maior=True,
                             desc="100 − taxa de alfabetização da população de 15 anos ou mais."),
    "I6_pib_renda": dict(nome="I6 · PIB per capita ÷ renda anual", fmt="{:.1f}×", pior_quando_maior=True,
                         desc="Quantas vezes a riqueza produzida por habitante supera a renda anual dos moradores."),
}


def validar_base(df: pd.DataFrame) -> list[str]:
    """Retorna a lista de colunas obrigatórias ausentes (vazia = base válida)."""
    return [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]


def calcular_indicadores(base: pd.DataFrame) -> pd.DataFrame:
    """Calcula I1 a I7 por município. A normalização do IVSA usa sempre os 39
    municípios, por isso esta função roda na base completa, antes dos filtros."""
    ind = base.copy()
    ind["I1_media_mediana"] = ind["renda_pc_media"] / ind["renda_pc_mediana"]
    ind["I2_mediana_sm"] = ind["renda_pc_mediana"] / SM_2022

    racas = ["pct_branca", "pct_preta", "pct_parda", "pct_amarela", "pct_indigena"]
    ind["I3_pct_negra"] = ind["pct_preta"] + ind["pct_parda"]
    p = ind[racas].div(ind[racas].sum(axis=1), axis=0)
    ind["I3_diversidade_simpson"] = 1 - (p ** 2).sum(axis=1)
    ind["pop_negra"] = ind["I3_pct_negra"] / 100 * ind["populacao_2022"]

    ind["dom_esg_inadequado"] = ind[["dom_esg_rudimentar", "dom_esg_vala",
                                     "dom_esg_corpo_dagua", "dom_sem_banheiro"]].sum(axis=1)
    ind["pct_agua_rede"] = 100 * ind["dom_agua_rede"] / ind["dom_total"]
    ind["pct_esgoto_adequado"] = 100 * (ind["dom_esg_rede"] + ind["dom_esg_fossa_septica"]) / ind["dom_total"]
    ind["pct_lixo_coletado"] = 100 * ind["dom_lixo_coletado"] / ind["dom_total"]
    ind["I4_isa"] = ind[["pct_agua_rede", "pct_esgoto_adequado", "pct_lixo_coletado"]].mean(axis=1)
    ind["I4_deficit"] = 100 - ind["I4_isa"]

    ind["I5_analfabetismo"] = 100 - ind["taxa_alfab_15m"]
    ind["I6_pib_renda"] = ind["pib_pc_2023"] / (ind["renda_pc_media"] * 12)

    mm = lambda s: (s - s.min()) / (s.max() - s.min())  # noqa: E731
    ind["dim_renda"] = (mm(-ind["I2_mediana_sm"]) + mm(ind["I1_media_mediana"])) / 2
    ind["dim_ambiente"] = mm(ind["I4_deficit"])
    ind["dim_educacao"] = mm(ind["I5_analfabetismo"])
    ind["I7_ivsa"] = ind[["dim_renda", "dim_ambiente", "dim_educacao"]].mean(axis=1)
    return ind


def resumo(g: pd.DataFrame) -> dict:
    """KPIs agregados de um conjunto de municípios (mesma regra do notebook):
    taxas ponderadas pela população ou calculadas sobre totais de domicílios."""
    if g.empty:
        return {}
    pop = g["populacao_2022"].sum()
    dom = g["dom_total"].sum()
    w = g["populacao_2022"]
    return {
        "municipios": len(g),
        "populacao_mi": pop / 1e6,
        "renda_mediana_sm": np.average(g["I2_mediana_sm"], weights=w),
        "media_mediana": np.average(g["I1_media_mediana"], weights=w),
        "pct_negra": 100 * g["pop_negra"].sum() / pop,
        "pct_agua_rede": 100 * g["dom_agua_rede"].sum() / dom,
        "pct_esgoto_adequado": 100 * (g["dom_esg_rede"] + g["dom_esg_fossa_septica"]).sum() / dom,
        "pct_lixo_coletado": 100 * g["dom_lixo_coletado"].sum() / dom,
        "dom_esg_inadequado": g["dom_esg_inadequado"].sum(),
        "analfabetismo": np.average(g["I5_analfabetismo"], weights=w),
        "ivsa_medio": g["I7_ivsa"].mean(),
    }
