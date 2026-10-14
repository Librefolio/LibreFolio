# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Las plataformas de **P2P / Crowdfunding** permiten a los inversores prestar cantidades relativamente
pequeñas a consumidores, empresas o proyectos inmobiliarios. El inversor no compra una participación
en nada: posee un **préstamo**, que normalmente paga intereses fijos o variables y tiene una fecha de
vencimiento definida.

LibreFolio modela estos instrumentos como la **familia Crowdfunding** de
[tipos de activos](index.md#crowdfunding-family): el `CROWDFUND` genérico y su especialización
inmobiliaria, `CROWDFUND_REAL_ESTATE`.

---

## 🔑 Características clave

| Propiedad | Detalle |
|----------|--------|
| **Códigos en LibreFolio** | `CROWDFUND` — préstamos P2P y a empresas, y el miembro genérico de la familia · `CROWDFUND_REAL_ESTATE` — préstamos respaldados por proyectos inmobiliarios |
| **Valoración** | No cotiza en un mercado organizado — el valor suele ser el principal invertido |
| **Moneda** | Denominada en la moneda de operación de la plataforma |
| **Rendimiento** | Pagos periódicos de intereses (mensuales, trimestrales o al vencimiento) |
| **Liquidez** | Muy baja — los fondos quedan bloqueados hasta el vencimiento o la recompra |
| **Proveedores típicos** | Inversión programada, o precios introducidos a mano en el [Editor de datos](../../../user/assets/detail/data-editor.md) |

---

## 🏷️ Qué código elegir {: #which-code-to-choose }

| | Código | Elegirlo cuando el préstamo… |
|:---:|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | financia un proyecto inmobiliario |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | `CROWDFUND` | va a consumidores o empresas — o no se indica su finalidad |

La regla se refiere a qué financia el préstamo, no a la plataforma. En caso de duda, `CROWDFUND` —el
residual de la familia— es la opción segura; el precio es que, en la
[vista de contenido](index.md#two-views-of-one-instrument), el préstamo ya no cuenta como inmobiliario.

---

## 📊 Cómo funciona

### 🏗️ Crowdfunding inmobiliario — `CROWDFUND_REAL_ESTATE`

1. Una plataforma publica un proyecto inmobiliario que necesita financiación
2. Varios inversores aportan pequeñas cantidades (€500–€10.000, habitualmente)
3. El proyecto paga intereses sobre el capital invertido
4. Al vencimiento, se devuelve el principal (si el proyecto tiene éxito)

### 💸 Préstamos P2P — `CROWDFUND`

1. Los prestatarios —consumidores o empresas— solicitan préstamos a través de una plataforma
2. Los inversores financian partes de los préstamos
3. Los prestatarios devuelven el principal + los intereses durante el plazo del préstamo
4. La plataforma distribuye los pagos a los inversores

---

## ⚠️ Factores de riesgo

| Riesgo | Descripción |
|------|-------------|
| **Riesgo de impago** | El prestatario/proyecto puede no reembolsar |
| **Riesgo de liquidez** | No se puede vender antes del vencimiento (a diferencia de las acciones) |
| **Riesgo de plataforma** | La propia plataforma puede quebrar |
| **Riesgo de concentración** | Cada inversión es un único proyecto/prestatario |

---

## 🏠 Tres formas de poseer inmuebles {: #three-ways-to-hold-property }

*Real estate* designa tres instrumentos diferentes en LibreFolio, y lo que los separa es la
diferencia entre **poseer** y **prestar**:

| | Código | Qué posees | Naturaleza del derecho |
|:---:|:---|:---|:---|
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | `REAL_ESTATE` | Una participación en un REIT o en otro vehículo inmobiliario cotizado | Renta variable: posees parte de los ingresos y del valor del inmueble |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | `ETF_REAL_ESTATE` | Una participación en un ETF que posee dichos vehículos | Renta variable, a través de una cesta |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | Un préstamo a un proyecto inmobiliario, a través de una plataforma | Deuda: se te deben intereses y principal, reembolsados por el proyecto |

Los tres contienen inmuebles, por lo que la [vista de contenido](index.md#two-views-of-one-instrument)
los coloca en la misma clase, y su insignia es verde azulado. Sin embargo, los derechos se comportan
de forma muy diferente cuando los mercados caen — y ahí es donde los escenarios de estrés se separan.

---

## 🌪️ En escenarios de estrés {: #in-stress-scenarios }

Un escenario de estrés que aplica impactos a la cartera por clase de activo da a cada código su
propio grupo de exposición. En los valores predeterminados de los dos escenarios de clase de activo
integrados:

| Código | Desplome de la renta variable | Aversión global al riesgo |
|:---|---:|---:|
| `REAL_ESTATE` | −20 % | −15 % |
| `ETF_REAL_ESTATE` | −20 % | −15 % |
| `CROWDFUND_REAL_ESTATE` | −10 % | −10 % |
| `CROWDFUND` | −10 % | −10 % |

`CROWDFUND_REAL_ESTATE` recibe el impacto como el **préstamo** que es, no como la propiedad que hay
detrás. La propiedad cotizada se recalcula cada día de negociación, por lo que una venta masiva le
afecta de inmediato. Un préstamo de crowdfunding es ilíquido y no se valora a precio de mercado —
nada lo recalcula a la mañana siguiente — y su riesgo es un **impago que llega tarde**; en un choque
instantáneo, por tanto, se mueve como el resto de `CROWDFUND`.

!!! warning "Limitación conocida: una crisis inmobiliaria prolongada"

    Un choque hipotético es una afirmación de un único periodo: no contempla el paso del tiempo. El
    riesgo de crédito de los préstamos respaldados por inmuebles es precisamente el tipo que se
    acumula con el tiempo, a medida que una crisis inmobiliaria se prolonga — por lo que el −10 %
    **subestima** ese riesgo en una crisis prolongada. El impacto de cada grupo de exposición es
    editable: si ese es el escenario que quieres probar, eleva tú mismo el grupo
    `CROWDFUND_REAL_ESTATE`.

    Cómo se aplican los grupos de exposición y qué ocurre con los que no configuras se explica en
    [Choque hipotético](../../technical-analysis/risk-metrics/hypothetical-shock.md).

---

## 🔧 Modelado en LibreFolio

El proveedor **Inversión programada** está diseñado para estos instrumentos. A partir de la
programación que configures, genera:

- **[Eventos de interés](../asset-events/interest.md)** — pagos periódicos de cupones, cuando la
  programación está configurada para generarlos
- **[Eventos de liquidación al vencimiento](../asset-events/maturity-settlement.md)** — la devolución
  final del capital al final del plazo

Los **[eventos de ajuste de precio](../asset-events/price-adjustment.md)** que registres tú mismo —
una reducción de valor cuando un proyecto tiene un rendimiento inferior — se aplican al valor que
calcula.

---

## 🔗 Relacionado

- 📊 **[Tipos de activos](index.md)** — La taxonomía de dos niveles y cómo se consolidan los subtipos
- 📈 **[Eventos de interés](../asset-events/interest.md)** — Cómo funciona el devengo de intereses
- 🏁 **[Liquidación al vencimiento](../asset-events/maturity-settlement.md)** — Devolución del capital al final de la vida
- 📅 **[Convenciones de recuento de días](../../fundamentals/day-count.md)** — Cómo se calculan los periodos de interés
- ⚡ **[Choque hipotético](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — Cómo los escenarios de estrés impactan en los grupos de clases de activos
