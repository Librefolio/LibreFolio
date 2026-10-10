# 📅 Anualización observada

Anualizar una cifra de riesgo requiere saber cuántos períodos contiene un año, y ese número puede medirse a partir de los datos observados en lugar de asumirse de antemano. LibreFolio lo mide: el factor utilizado para escalar una cifra por período a una anual es **contado a partir de la serie que realmente se analizó**, nunca tomado de una convención de mercado fijada de antemano.

---

## 🔢 Fórmula {: #formula }

Se leen dos cantidades de la serie antes de anualizar cualquier cifra — el lapso de calendario que cubre, y el número de rentabilidades observadas dentro de ese lapso:

$$
D = d_{last} - d_{baseline}
$$

$$
f = \frac{N \times 365}{D}
$$

donde:

- $N$ = número de rentabilidades por período realmente utilizadas
- $d_{baseline}$ = fecha de la primera valoración (abre la serie y por lo tanto no produce una rentabilidad propia)
- $d_{last}$ = fecha de la última rentabilidad
- $D$ = días naturales abarcados, fines de semana y cierres incluidos

El factor $f$ se aplica entonces dondequiera que una cifra por período deba expresarse en base anual. Para la volatilidad:

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

!!! info "Es un conteo, no una convención"

    $f$ tiene una lectura literal: **observaciones por año, contadas**. Una serie con $N$ rentabilidades distribuidas a lo largo de $D$ días naturales fue observada a una tasa de $N/D$ por día, es decir $365N/D$ por año. No se hace ninguna suposición sobre el instrumento, su calendario de mercado o su clase de activo — la tasa es la que resulte de los datos. La única pieza de conocimiento del calendario involucrada decide qué cuenta como una observación, nunca cuántas debería haber: un precio almacenado que solo repite el cierre anterior en un fin de semana o un día festivo del mercado es un arrastre, no una cotización (ver [abajo](#252-is-recovered-not-imposed)).

Si el lapso se colapsa — una única fecha de valoración, de modo que $D \leq 0$ — no existe factor alguno y no se produce ninguna cifra anualizada. La alternativa sería inventar una.

---

## 💡 Interpretación {: #interpretation }

La siguiente tabla desarrolla la fórmula para algunas formas de series. Es aritmética, no el resultado de una ejecución de LibreFolio:

| Serie | Rentabilidades $N$ | Días naturales $D$ | $f = 365N/D$ | $\sqrt{f}$ |
|---|---|---|---|---|
| Instrumento cotizado solo en días de negociación, año completo | 252 | 365 | 252.0 | 15.87 |
| Instrumento que cotiza todos los días (cripto), año completo | 365 | 365 | 365.0 | 19.10 |
| Fondo con precio semanal, año completo | 52 | 365 | 52.0 | 7.21 |
| Instrumento cotizado en días de negociación, iniciado a mitad de período | 126 | 183 | 251.3 | 15.85 |
| Serie diaria con huecos | 180 | 365 | 180.0 | 13.42 |

De esas filas se desprenden cuatro lecturas.

### 📈 √252 se recupera, no se impone {: #252-is-recovered-not-imposed }

Un instrumento cotizado solo mientras su mercado está abierto contribuye con aproximadamente 252 rentabilidades a lo largo de un año natural completo, así que $f = 252 \times 365 / 365 = 252$ y el conocido $\sqrt{252}$ sale de la medición. El número convencional es **un resultado** aquí, no una entrada — que es precisamente por lo que no se pierde nada al negarse a fijarlo en el código.

Sale incluso cuando la fuente de precios entrega una fila por cada día natural. Algunas fuentes repiten el último cierre en los días en que el mercado está cerrado — justETF, por ejemplo, repite el cierre del viernes el sábado y el domingo. Contadas como cotizaciones, esas filas agregarían una rentabilidad cero que ningún mercado produjo por cada día cerrado, y empujarían $f$ hacia 365. No se cuentan: un precio almacenado fechado en sábado, domingo o un día festivo entre semana cuyo cierre repite **exactamente** el cierre de la fila anterior es un **arrastre** — la última cotización mantenida, no una nueva — y su fecha no añade observación alguna a la serie. Un precio que se movió en un día cerrado sigue siendo una cotización, como lo son los precios de fin de semana de un criptoactivo, y también lo es un precio sin cambios en un día hábil ordinario, como un día plano de un bono. El instrumento conserva sus días de negociación, y $f$ se mantiene cerca de 252. La regla completa, con las bolsas cuyos festivos cuentan, está en [Calidad de datos](data-quality.md#stored-carries).

!!! info "Una serie de cartera se lee en los días de cotización de sus posiciones"

    Esa fila describe los precios cotizados propios de un instrumento; la serie de rentabilidades de una **cartera** llega a ella por otra vía. La [rentabilidad ponderada por tiempo](../performance-metrics/portfolio-engine/twrr.md) de la cartera se calcula día natural a día natural, fines de semana y festivos incluidos, arrastrando hacia adelante el último precio conocido donde no se cotizó nada. El análisis de riesgos la lee solo en sus **días de observación** — los días en que al menos una de las posiciones mantenidas al final del período analizado tuvo una cotización propia — y encadena la rentabilidad de todos los demás días en el siguiente día de observación, de modo que la rentabilidad acumulada es exactamente la que era: solo cambia el muestreo. Una cartera de acciones y fondos cotizados en días de negociación, por lo tanto, contribuye con aproximadamente 252 rentabilidades al año, como la primera fila, aunque su historial tenga un punto por cada día natural; una que mantiene un instrumento cotizado cada día natural, como un criptoactivo, se observa todos los días, como la segunda. El factor sigue a la serie sobre la que se calcula la métrica, que es exactamente por lo que se mide en lugar de asumirse.

### 🪙 Un instrumento 24/7 da ≈ √365 {: #a-247-instrument-gives-365 }

Un instrumento que cotiza cada día natural se observa 365 veces al año, así que $f \approx 365$. Un $\sqrt{252}$ fijado en el código, si se aplicara a este instrumento, **subestimaría** su volatilidad anualizada en un factor de:

$$
\frac{\sqrt{365}}{\sqrt{252}} \approx 1.20
$$

El error no es un detalle de redondeo: es sistemático, y siempre apunta en la dirección tranquilizadora.

### 📐 El factor mide una tasa, no una longitud {: #the-factor-measures-a-rate-not-a-length }

La cuarta fila es una acción con precio diario observada durante aproximadamente medio año: $f$ aún cae cerca de 252, porque numerador y denominador se encogen juntos. Una ventana más corta no encoge el factor — solo lo hace más ruidoso (ver las limitaciones a continuación).

### 🕳️ Los huecos lo bajan, honestamente {: #gaps-lower-it-honestly }

Festivos, precios faltantes, un activo que comenzó a mitad de período: lo que se observó es lo que se cuenta. Una serie con huecos se anualiza como la serie dispersa que es, en lugar de como la serie densa que se asumió que era.

---

## 📏 Cobertura {: #coverage }

Junto con el factor, se publica una segunda cantidad con el resultado: de los días en que la serie podría haberse observado, la proporción en que se observó.

$$
c = \frac{N}{Q}
$$

donde $Q$ es el número de esos días. La cobertura dice cuán **densamente** se muestreó la serie, como una fracción entre 0 y 1. No es un segundo factor de anualización: $f$ dice a qué tasa se observó la serie, $c$ dice cuántas de sus posibles observaciones conservó. Qué días cuentan en $Q$ depende de cómo se construye la serie:

- Una serie de **instrumento** — y cualquier serie construida a partir de los precios de varios activos — corre sobre un calendario conjunto. Cada fecha en la ventana solicitada en la que al menos uno de los activos tiene una cotización propia es una candidata, y una candidata se convierte en observación solo si todos los activos pueden valorarse en ella, incluido un precio arrastrado hacia adelante desde una fecha anterior. $Q$ cuenta las candidatas, excluida la línea base. Para un instrumento cotizado solo mientras su mercado está abierto, las candidatas son el calendario propio del mercado, así que sus días cerrados no cuestan nada: un arrastre no es una cotización, y no añade candidata alguna.
- Una serie de **cartera** es su rentabilidad ponderada por tiempo leída en sus días de observación (ver [arriba](#252-is-recovered-not-imposed)), con su primer punto conservado como la línea base. $Q$ cuenta los días de observación posteriores a la línea base, hasta la última rentabilidad. El historial de la cartera tiene un punto por cada día natural, así que para una cartera mantenida sin interrupción cada día de observación lleva uno, y la cobertura se sitúa en la parte alta de su rango por construcción. Solo si ninguna de las posiciones tiene una cotización propia en la ventana se conserva cada día natural, y $Q$ es entonces el lapso $D$.

Lo que la cobertura **no** dice es si los precios detrás de esas observaciones eran reales. En un calendario conjunto, una fecha en la que solo algunos de los activos cotizaron sigue siendo una observación, entrando los demás con un precio arrastrado hacia adelante; en un día de observación de una cartera, cada posición no cotizada ese día entra a su último valor conocido. Así que una cobertura alta no es un certificado y una baja no es un defecto: ambas describen *cuántas de las posibles observaciones conservó la serie*, no la calidad de lo que hay dentro de ellas. Esa segunda pregunta — ¿estos precios fueron cotizados, o arrastrados hacia adelante? — es trabajo de [Calidad de datos](data-quality.md).

!!! info "Ambas cifras viajan con el resultado"

    Cada resultado de riesgo lleva los parámetros de entrada de su propia anualización en sus metadatos — el número de observaciones, los días naturales abarcados, el factor y la cobertura. Una cifra anual publicada puede, por lo tanto, recalcularse a mano a partir de las mismas entradas que la produjeron.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "Un lapso corto hace inestable el factor"

    El denominador es el lapso de calendario observado. En unas pocas semanas $D$ es pequeño, así que una observación faltante o una extra mueve $f$ de manera apreciable, y $\sqrt{f}$ con él. La cifra anualizada hereda esa inestabilidad: se está extrapolando desde una ventana mucho más corta que el año que pretende describir.

!!! warning "Medir el factor no repara la suposición"

    Escalar por $\sqrt{f}$ se deriva de que la varianza suma a través de períodos **independientes** (ver [Volatilidad](volatility.md)). Si las rentabilidades están autocorrelacionadas — tendencias, agrupamiento de volatilidad, reversión a la media — la cifra escalada está sesgada independientemente de cuán exactamente se contó $f$. Medir el factor elimina una constante errónea; no elimina la hipótesis de independencia subyacente.

Dos cifras anualizadas con factores diferentes también son comparables solo si el muestreo detrás de ellas es comparable. Un fondo con precio semanal y un instrumento 24/7 están ambos anualizados correctamente, y aun así se observan de maneras muy diferentes — que es lo que el conteo de observaciones y la cobertura están ahí para hacer visible.

---

## 🔗 Relacionado {: #related }

- 📊 **[Volatilidad](volatility.md)** — la cifra que más a menudo se expresa en base anual
- 🧪 **[Calidad de datos](data-quality.md)** — qué significa una cobertura baja para la fiabilidad de un resultado
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — un ratio ajustado por riesgo que también lleva una escala anual
- 📊 **[Ratio de Sortino](sortino-ratio.md)** — la variante solo a la baja, misma cuestión de escalado
