"""Reconstrução do modelo da Parte 3 para o simulador do app.

O modelo é treinado de novo a partir de data/brasil_modelagem.csv com os mesmos
hiperparâmetros escolhidos no notebook (data/resultados_modelo.json). Isso evita
salvar um arquivo pickle, que costuma quebrar entre versões do scikit-learn.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def montar_X(df: pd.DataFrame, numericas: list[str], colunas: list[str] | None = None) -> pd.DataFrame:
    """Variáveis numéricas + dummies de UF, na mesma ordem de colunas do treino."""
    X = pd.get_dummies(df[numericas + ["uf"]], columns=["uf"], prefix="uf", dtype=float)
    if colunas is not None:
        X = X.reindex(columns=colunas, fill_value=0.0)
    return X


def treinar(brasil: pd.DataFrame, info: dict):
    """Treina o modelo escolhido com todos os municípios do Brasil."""
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    numericas = info["numericas"]
    X = montar_X(brasil, numericas)
    y = brasil["pct_esgoto_adequado"]
    nome, p = info["modelo_escolhido"], info.get("parametros", {})
    if nome == "Gradient Boosting":
        modelo = HistGradientBoostingRegressor(**p)
    elif nome == "Random Forest":
        modelo = RandomForestRegressor(n_jobs=-1, **p)
    else:
        modelo = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 13)))
    modelo.fit(X, y)
    return modelo, list(X.columns)


def cenario(linha: pd.Series, var_renda_pct: float, var_alfab_pp: float) -> pd.Series:
    """Aplica um cenário a um município: renda (média e mediana) multiplicada por
    (1 + var%), mantendo a razão média/mediana, e alfabetização somada em p.p."""
    nova = linha.copy()
    nova["log_renda_mediana"] = np.log(linha["renda_pc_mediana"] * (1 + var_renda_pct / 100))
    nova["taxa_alfab_15m"] = min(100.0, linha["taxa_alfab_15m"] + var_alfab_pp)
    return nova
