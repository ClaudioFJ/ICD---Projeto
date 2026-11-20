# Justificativa dos componentes do Streamlit

O app foi pensado para responder a uma pergunta de gestão: **onde, na RMSP,
desigualdade de renda, composição racial e déficit de saneamento se sobrepõem?**
Cada componente tem uma função distinta nessa análise. Nenhum widget repete o
papel de outro.

## 1. Organização da tela

| Componente | Função na análise |
|---|---|
| `st.set_page_config(layout="wide")` | Usa a largura toda, para o mapa e o ranking ficarem lado a lado e serem comparados de uma vez. |
| `st.sidebar` | Reúne os filtros **globais**. Fica separado do conteúdo para deixar claro que esses filtros valem para todas as abas. |
| `st.tabs` | Separa o app em cinco tarefas: resumo, exploração, detalhe de um município, modelagem e documentação. Quem só quer os números principais não precisa rolar por todos os gráficos. |
| `st.columns` | Coloca lado a lado o que deve ser comparado (mapa × ranking, KPIs em linha, gráfico × texto de leitura). |
| `st.expander` | Esconde o envio de arquivo, que é uma função eventual, para não disputar atenção com os filtros. |
| `st.divider` | Separa os blocos de análise dentro de uma aba. |

## 2. Textos explicativos

| Componente | Função na análise |
|---|---|
| `st.title`, `st.subheader`, `st.markdown` | Dizem o que cada bloco mostra e trazem os achados da Parte 1 em linguagem simples. |
| `st.caption` | Notas de leitura logo abaixo de cada gráfico: o que a cor significa, o que é melhor ou pior e os cuidados de interpretação (falácia ecológica, poços fora da rede). |
| `help=` nos widgets e métricas | Mostra a fórmula do indicador ao passar o mouse, sem ocupar espaço na tela. |
| `st.info`, `st.warning`, `st.error` | Avisam sobre o estado do app: aba em construção, filtro que não retorna nenhum município, arquivo enviado inválido. |

## 3. Carregamento dos dados

| Componente | Função na análise |
|---|---|
| `st.cache_data` | Lê o CSV e calcula os indicadores uma única vez. Os filtros respondem na hora, sem reprocessar a base. |
| `st.file_uploader` | Permite carregar uma nova versão da base tratada (por exemplo, depois de rodar o notebook de novo). O app confere as colunas obrigatórias antes de usar o arquivo. |
| `st.download_button` | Exporta os indicadores da seleção atual em CSV, para quem quiser continuar a análise em outra ferramenta. |

## 4. KPIs (`st.metric`)

A **Visão geral** tem 8 métricas em dois grupos (renda e diversidade; saneamento
e educação). A **Ficha do município** tem mais 8. Todas são calculadas a partir
dos dados no momento da execução:

- Renda mediana per capita em salários mínimos (I2)
- Razão média/mediana da renda (I1)
- % de população negra (I3)
- IVSA médio (I7)
- % de domicílios com água da rede, % com esgoto adequado, número de domicílios com esgoto inadequado (I4)
- Analfabetismo 15+ (I5)

Para grupos de municípios, as taxas são **ponderadas pela população** ou calculadas
sobre o **total de domicílios**, como no notebook. Assim a capital pesa o que
realmente representa na região.

O `delta` de cada métrica mostra a **diferença em relação à RMSP inteira**, e a cor
segue o sentido do indicador: `delta_color="inverse"` quando "maior é pior"
(analfabetismo, IVSA) e `"off"` quando não há melhor ou pior (composição racial).
Para o número absoluto de domicílios com esgoto inadequado, o delta mostra a
**parcela do total da região**, porque uma diferença absoluta entre um grupo de
municípios e a região inteira não teria sentido.

## 5. Filtros

São três widgets de filtro, de tipos diferentes e com funções que não se sobrepõem:

| Widget | Onde | O que filtra | Por quê |
|---|---|---|---|
| `st.multiselect` **Sub-regiões** | Barra lateral | Quais municípios entram na análise, pelas 6 sub-regiões oficiais | O planejamento metropolitano é feito por sub-região. Permite, por exemplo, comparar o Sudoeste (mananciais) com o ABC (Sudeste). |
| `st.slider` **Renda mediana per capita (R$)** | Barra lateral | Mantém só os municípios dentro de uma faixa de renda | Isola o recorte de renda: "como estão o saneamento e a composição racial nos municípios com renda mediana abaixo de 1 salário mínimo?" |
| `st.selectbox` **Indicador** | Aba Explorar | Qual indicador colore o mapa e ordena o ranking | Um mapa e um ranking servem a 9 indicadores, sem repetir gráficos. |

Também há dois controles de visualização:

| Widget | Função |
|---|---|
| `st.radio` **% dos domicílios × número de domicílios** | Mostra as "duas faces" do déficit de saneamento, um dos achados da Parte 1. Em percentual aparecem os municípios pequenos de mananciais (Juquitiba, São Lourenço da Serra); em número absoluto, a mancha urbana (São Paulo, Guarulhos). |
| `st.selectbox` **Município** | Escolhe o município da ficha. A lista mostra só os municípios que passam nos filtros da barra lateral. |

### Como cada filtro muda o app

| Elemento | Sub-regiões | Faixa de renda | Indicador | % / absoluto | Município |
|---|:---:|:---:|:---:|:---:|:---:|
| KPIs da Visão geral | ✔ | ✔ | | | |
| Mapa coroplético | ✔ (fora da seleção fica cinza) | ✔ | ✔ (cor) | | |
| Ranking | ✔ | ✔ | ✔ (ordem e valor) | | |
| Dispersão raça × renda e correlação | ✔ | ✔ | | | |
| Barras de saneamento | ✔ | ✔ | | ✔ | |
| Lista da Ficha do município | ✔ | ✔ | | | |
| KPIs e gráfico da Ficha | | | | | ✔ |
| Tabela e download | ✔ | ✔ | | | |
| Cartões e gráficos de resíduo (Modelagem) | ✔ | ✔ | | | |
| Lista do simulador (Modelagem) | ✔ | ✔ | | | |

Exemplo: ao selecionar apenas **Leste** e **Sudoeste**, a renda mediana cai para
0,91 SM (−0,16 em relação à RMSP), o esgoto adequado cai para 88,7% (−4,8 p.p.)
e a correlação entre % de população negra e renda passa de −0,57 para −0,33.

**Escolha de projeto:** o IVSA é sempre normalizado sobre os 39 municípios.
Por isso o valor de um município não muda quando os filtros mudam, e o mapa e o
ranking continuam comparáveis entre seleções diferentes.

## 6. Gráficos interativos (Plotly, via `st.plotly_chart`)

Nas abas de exploração são cinco gráficos de três tipos: mapa coroplético, barras (horizontais, empilhadas e agrupadas) e dispersão. A aba de modelagem acrescenta mais três (seção 8). Todos mostram o valor ao passar o mouse e
permitem zoom e ocultar séries pela legenda.

| Gráfico | Tipo | O que responde |
|---|---|---|
| Mapa dos municípios | Coroplético | **Onde** está o problema. A questão é territorial, então o mapa é a visão principal. |
| Ranking da seleção | Barras horizontais | **Quem** está em pior ou melhor situação, com a sub-região identificada pela cor. |
| Raça e renda no território | Dispersão (bolhas) | Se há **relação** entre composição racial e renda. O tamanho da bolha é a população e a linha marca 1 salário mínimo. |
| Déficit de saneamento | Barras empilhadas | **De que é feito** o déficit (água, esgoto ou lixo) e como o quadro muda entre percentual e número absoluto. |
| Componentes do IVSA | Barras agrupadas | **Por que** um município é vulnerável: renda, saneamento ou educação, comparados com a média da região. |

Escolhas visuais:
- Cada sub-região tem uma cor fixa, que não muda quando os filtros mudam.
- Na dispersão, cada sub-região também tem um símbolo diferente, para não depender só da cor.
- O mapa usa uma escala de um único tom (verde claro → escuro) para magnitude.
- Estilo institucional, inspirado em relatórios de órgãos públicos: barra lateral azul-marinho, verde como cor de destaque, títulos serifados (Source Serif) e texto em Source Sans. As duas fontes já vêm com o Streamlit, então o visual é o mesmo mesmo sem internet. As cores foram conferidas para que pessoas com daltonismo consigam diferenciá-las.
- Os números aparecem no formato brasileiro (vírgula decimal).

## 7. Tabela (`st.dataframe` com `column_config`)

A aba **Sobre os dados** mostra a tabela da seleção, ordenada pelo IVSA, com
barra de progresso para o índice. Serve para conferir os valores exatos que os
gráficos resumem.

## 8. Modelagem preditiva (resultados da Parte 3)

| Componente | Função na análise |
|---|---|
| `st.metric` (4 cartões) | Resumem a qualidade do modelo: tamanho da base, erro médio no teste (com o ganho sobre prever a média no `delta`), R² e erro médio na RMSP. |
| `st.expander` com `st.dataframe` | Tabela completa de comparação dos modelos (validação, teste e estado novo). Fica recolhida porque é detalhe técnico. |
| `st.metric` (3 cartões) da seleção | Quantos municípios estão abaixo do esperado, quantos domicílios isso representa e a diferença média. **Respondem aos filtros da barra lateral.** |
| Dispersão previsto × observado | Mostra de uma vez quem está acima ou abaixo da linha "observado = previsto". |
| Barras de resíduo | Ordena os municípios pelo déficit inesperado, com terracota para abaixo do esperado e verde para acima. |
| Barras de importância | Mostram o que o modelo usa para prever. |
| `st.selectbox` + 2 `st.slider` (simulador) | Escolhem o município e o cenário (variação da renda e da alfabetização). Os três cartões mostram observado, previsto hoje e previsto no cenário. São os únicos controles que mexem no modelo, por isso não repetem os filtros da barra lateral. |
| `st.cache_resource` | Treina o modelo do simulador uma única vez por servidor, e não a cada clique. |

Os filtros de sub-região e de renda da barra lateral também valem para esta aba:
eles definem quais municípios aparecem nos cartões, nos dois gráficos de
resíduo e na lista do simulador.
