# 🛡️ Pestaña Riesgo

La pestaña **Riesgo** del [Panel](index.md) muestra cuán riesgosa es tu cartera, a través de cuatro preguntas sencillas — desde lo que realmente ocurrió hasta lo que podría ocurrir. Se ubica entre **Posiciones y Análisis** y **Transacciones**, y la página de cada bróker tiene la misma pestaña solo para ese bróker.

Cada bloque a continuación sigue un patrón: qué responde, una captura de pantalla, sus herramientas y cómo leerlas.

- 📉 **[¿Cuánto puede doler?](#how-much-can-it-hurt)** — las pérdidas que tu cartera realmente sufrió
- 🧩 **[¿Estoy tan diversificado como creo?](#diversification)** — qué posiciones cargan el riesgo, y cuáles se mueven juntas
- ⚖️ **[¿Me están pagando por este riesgo?](#being-paid)** — rentabilidad frente al riesgo, posición por posición y frente a un índice de referencia
- 🔮 **[¿Y si…?](#what-if)** — una crisis pasada, un choque que elijas, o una simulación
- 🚩 **[Avisos y datos faltantes](#notices)** — qué le faltó a los datos, y qué hacer al respecto

---

## 📉 ¿Cuánto puede doler? {: #how-much-can-it-hurt }

¿Cuánto podrías perder, y qué tan mal ha sido ya? Cada cifra aquí es algo que tu cartera realmente experimentó en el período; los depósitos y retiros no cuentan como ganancias ni pérdidas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-hurt" alt="El bloque ¿Cuánto puede doler?: las tarjetas Un mal día, Un mal mes y La peor caída, cada una con su importe, y sus líneas de detalle (peor día realmente visto, cuánto duró la caída, recuperación necesaria, caída en riesgo, promedio más allá de ese umbral); luego Tiempo pasado bajo el pico con el índice de Ulcer, y la Distribución de rendimientos diarios con el umbral de VaR" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Un mal día**, **Un mal mes** — tu pérdida promedio en el peor 5% de los días, o de los períodos de un mes → [VaR condicional](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Umbral de VaR** — en *Distribución de rendimientos diarios*: la pérdida diaria que solo el peor 5% de los días superó → [Valor en riesgo](../../financial-theory/technical-analysis/risk-metrics/value-at-risk.md)
- **Peor día realmente visto** — el peor día del período → [Peor realización](../../financial-theory/technical-analysis/risk-metrics/worst-realization.md)
- **La peor caída** — la caída más profunda desde un máximo hasta un mínimo posterior → [Caída máxima](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Caída en riesgo** — cuán por debajo de su pico estuvo la cartera, dejando de lado su peor 5% de días → [Caída en riesgo](../../financial-theory/technical-analysis/risk-metrics/drawdown-at-risk.md)
- **Promedio más allá de ese umbral** — cuán por debajo de su pico estuvo, en promedio, en esos peores días → [Caída en riesgo condicional](../../financial-theory/technical-analysis/risk-metrics/conditional-drawdown-at-risk.md)
- **Actualmente por debajo del pico** — cuán por debajo de su último máximo está la cartera hoy → [Caída actual](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Índice de Ulcer** — bajo *Tiempo pasado bajo el pico*: cuán profundas y cuán largas fueron las caídas; más bajo es más calmado → [Índice de Ulcer](../../financial-theory/technical-analysis/risk-metrics/ulcer-index.md)

**Cómo leerlo**

- **Distintos horizontes**: las tarjetas van de un día a un mes a la peor caída, así que nunca las sumes.
- **El importe** bajo cada porcentaje es esa pérdida aplicada a tu patrimonio neto.
- **Actualmente por debajo del pico** aparece solo mientras tu cartera está por debajo de su último máximo.
- **Los iconos ? e ⓘ** junto a una cifra abren su página de teoría.

---

## 🧩 ¿Estoy tan diversificado como creo? {: #diversification }

Poseer muchas posiciones no es lo mismo que estar diversificado. Este bloque muestra qué posiciones realmente cargan tu riesgo, y cuáles se mueven juntas tan de cerca que son la misma apuesta.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-diversification" alt="El bloque ¿Estoy tan diversificado como creo?: la frase bajo el título; las tarjetas ¿Cuántas apuestas independientes tengo realmente?, ¿Repartir el dinero logró algo? y ¿Cuánto de mi cartera no se mide aquí?; las posiciones con peso, contribución al riesgo y la barra de dos lados; y ¿Cuáles de estas son la misma apuesta?, con su matriz, Las más parecidas y Las que se compensan" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **¿Cuántas apuestas independientes tengo realmente?** — cuán uniformemente está repartido tu dinero → [Concentración](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **¿Repartir el dinero logró algo?** — cuánto se amortiguan tus posiciones entre sí → [Concentración](../../financial-theory/technical-analysis/risk-metrics/concentration.md)
- **¿Cuánto de mi cartera no se mide aquí?** — efectivo, más posiciones sin precios utilizables → [Calidad de datos](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#excluded-weight)
- **Peso** y **contribución al riesgo** — la parte de tu dinero y de tu riesgo que corresponde a cada posición → [Contribución al riesgo](../../financial-theory/technical-analysis/risk-metrics/risk-contribution.md)
- **¿Cuáles de estas son la misma apuesta?** — cuán de cerca se mueve cada par de posiciones → [Correlación](../../financial-theory/technical-analysis/risk-metrics/correlation.md)

**Cómo leerlo**

- **Una barra roja larga** a la derecha señala una posición que carga más de tu riesgo de lo que sugiere su peso; cuando una destaca, la frase bajo el título la nombra.
- **En la matriz**, los pares azules se mueven juntos, así que tener ambos añade poco; los pares rojos se mueven en direcciones opuestas y se compensan entre sí.
- **Pasa el cursor sobre un cuadrado** para ver su valor en palabras. Las listas *Las más parecidas* y *Las que se compensan* señalan los pares que vale la pena mirar.

---

## ⚖️ ¿Me están pagando por este riesgo? {: #being-paid }

El riesgo vale la pena solo si paga. Este bloque compara el rendimiento de tu cartera y de cada posición con sus oscilaciones — en una tabla y en un gráfico — y, si eliges uno, con un índice de referencia.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-paid" alt="El bloque ¿Me están pagando por este riesgo?, comparado con MSCI World Index: la tabla abierta por las filas Cartera e índice de referencia, con Peso, Volatilidad, Rend. anual, Sortino, Sharpe, Beta y Correlación; el gráfico riesgo/rentabilidad con los puntos de las posiciones y de la cartera dimensionados por peso, el diamante del índice de referencia y la línea discontinua desde la tasa libre de riesgo; y las notas bajo el gráfico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Volatilidad** — cuánto oscilan los rendimientos a lo largo de un año → [Volatilidad](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Rend. anual** — el rendimiento promedio, escalado a un año → [Anualización observada](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — el rendimiento obtenido por cada unidad de oscilaciones a la baja → [Ratio de Sortino](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — el rendimiento obtenido por cada unidad de oscilaciones, al alza o a la baja → [Ratio de Sharpe](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Beta** — cuánto se mueve una posición cuando se mueve el índice de referencia → [Beta y rendimiento activo](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md)
- **Correlación** — cuán de cerca se mueve una posición con el índice de referencia → [Correlación](../../financial-theory/technical-analysis/risk-metrics/correlation.md)
- **Comparado con** y la línea discontinua — tu índice de referencia, y la línea entre mejor y peor pagados → [Selección del índice de referencia](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**Cómo leerlo**

- **Elige un índice de referencia** en **Comparado con** — un fondo indexado (tracker) de un índice mundial amplio es lo más significativo. Se aplica a cada página de Riesgo, y añade las columnas **Beta** y **Correlación**.
- **Por encima de la línea discontinua**, un punto estuvo mejor pagado por su riesgo que el índice de referencia — o, sin índice de referencia, que tu cartera.
- **Haz clic** en el título de una columna para ordenar la tabla, o en una fila para encontrar su punto en el gráfico.
- **La fila Cartera** reproduce las posiciones de hoy, con los pesos de hoy, a lo largo del período — el título dice *sobre la composición actual* — así que no es el historial de tus operaciones. Los rendimientos provienen solo de los precios, sin dividendos ni cupones por ahora.

---

## 🔮 ¿Y si…? {: #what-if }

¿Qué le haría a la cartera que tienes hoy una crisis pasada, o un choque que imaginas — y qué podría deparar el futuro? El bloque empieza cerrado: haz clic en su título para abrirlo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="risk-whatif" alt="El bloque ¿Y si…? abierto: el aviso de Repetición histórica: Parcial, Añadir: Choque hipotético y Simulación, y el cuadro de Repetición histórica tras Ejecutar repetición, con el preajuste Crisis Financiera Global y su período, el cuadro del activo excluido, la frase del total, y la tabla con Peso, Rendimiento, Contribución, Impacto y Efecto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Repetición histórica** — un período real pasado, aplicado a tu cartera tal como está hoy → [Repetición histórica](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)
- **Choque hipotético** — una caída o una subida que asumes para cada clase de activo, sector o región → [Choque hipotético](../../financial-theory/technical-analysis/risk-metrics/hypothetical-shock.md)
- **Simulación** — un rango de futuros posibles, construido a partir de tu propio historial → [Modos de simulación](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md)

**Cómo leerlo**

- **Añade una herramienta** con los botones **Añadir:**; su **×** la cierra y descarta su resultado. Las herramientas que dejes abiertas vuelven la próxima vez, en este navegador.
- **Repetición histórica**: elige una crisis en **Preajuste**, o tu propio **Período**, y luego **Ejecutar repetición**. Las posiciones sin precios para ese período se excluyen, y un botón puede ofrecer un período en el que todas tengan precios.
- **Choque hipotético**: haz clic en un escenario, como *Equity crash*, para ejecutarlo; **Mostrar el choque por grupo de exposición** te permite cambiar sus supuestos.
- **Simulación**: elige un modo — *Historial remezclado* es el recomendado — y un horizonte, luego **Simular**. Lee el cono como un rango de posibilidades, no como un pronóstico.

!!! note "La simulación sigue en beta"

    Su resultado depende en gran medida de cuánta historia contiene el período en comparación con el horizonte — consulta [Por qué la simulación sigue en beta](../../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="whatif-simulation" alt="El cuadro ¿Y si…? Simulación: el aviso de beta y la advertencia del modelo, los cinco modos con Historial remezclado recomendado, horizonte, trayectorias y semilla, y tras Simular las cifras terminales, el cono y Qué asumió esta simulación" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚩 Avisos y datos faltantes {: #notices }

Una cifra de riesgo es tan buena como los precios que la sustentan. Cuando faltan datos o son obsoletos, la pestaña lo dice, y qué cambió eso.

**Herramientas mostradas**

- **Calidad de datos** — precios y tasas faltantes u obsoletos, y las posiciones que quedan fuera → [Calidad de datos](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Cómo leerlo**

- **El aviso en la parte superior** lista los precios y tipos de cambio faltantes u obsoletos: corrígelos con sus botones, o con **Sincronizar** en la esquina superior derecha.
- **El aviso sobre los bloques** indica qué resultados son parciales, y por qué.
- **Un aviso dentro de un bloque** nombra una cifra que no se pudo calcular, con la razón.
- **Un guion (—)** significa que una cifra no se pudo medir: nunca significa cero.
- **Para intentarlo de nuevo**, pulsa **Actualizar**, o vuelve a ejecutar la herramienta ¿Y si…?.

---

## 🔎 Bueno saber {: #good-to-know }

- **La pestaña del Panel cubre toda tu cartera** — cada bróker que posees con una participación por encima del 0% — dentro del rango de fechas y la divisa del Panel. Ignora el filtro de bróker: un subtítulo lo dice, y los importes bajo los porcentajes se ocultan mientras un filtro está activo.
- **En la página de un bróker**, la pestaña muestra los mismos bloques solo para ese bróker.
- **Cambiar el período o la divisa** recalcula cada bloque y borra los resultados de ¿Y si…?: vuelve a ejecutarlos.
- **Detalles del cálculo**, plegados al final de cada bloque, muestran sobre cuántos datos descansan las cifras.

---

## 🔗 Relacionado {: #related }

- 🧪 **[Pestaña Correlación](../assets/correlation.md)** — las mismas preguntas, planteadas sobre una selección de activos que tú eliges
- 📚 **[Métricas de Riesgo](../../financial-theory/technical-analysis/risk-metrics/index.md)** — la teoría detrás de cada cifra; el icono de libro de cada bloque la abre
- 📊 **[Panel](index.md)** — las otras pestañas, el rango de fechas, la divisa y el filtro de bróker
- 🏦 **[Brókers](../brokers/index.md)** — la página de cada bróker, con su propia pestaña Riesgo
- 🛠️ **[Detalles técnicos](../../developer/frontend/components/features/risk-lab.md#dashboard-risk-tab)** — para desarrolladores: cómo funciona esta pestaña por dentro
