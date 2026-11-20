# Data app: desigualdade, diversidade e saneamento na RMSP (Censo 2022)

**Introdução à Ciência de Dados · Sistemas para Internet · Projeto Tema 2, Parte 2**
Trabalho individual · Claudio Ferreira Junior

Aplicação interativa em Streamlit que reúne os indicadores da Parte 1 sobre os
39 municípios da Região Metropolitana de São Paulo e os resultados da modelagem
preditiva da Parte 3 (previsão do % de domicílios com esgoto adequado).

## Estrutura do projeto

```
.
├── app.py                         # aplicação Streamlit
├── indicadores.py                 # cálculo dos indicadores I1 a I7 (mesmas fórmulas do notebook)
├── modelo.py                      # reconstrução do modelo da Parte 3 para o simulador
├── notebooks/
│   └── rmsp_parte3_modelagem.ipynb    # treino e avaliação do modelo (Parte 3)
├── requirements.txt               # dependências
├── JUSTIFICATIVA.md               # componentes do Streamlit e função de cada um
├── .streamlit/config.toml         # tema visual
└── data/
    ├── rmsp_censo2022_tratado.csv     # base tratada na Parte 1 (39 municípios)
    ├── brasil_modelagem.csv           # 5.570 municípios usados no treino (gerado na Parte 3)
    ├── resultados_modelo.json         # métricas, modelo escolhido e importância (Parte 3)
    ├── rmsp_previsoes.csv             # observado, previsto e resíduo dos 39 municípios (Parte 3)
    └── rmsp_municipios.geojson        # limites municipais (IBGE, via tbrugz/geodata-br)
```

## Como executar localmente

Requisitos: Python 3.10 ou mais recente.

```bash
# 1. Entrar na pasta do projeto
cd rmsp_data_app

# 2. (Opcional, recomendado) criar e ativar um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Rodar o app
streamlit run app.py
```

O navegador abre em `http://localhost:8501`. Se não abrir sozinho, copie esse endereço.

## Fonte dos dados

Tabelas oficiais do IBGE: Censo Demográfico 2022, PIB dos Municípios 2023 e
Estimativas de População. Todos os números podem ser conferidos no
[SIDRA](https://sidra.ibge.gov.br/tabela).

| Conteúdo | Tabelas SIDRA | Arquivo de origem |
|---|---|---|
| População, PIB per capita, renda, cor ou raça, alfabetização | 4714, 6579, 5938, 10295, 9605, 9543 | https://github.com/caioapolonio/eleicoes-2026 (só as colunas do IBGE) |
| Água, esgoto e lixo por domicílio | 6803, 6805, 6892 | https://github.com/zxcortes/Saneamento-censo-2022-Analise_de_Dados |

O pré-processamento está no notebook da Parte 1 (`rmsp_parte1_censo2022.ipynb`).
O app lê a base já tratada (`data/rmsp_censo2022_tratado.csv`) e recalcula os
indicadores em `indicadores.py`. Pela barra lateral (**Fonte dos dados**) é
possível enviar outra versão do mesmo CSV: o app confere as colunas e, se o
arquivo estiver fora do formato, volta para a base padrão.

## O que o app tem

| Aba | Conteúdo |
|---|---|
| **Visão geral** | 8 KPIs (`st.metric`) da seleção comparados com a RMSP e os principais achados da Parte 1 |
| **Explorar indicadores** | Mapa coroplético, ranking, dispersão raça × renda com correlação de Spearman e déficit de saneamento em % ou em número de domicílios. Botão para baixar os dados da seleção |
| **Ficha do município** | KPIs de um município comparados com a RMSP e gráfico dos componentes do IVSA |
| **Modelagem preditiva** | Métricas dos modelos, previsto × observado, municípios abaixo do esperado ("déficit inesperado"), importância das variáveis e simulador de cenários |
| **Sobre os dados** | Fontes, pré-processamento, dicionário de indicadores e tabela da seleção |

## Atualizar os resultados do modelo

Rode `notebooks/rmsp_parte3_modelagem.ipynb` (ele baixa os dados do IBGE se
não encontrar os arquivos) e copie para `data/` os três arquivos que ele gera:
`resultados_modelo.json`, `rmsp_previsoes.csv` e `brasil_modelagem.csv`. O
simulador treina o modelo de novo a partir desses arquivos na primeira vez que a
aba é aberta (alguns segundos), então não há arquivo de modelo salvo para manter.

## Publicar no Streamlit Community Cloud (opcional)

1. Crie um repositório público no GitHub e envie todos os arquivos desta pasta
   (incluindo `data/` e `.streamlit/`).
2. Acesse https://share.streamlit.io e entre com a conta do GitHub.
3. Clique em **Create app**, escolha o repositório, a branch `main` e o arquivo
   principal `app.py`.
4. Clique em **Deploy**. A primeira publicação leva alguns minutos. O link gerado
   pode ser colocado na entrega.

## Limitações

- A unidade de análise é o município: a desigualdade dentro de São Paulo, que tem
  mais da metade da população da região, não aparece.
- As associações entre raça e renda são entre municípios, não entre pessoas.
- O IVSA é normalizado entre os 39 municípios da RMSP, então só vale para comparação
  dentro da região.
