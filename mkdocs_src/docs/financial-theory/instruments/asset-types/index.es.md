# 📊 Tipos de activos

Los instrumentos difieren en el mundo real — cómo se valoran, si pagan ingresos, cómo se
gravan — y las páginas de detalle a continuación cubren esas diferencias. Dentro de LibreFolio, cada activo lleva
exactamente un **tipo de activo**, y el tipo es una **clasificación** que se lee en tres lugares: elige el
icono y la etiqueta que ves, decide dónde se cuenta el activo en los
gráficos de [asignación](../../portfolio-theory/asset-allocation.md), y nombra el grupo en el que cae el activo
cuando un [escenario de estrés](../../technical-analysis/risk-metrics/hypothetical-shock.md)
aplica choques a la cartera por clase de activo. `INDEX` es, además, el único tipo que no acepta
transacciones.

La taxonomía tiene **dos niveles**. La mayoría de los tipos son independientes; dos de ellos — **ETF** y
**Crowdfunding** — son **familias**, cuyos miembros también indican qué *contiene* el instrumento.

---

## 📋 Tipos base {: #base-types }

| | Tipo | Código | Descripción | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Acciones** | `STOCK` | Acciones de capital en una sola empresa. Los precios normalmente se obtienen de bolsas públicas. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Fondo cotizado (ETF) de contenido mixto o no especificado (equilibrado, multiactivo) — el miembro genérico de la [familia ETF](#etf-family). | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Bono** | `BOND` | Valores de renta fija que representan un préstamo a un prestatario (gobierno o empresa). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Cripto** | `CRYPTO` | Monedas digitales y tokens (Bitcoin, Ethereum, etc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fondo** | `FUND` | Fondos de inversión colectiva y otros fondos gestionados profesionalmente. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfunding (genérico)** | `CROWDFUND` | Préstamos de financiación colectiva entre particulares y préstamos empresariales, a menudo valorados mediante pagos de intereses programados — el miembro genérico de la [familia Crowdfunding](#crowdfunding-family). | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Activo mantenido** | `HOLD` | Activos sin valoración automática de mercado: arte, objetos de colección, participaciones en empresas no cotizadas. | — |
| ![](../../../static/icons/asset-types/commodity.png){: width="32" } | **Materia prima** | `COMMODITY` | Bienes físicos y sus exposiciones directas: oro, petróleo, productos agrícolas. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | **Inmobiliario** | `REAL_ESTATE` | Exposición inmobiliaria: REITs y otros vehículos inmobiliarios cotizados. | [📖](real-estate.md#three-ways-to-hold-property) |
| ![](../../../static/icons/asset-types/index.png){: width="32" } | **Índice** | `INDEX` | Índices de mercado (S&amp;P 500, MSCI World) utilizados como índices de referencia — no son directamente negociables, por lo que no se permiten transacciones. | [📖](index-benchmark.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Otro** | `OTHER` | Cualquier activo que los tipos anteriores no describan. | [📖](other.md) |

Un tipo es **una etiqueta por activo**: un ETF equilibrado se cuenta íntegramente como `ETF`, nunca se divide en sus
partes de acciones y bonos. Mirar *a través de* un instrumento es tarea de sus distribuciones sectoriales y
geográficas, no de su tipo.

---

## 🧬 Familias y subtipos {: #families-and-subtypes }

Un subtipo responde a una única pregunta: **¿qué tipo base contiene este instrumento?** El segundo
nivel, por tanto, no es una taxonomía paralela — *es* el conjunto de tipos base, visto a través de un contenedor.
El miembro genérico de cada familia (`ETF`, `CROWDFUND`) sigue siendo una opción válida por derecho propio: es
el caso residual para contenido mixto o no especificado, y el menú de tipos lo lista primero en su familia, con
una indicación que lo dice.

El icono de un subtipo es el icono de su familia con un pequeño disco en la esquina — una **pastilla** — que muestra su
contenido: el contenedor dice qué *es* el instrumento, la pastilla qué *contiene*. La pastilla es
el icono del tipo base que contiene el subtipo; el ETF de mercado monetario, que no contiene ningún tipo base,
toma prestado el icono de liquidez. Dondequiera que LibreFolio dibuje el icono de tipo, un subtipo muestra su compuesto —
un activo con un icono personalizado conserva el suyo.

### 📦 Familia ETF {: #etf-family }

| | Tipo | Código | Contiene | Consolida en |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Contenido mixto o no especificado — el miembro genérico | `ETF` (él mismo) |
| ![](../../../static/icons/asset-types/etf-stock.png){: width="32" } | **ETF de acciones** | `ETF_STOCK` | Acciones | `STOCK` |
| ![](../../../static/icons/asset-types/etf-bond.png){: width="32" } | **ETF de bonos** | `ETF_BOND` | Bonos | `BOND` |
| ![](../../../static/icons/asset-types/etf-commodity.png){: width="32" } | **ETF de materias primas** | `ETF_COMMODITY` | Materias primas | `COMMODITY` |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | **ETF inmobiliario** | `ETF_REAL_ESTATE` | Inmobiliario | `REAL_ESTATE` |
| ![](../../../static/icons/asset-types/etf-crypto.png){: width="32" } | **ETF de cripto** | `ETF_CRYPTO` | Criptoactivos | `CRYPTO` |
| ![](../../../static/icons/asset-types/etf-liquidity.png){: width="32" } | **ETF de mercado monetario** | `ETF_MONETARY` | Instrumentos de mercado monetario | `ETF_MONETARY` (él mismo — ver [abajo](#two-views-of-one-instrument)) |

El propio instrumento se describe en la página de [ETFs](etfs.md).

### 🤝 Familia Crowdfunding {: #crowdfunding-family }

| | Tipo | Código | Contiene | Consolida en |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfunding (genérico)** | `CROWDFUND` | Préstamos P2P y empresariales — el miembro genérico | `CROWDFUND` (él mismo) |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | **Crowdfunding inmobiliario** | `CROWDFUND_REAL_ESTATE` | Préstamos respaldados por proyectos inmobiliarios | `REAL_ESTATE` |

Ambos se describen en la página de [P2P / Crowdfunding](real-estate.md).

---

## ⚖️ Dos vistas de un mismo instrumento {: #two-views-of-one-instrument }

Los dos niveles responden a dos preguntas diferentes, y LibreFolio los mantiene separados.

- **La vista de contenedor** — *¿qué tipo de instrumento es?* — es la familia. El menú de tipos agrupa por
  familia, el icono conserva la forma de la familia, y la etiqueta dice *ETF de acciones*: ese es el instrumento
  que realmente posees.
- **La vista de contenido** — *¿a qué estoy expuesto?* — es la consolidación: un subtipo pertenece al tipo base
  que contiene. Un ETF de acciones y una acción son ambas exposición a acciones, y a la pregunta *¿estoy tan
  diversificado como creo?* el contenedor no dice nada.

Formalmente, sea $c$ la función que envía cada subtipo al tipo base que contiene, y cada otro tipo — los
miembros genéricos y `ETF_MONETARY` incluidos — a sí mismo. El peso de una clase de contenido $k$ es entonces

$$
W_k = \sum_{i \,:\, c(\tau_i) = k} w_i
$$

donde $\tau_i$ es el tipo de la posición $i$ y $w_i$ su peso en la cartera. La misma suma tomada
sobre el mapa de familias en lugar de $c$ — cada subtipo de ETF a `ETF`, `CROWDFUND_REAL_ESTATE` a
`CROWDFUND`, cada otro tipo a sí mismo — da el peso de cada familia, la contraparte de la vista de
contenedor.
La insignia de tipo sigue el contenido: una insignia de *ETF de acciones* es azul, como una insignia de *Acciones*. Cómo el
panel presenta la asignación por tipo se describe en el
[Panel de asignación](../../../user/dashboard/charts.md#allocation-panel).

Dos excepciones merecen una frase cada una:

- **`ETF_MONETARY` consolida en sí mismo.** Un fondo de mercado monetario no tiene un tipo base en el que consolidar: el efectivo es
  un saldo de cuenta, no un activo que se compra, así que no es un tipo de activo. `ETF` enterraría el
  fondo entre fondos mixtos, y *Liquidez* no es un tipo de activo en absoluto — es el grupo de asignación
  en el que LibreFolio cuenta tu saldo de efectivo, por separado. En la vista de contenido, el ETF de mercado monetario
  es, por tanto, una clase propia, y su insignia tiene un color propio.
- **`CROWDFUND_REAL_ESTATE` tiene dos respuestas.** En la vista de contenido contiene inmobiliario y
  pertenece a la clase Inmobiliario; en escenarios de estrés recibe un choque como el préstamo que es.

---

## 🌪️ Tipos en escenarios de estrés {: #types-in-stress-scenarios }

Un escenario de estrés que aplica choques a la cartera por clase de activo trata cada código como su **propio grupo** —
allí, un subtipo nunca se pliega en su clase de contenido. En los valores predeterminados de los dos
escenarios integrados de clase de activo, *Caída de acciones* y *Aversión global al riesgo*, cada subtipo de ETF recibe exactamente el
choque del tipo base que posee, mientras que el `ETF` genérico mantiene un choque combinado propio, porque
su contenido no está especificado; `ETF_MONETARY` no recibe choque.

La única desviación deliberada es `CROWDFUND_REAL_ESTATE`, que se mueve como `CROWDFUND` en lugar de
como `REAL_ESTATE`: un préstamo de crowdfunding es ilíquido y no se valora a mercado, y su riesgo es un
incumplimiento que llega tarde. El razonamiento, y su límite conocido, están en la
página de [P2P / Crowdfunding](real-estate.md#in-stress-scenarios).

Cada choque de grupo de esos escenarios es editable, y un grupo que se deja sin configurar recibe un choque de
cero — ver [Choque hipotético](../../technical-analysis/risk-metrics/hypothetical-shock.md#what-you-did-not-configure).

---

## 🔗 Relacionado

- 💸 **[Tipos de transacción](../transaction-types/index.md)** — Operaciones que afectan a tu cartera
- 📅 **[Eventos de activos](../asset-events/index.md)** — Acciones corporativas que afectan a los precios de los activos
- 💰 **[Fiscalidad](../../fundamentals/taxation.md)** — Implicaciones fiscales por clase de activo
- 🧭 **[Asignación de activos](../../portfolio-theory/asset-allocation.md)** — Distribuir capital entre clases de activos
- ⚡ **[Choque hipotético](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — Cómo se aplican choques a los grupos por clase de activo
