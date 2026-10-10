# 🧪 Pestaña Correlación

La pestaña **Correlación** de la [página de Activos](index.md) plantea las mismas preguntas a una **selección de activos** que reúnes — activos que posees, activos que solo observas o las posiciones de un bróker. Ábrela desde **Activos** en la barra lateral y luego la pestaña **Correlación** en la barra de herramientas. Una selección no tiene ponderaciones, así que la pestaña muestra porcentajes y ratios, nunca dinero: para tu propio dinero, consulta la [pestaña Riesgo](../dashboard/risk.md) del Panel.

Cada bloque a continuación sigue un patrón: qué responde, una captura de pantalla, sus herramientas y cómo leerlas.

- 🧺 **[Construcción de la selección](#building-the-selection)** — qué activos se comparan
- 🕸️ **[Correlación](#correlation)** — cuáles de ellos se mueven juntos
- 📉 **[¿Cuánto dolió cada uno de estos?](#how-much-did-each-hurt)** — las pérdidas de cada uno
- ⚖️ **[¿Cuánto pagó cada uno de estos por su riesgo?](#what-did-each-pay)** — riesgo frente a rentabilidad
- ⏮️ **[¿Qué pasaría si…?](#what-if)** — un episodio pasado, reproducido
- 🚩 **[Avisos y datos faltantes](#each-section-speaks-for-itself)** — lo que faltaba en los datos

---

## 🧺 Construcción de la selección {: #building-the-selection }

La tarjeta en la parte superior responde a la pregunta *¿qué activos se comparan?* Cada chip es un activo seleccionado, y la pestaña recuerda tu selección en este navegador.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-asset-picker" alt="El panel + abierto sobre la tarjeta de selección: búsqueda, filtros Tipo y Divisa, dos activos marcados con Añadir 2 y, en solo lectura, los activos que no se pueden analizar en el periodo, cada uno con su motivo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Comprobación de elegibilidad** — si un activo tiene suficientes precios en el periodo para ser analizado → [Calidad de datos](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Cómo leerlo**

- **Añade activos con el +**, elimina uno con su **×**, o cambia muchos a la vez con **Seleccionar todo**, **Deseleccionar todo**, **Invertir** y **Mis activos** — hasta **100 activos**.
- **El contador** — *3 en el análisis, de 42 que se pueden analizar* — cuenta los activos seleccionados que se están analizando, de todos los que podrían estarlo en el periodo definido en la barra de herramientas.
- **Un chip con línea discontinua** no se puede analizar en este periodo: permanece seleccionado, pero fuera de los resultados. **Un chip ámbar** se analiza, con una advertencia. Pasa el cursor o toca un chip para leer el motivo.
- **Si el periodo deja algunos activos sin precios**, una franja ámbar ofrece **Usar el periodo en el que todos tienen precios**, que mueve las fechas de la página para que encajen todos.

---

## 🕸️ Correlación {: #correlation }

Esta sección responde a la pregunta *¿cuáles de estos se mueven juntos?* — para detectar los activos que en realidad son la misma apuesta y los que amortiguan a los demás.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-correlation" alt="La sección Correlación con cinco activos: la matriz triangular con su leyenda, botones de orden e insignias de sector y región; Los más parecidos emparejan RE Loan Roma con RE Loan Milano en 0,94, casi idénticos, y Los que se compensan están vacíos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Coeficiente de correlación (ρ)** — cuán estrechamente se movieron juntos dos activos, desde −1 (siempre opuestos) hasta +1 (siempre juntos) → [Correlación](../../financial-theory/technical-analysis/risk-metrics/correlation.md#interpretation)
- **Ordenar por similitud** — el orden predeterminado: los activos estrechamente vinculados se sitúan uno al lado del otro, de modo que los grupos redundantes aparecen como bloques → [Correlación](../../financial-theory/technical-analysis/risk-metrics/correlation.md#why-the-matrix-answers-am-i-diversified)

**Cómo leerlo**

- **Un cuadrado por par**: azul cuando los dos activos se mueven juntos, rojo cuando se mueven en direcciones opuestas, pálido cuando se mueven de forma independiente. Pasa el cursor o toca para ver el valor en palabras.
- **Empieza por las dos listas**: **Los más parecidos** nombra los pares que son casi la misma exposición, **Los que se compensan** los pares que se amortiguan mutuamente. Una lista vacía es un hallazgo. Haz clic en un par para encontrarlo en la matriz.
- **Un guion no es un cero**: el par no se pudo medir — demasiado poca historia, o un precio que nunca se movió.
- **Los botones de orden** reorganizan la matriz; nunca cambian un valor.

---

## 📉 ¿Cuánto dolió cada uno de estos? {: #how-much-did-each-hurt }

Esta sección pone cada activo en la misma escala de daño: sus peores pérdidas en el periodo, y cuánto sigue por debajo de su máximo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-hurt-table" alt="La tabla ¿Cuánto dolió cada uno de estos?: una fila por activo con Mal día, Mal mes, Peor caída y cuánto duró, Por debajo del máximo ahora y Subida hasta el máximo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Mal día** — la pérdida promedio en el peor 5% de los días (CVaR al 95%) → [VaR condicional](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Mal mes** — lo mismo en tramos reales de un mes → [VaR condicional](../../financial-theory/technical-analysis/risk-metrics/conditional-value-at-risk.md)
- **Peor caída** — la caída más profunda desde un máximo; *duró N d* cuenta los días hasta que el activo volvió allí, o hasta el final del periodo → [Caída máxima](../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md)
- **Por debajo del máximo ahora** — cuánto está por debajo de su nivel más alto en el periodo → [Caída actual](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md)
- **Subida hasta el máximo** — la ganancia necesaria para volver allí: estar un 20% por debajo requiere +25% → [Lo que hace falta para recuperarse](../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md#what-it-takes-to-get-back)

**Cómo leerlo**

- **Cada columna es su propio horizonte**, desde un día hasta todo el periodo: compara los activos a lo largo de una columna, nunca sumes las columnas.
- **No es un ranking**: la tabla se abre en el orden de tu selección. Haz clic en el título de una columna para ordenarla, o pasa el cursor por encima para ver qué mide.
- **En un periodo corto**, **Mal día** y **Mal mes** pueden quedar vacíos mientras las columnas de caída están rellenas: necesitan más historial.

---

## ⚖️ ¿Cuánto pagó cada uno de estos por su riesgo? {: #what-did-each-pay }

Esta sección compara riesgo y recompensa — cuánto osciló cada activo y qué rentabilidad media anual dio — en una tabla y un gráfico. Con un índice de referencia elegido en *Comparado con*, también muestra cómo se movió cada activo con él.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="¿Cuánto pagó cada uno de estos por su riesgo? con el S&P 500 como índice de referencia: su fila coloreada abriendo la tabla, la línea del periodo y el gráfico con los círculos de los activos, el rombo del índice de referencia y la línea discontinua" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Volatilidad** — cuánto oscilaron los rendimientos, en base anual → [Volatilidad](../../financial-theory/technical-analysis/risk-metrics/volatility.md)
- **Rent. anual** — la *rentabilidad media anual*: la rentabilidad media del periodo, escalada a un año → [Anualización observada](../../financial-theory/technical-analysis/risk-metrics/observed-annualization.md)
- **Sortino** — la rentabilidad obtenida por unidad de oscilación a la baja → [Ratio de Sortino](../../financial-theory/technical-analysis/risk-metrics/sortino-ratio.md)
- **Sharpe** — la rentabilidad obtenida por unidad de volatilidad → [Ratio de Sharpe](../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)
- **Beta** — con un índice de referencia: cuánto se movió el activo cuando se movió el índice de referencia → [Beta y rendimiento activo](../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md#interpretation)
- **Correlación** — con un índice de referencia: cuán estrechamente se movieron juntos los dos → [Selección del índice de referencia](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#interpretation)
- **Línea riesgo/rentabilidad** — con un índice de referencia: la línea discontinua trazada a través de él en el gráfico → [La línea riesgo/rentabilidad](../../financial-theory/technical-analysis/risk-metrics/benchmark-selection.md#the-risk-return-line)

**Cómo leerlo**

- **No es un ranking**: la tabla se abre con la fila del índice de referencia y luego tu selección en su propio orden. Haz clic en el título de una columna para ordenarla.
- **La línea bajo la tabla** indica el periodo exacto que hay detrás de las cifras, y avisa cuando es más corto que el tuyo — normalmente por un activo con un historial más corto.
- **En el gráfico**, más a la derecha significa más oscilación y más arriba significa más rentabilidad media; el índice de referencia es el rombo. Un círculo por encima de la línea discontinua estuvo mejor remunerado por su riesgo que el índice de referencia. Haz clic en una fila o en un círculo para resaltar ese activo en ambos.

!!! warning "La rentabilidad media anual no es la rentabilidad que viviste"

    En un activo muy volátil, la rentabilidad realmente vivida es menor: no leas la altura de un punto como lo que ganó el activo. Además, procede solo de los precios — los cupones y dividendos aún no están incluidos.

### 🎯 Elegir el índice de referencia {: #choosing-the-benchmark }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-benchmark-picker" alt="El selector Comparado con abierto: búsqueda, filtros Tipo y Divisa, los activos utilizables y, después, en solo lectura, los no utilizables en este periodo, cada uno con su motivo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Un único índice de referencia para cada página de riesgo**: tu elección en *Comparado con* también se aplica a las páginas de riesgo del Panel, del bróker y de los activos, para que sigan siendo comparables.
- **Su fila abre la tabla**, con un guion en las columnas **Beta** y **Correlación**: el índice de referencia no se compara consigo mismo. También puede ser uno de tus activos seleccionados.
- **Los activos que no se pueden medir en el periodo** se listan aparte en el selector, en solo lectura. Un índice de referencia entre ellos permanece elegido, pero no se usa hasta que elijas un periodo que le vaya bien.

---

## ⏮️ ¿Qué pasaría si…? {: #what-if }

Esta sección responde a la pregunta *¿cómo atravesó cada uno de estos un episodio pasado real?* — una crisis incorporada o un periodo que elijas, repetido con rentabilidades reales. Haz clic en su título para abrirla. Solo se ofrece la repetición histórica: un choque hipotético o una simulación necesitarían ponderaciones.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="¿Qué pasaría si…? tras Ejecutar repetición: el cuadro de activos excluidos, agrupados por motivo, con el botón que repite el periodo más corto, encima de la tabla con Rentabilidad y Efecto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Repetición histórica** — la rentabilidad real de cada activo durante un periodo pasado → [Repetición histórica](../../financial-theory/technical-analysis/risk-metrics/historical-replay.md)

**Cómo leerlo**

- **Elige un Preajuste**, como la *Crisis Financiera Global*, o define el **Periodo**, y luego pulsa **Ejecutar repetición**. Cambiar la selección o las fechas de la página borra el resultado.
- **La tabla** muestra la **Rentabilidad** de cada activo, con los peores primero, con una barra: roja para una pérdida, verde para una ganancia. No hay total: una selección no tiene ponderaciones que sumar.
- **Los activos sin precios en los extremos del periodo** se excluyen y se listan encima de la tabla, con el motivo. Cuando es posible, un botón repite el periodo más corto en el que todos tienen precios.

---

## 🚩 Avisos y datos faltantes {: #each-section-speaks-for-itself }

Cuando algo va mal con los datos, la pestaña lo indica una vez, justo debajo de la tarjeta de selección, y nombra los resultados a los que afecta.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-notice" alt="Parte superior de la pestaña Correlación: el banner plegado de calidad de datos, el aviso Algunos resultados son parciales con sus insignias Mediciones afectadas, y el banner ámbar de la sección Correlación No disponible para los datos seleccionados" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Herramientas mostradas**

- **Calidad de datos** — precios y tipos de cambio faltantes o desactualizados, y los resultados que vuelven parciales → [Calidad de datos](../../financial-theory/technical-analysis/risk-metrics/data-quality.md)

**Cómo leerlo**

- **El banner de calidad de datos** enumera lo que hay que corregir, cada problema con su acción, como **Sincronizar precios** o **Sincronizar tipos**. Haz clic en él para abrir la lista.
- **El aviso** debajo nombra los resultados **parciales** y su causa. Un resultado parcial sigue mostrando sus cifras: léelas teniendo en cuenta esa causa.
- **El banner ámbar propio de una sección** significa que un resultado no se obtuvo en absoluto, a menudo porque el periodo es demasiado corto: elige uno más largo o sincroniza los precios.
- **¿Qué pasaría si…?** informa de sus propios problemas dentro de su sección.

---

## 🔎 Conviene saber {: #reading-the-numbers }

- **Un periodo para todos los activos.** Cada cifra cubre los mismos días para cada activo seleccionado, de modo que las filas se pueden comparar. Un activo con un historial más corto acorta ese periodo para todos ellos, y sus cifras cambian: esto es esperable → [Calidad de datos](../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs)
- **Una única divisa.** Las rentabilidades se miden en tu **Divisa predeterminada**, definida en [Preferencias](../settings/preferences.md) (la predeterminada de la instancia si nunca elegiste una), incluidos los movimientos de los tipos de cambio.
- **Un guion no es un cero.** La cifra no se pudo medir para ese activo en este periodo; pasa el cursor o toca para leer el motivo.
- **Otra página, otra cifra.** Otra página u otra selección mide en días diferentes: compara cifras solo si cubren el mismo periodo.

---

## 🔗 Relacionado {: #related }

- 📋 **[Lista de activos](index.md)** — la pestaña Activos, su barra de herramientas y su rango de fechas
- 🛡️ **[Pestaña Riesgo del Panel](../dashboard/risk.md)** — las mismas preguntas, para tu propia cartera
- 📊 **[Métricas de riesgo](../../financial-theory/technical-analysis/risk-metrics/index.md)** — la teoría detrás de cada sección de esta pestaña
- 🛠️ **[Detalles técnicos](../../developer/frontend/components/features/risk-lab.md)** — para desarrolladores: cómo funciona esta pestaña por dentro
