# 🎯 Selección del índice de referencia

Cada cifra relativa lleva un pasajero invisible: aquello contra lo que se midió. «La cartera superó al mercado por tres puntos» no es una afirmación sobre la cartera — es una afirmación sobre la cartera **y** lo que se llamara «el mercado». Cambie el segundo término y el veredicto cambia con él, sin que se haya movido una sola posición.

Esta página trata sobre ese segundo término. La elección de comparación no es una preferencia de visualización aplicada después del análisis: es parte del resultado.

---

## 🔢 Qué significa "relativo" {: #what-relative-means }

Dadas una serie de rendimiento primaria $r_p$ y una serie de comparación $r_b$ observadas en las mismas fechas, LibreFolio deriva las cifras relativas del par.

**Rendimiento activo** es la diferencia entre los dos rendimientos del período de tenencia, cada uno compuesto durante la ventana compartida:

$$\text{Active} = \left[ \prod_{t=1}^{N} (1 + r_{p,t}) - 1 \right] - \left[ \prod_{t=1}^{N} (1 + r_{b,t}) - 1 \right]$$

Es una diferencia de rendimientos compuestos durante la ventana realmente compartida por las dos series — no es una cifra anualizada, ni un ratio.

**Beta** mide con qué fuerza respondió la serie primaria a la de comparación:

$$\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}$$

El denominador es la clave de toda la página: beta es la covarianza **dividida por la varianza del índice de referencia**. Todo lo que hace el índice de referencia — o deja de hacer — se propaga a la cifra.

**Correlación** se calcula con el mismo estimador que la [matriz de correlación](correlation.md), y responde si la comparación es siquiera relevante: una beta medida contra algo que la cartera no sigue describe una relación que no existe.

---

## 💡 Interpretación {: #interpretation }

Las tres cifras responden a preguntas diferentes y están pensadas para leerse juntas.

| Cifra | Pregunta que responde |
|---|---|
| Rendimiento activo | ¿Terminó la cartera la ventana compartida por delante o por detrás de la comparación? |
| Beta | ¿Cuán amplificada fue la respuesta de la cartera a los movimientos de la comparación? |
| Correlación | ¿Fue la comparación una referencia significativa en absoluto? |

La correlación es lo primero en la práctica. El rendimiento activo y la beta siguen estando aritméticamente bien definidos contra una comparación que la cartera ignora por completo, y ahí carecen de sentido — una correlación baja es la señal de que el índice de referencia era la pregunta equivocada, no de que la cartera fuera la respuesta equivocada.

### 🧭 Por qué la elección ya es la mitad del veredicto {: #why-the-choice-is-already-half-the-verdict }

Una única cartera global de renta variable comparada contra un índice mundial amplio, contra un índice nacional y contra un fondo de bonos producirá tres rendimientos activos diferentes, tres betas diferentes y tres impresiones diferentes — a partir de las mismas posiciones en las mismas fechas. Ninguna de las tres es un error de medición. Responden a tres preguntas diferentes, y la pregunta se eligió cuando se eligió el índice de referencia.

La consecuencia práctica es una regla de comparabilidad: **dos cifras relativas solo pueden compararse entre sí si se midieron contra el mismo índice de referencia**. Una beta no es una propiedad de una cartera; es una propiedad de una cartera *y* una referencia. LibreFolio registra el activo de comparación en los propios metadatos del resultado precisamente para que una cifra nunca pueda separarse de la referencia que la produjo.

---

## 🧮 Qué puede servir como índice de referencia {: #what-can-serve-as-a-benchmark }

La comparación no es arbitraria. El análisis toma un **activo real que existe en sus datos** como su referencia, identificado explícitamente, y de eso se derivan tres cosas.

**Debe existir.** Una comparación contra un activo desconocido no se descarta silenciosamente ni se reemplaza por un valor predeterminado: el análisis no devuelve ningún valor, informa parámetros inválidos y nombra el activo que se solicitó.

**Debe tener un historial de precios utilizable.** La serie del índice de referencia se prepara exactamente igual que las posiciones bajo análisis, en el mismo calendario compartido y en la misma moneda objetivo. Si no se puede construir una serie utilizable para él, el resultado no está disponible en lugar de ser aproximado.

El selector de índice de referencia pregunta al motor qué activos tienen un historial de precios utilizable propio durante el período de análisis y en la moneda objetivo, y lista los demás por separado, en modo de solo lectura, cada uno con las razones del motor. Un índice de referencia elegido anteriormente que no pasa esta verificación permanece elegido y mostrado en el selector, pero no se mide nada contra él. Si la verificación no se puede realizar, no se bloquea nada.

**Debe moverse.** Beta divide por la varianza de la serie de comparación, por lo que un índice de referencia que nunca se mueve no tiene varianza por la que dividir: beta vuelve indefinida y la correlación con él también, y ambas generan una advertencia explícita en lugar de un número. Por eso una referencia plana — una constante, una tasa de rendimiento fija hipotética — no puede funcionar como índice de referencia aquí. La restricción no es una política de la que se pueda prescindir; es la aritmética del ratio.

!!! info "Un índice de referencia no es un umbral"

    La comparación responde a «¿comparado con qué?», no a «¿es esto bueno?». Una cartera que se queda atrás de un índice de referencia en ascenso y una que cae menos que un índice de referencia en desplome ambas producen una cifra; ninguna de las dos cifras sabe si el inversor debería estar satisfecho. Ese juicio necesita el objetivo, que vive fuera de la métrica.

---

## 📏 La ventana compartida {: #the-shared-window }

Dos series rara vez cubren exactamente las mismas fechas, por lo que la comparación se calcula sobre la **intersección** de los dos calendarios: en cada fecha compartida, cada serie aporta sus rendimientos desde la fecha compartida anterior — para la primera, desde la fecha anterior de la primaria — compuestos en uno. Un índice de referencia cotizado en días que la primaria omite — un criptoactivo el fin de semana, junto a una cartera leída en sus [días de observación](data-quality.md#coverage) — conserva esos movimientos.

Tres consecuencias se publican con el resultado.

**Se aplica un mínimo.** Por debajo de 20 observaciones compartidas la comparación no se calcula en absoluto: el resultado vuelve como no disponible con una razón de historial insuficiente que incluye tanto el número de observaciones compartidas encontradas como el número requerido. Un índice de referencia que apenas se superpone con su historial no produce ninguna cifra en lugar de una frágil.

**Se informa la cobertura.** El resultado registra qué fracción de las fechas propias de la serie primaria sobrevivió a la intersección — es decir, en cuántas de sus fechas el índice de referencia elegido tuvo un rendimiento propio. Un índice de referencia lanzado a mitad de su período de tenencia no compara silenciosamente medio período; lo dice.

**El factor de anualización se vuelve a medir en la ventana compartida.** Dado que la intersección es generalmente más corta y dispersa que la ventana de análisis completa, cualquier cantidad anualizada en la comparación se escala por un factor medido en la muestra común en lugar de heredarse del análisis más amplio — la misma lógica de factor observado descrita en [Anualización observada](observed-annualization.md), aplicada a la superposición.

---

## 📈 La línea de riesgo/rendimiento {: #the-risk-return-line }

En la pestaña **Riesgo** del Panel y de la página de un bróker, el nivel **¿Me están pagando por este riesgo?** dibuja un gráfico de riesgo frente a rendimiento — volatilidad anualizada en el eje horizontal, rendimiento anual medio en el vertical. Muestra un punto por cada posición, dimensionado por su peso en la cartera; uno para la propia cartera, tal como está compuesta hoy y reproducida durante la ventana; uno para el índice de referencia, dibujado como un rombo; y una línea discontinua recta.

La línea comienza en el eje vertical en la **tasa libre de riesgo que utiliza la página** — la misma tasa que sus cifras de Sharpe y Sortino, que hoy es 0 en el Panel y en la página de un bróker — y atraviesa **el índice de referencia**. En teoría, esta es la Línea del Mercado de Capitales, que pasa por la *cartera de mercado*; aquí el índice de referencia es lo que sustituye al mercado:

$$R = R_f + \frac{R_b - R_f}{\sigma_b}\,\sigma$$

donde:

- $\sigma$ es una volatilidad anualizada, y $R$ el rendimiento anual medio que alcanza la línea a esa volatilidad;
- $R_f$ es la tasa libre de riesgo que utiliza la página;
- $R_b$ y $\sigma_b$ son el rendimiento anual medio del índice de referencia — su rendimiento medio por período, escalado a un año — y su volatilidad anualizada.

**Lectura.** La pendiente, $(R_b - R_f)/\sigma_b$, es el [ratio de Sharpe](sharpe-ratio.md) del índice de referencia: su rendimiento medio por encima de la tasa libre de riesgo por unidad de volatilidad. Un punto por encima de la línea estuvo mejor pagado por su riesgo que el índice de referencia — más rendimiento medio por encima de la tasa libre de riesgo por unidad de volatilidad, un ratio de Sharpe más alto. Un punto por debajo estuvo peor pagado. Como toda cifra relativa en esta página, eso es una comparación con la referencia, no una calificación.

**Elección del índice de referencia para ello.** Dado que el índice de referencia representa «el mercado», un **índice global amplio** — por ejemplo, un fondo indexado a un índice mundial de renta variable — es el sustituto más significativo. Un índice nacional, un índice sectorial o un fondo de bonos aún dibujan una línea, pero la convierten en una comparación con esa referencia más estrecha: véase [Por qué la elección ya es la mitad del veredicto](#why-the-choice-is-already-half-the-verdict).

**Sin índice de referencia elegido** — o uno que no pudo medirse durante la ventana — la línea atraviesa **su propia cartera** en su lugar. Estar por encima de ella significa entonces mejor pagado que la cartera en su conjunto, y la pendiente es el ratio de Sharpe de la cartera.

**Un índice de referencia que usted posee** se dibuja una sola vez, no como dos puntos: es el propio punto de su posición, en su peso, con el estilo del índice de referencia, y la línea pasa por él.

**En la página de Activos.** Su [pestaña Correlación](../../../user/assets/correlation.md#what-did-each-pay), que compara una selección de activos que usted compone, dibuja la misma línea cuando se elige un índice de referencia y se mide durante la ventana: comienza en la tasa libre de riesgo que utiliza la página — 0 hoy, como en el Panel — y pasa por el rombo del índice de referencia, por lo que su pendiente es el ratio de Sharpe del índice de referencia y un punto por encima de ella estuvo mejor pagado por su riesgo que el índice de referencia. Un índice de referencia que es uno de los activos seleccionados se dibuja una sola vez, como el propio punto de ese activo con el estilo del índice de referencia, y la línea pasa por él. Sin índice de referencia, o con uno que no pudo medirse durante la ventana, no se dibuja ninguna línea, porque ninguna cartera puede ocupar el lugar del índice de referencia — una selección no tiene pesos y por lo tanto no tiene un todo propio por el que trazar una línea — y el gráfico muestra la disyuntiva y deja el juicio en sus manos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="¿Qué pagó cada uno de estos por su riesgo? en la pestaña Correlación, con el S&P 500 como índice de referencia: la tabla abierta por su fila tintada, y el gráfico con los círculos de los activos, el rombo del índice de referencia y la línea discontinua desde la tasa libre de riesgo pasando por él" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Solo precios, por ahora"

    Los rendimientos de este gráfico provienen únicamente de series de precios: los cupones y dividendos aún no están incluidos. Una posición que reparte una gran parte de su rendimiento como ingresos, por lo tanto, se sitúa más abajo de lo que la situaría su rendimiento total — y cuando el índice de referencia lo hace, la línea se inclina hacia abajo con él.

---

## ⚠️ Limitaciones {: #limitations }

!!! warning "El índice de referencia es una elección, y la elección no es neutral"

    Debido a que tanto la beta como el signo del rendimiento activo dependen de la referencia, una comparación elegida después de ver los resultados no es una medición — es una narrativa. La secuencia honesta es decidir qué intenta seguir la cartera *antes* de preguntar cómo se desempeñó frente a ello.

!!! warning "Las cifras relativas no se acumulan"

    Las betas y los rendimientos activos medidos contra referencias diferentes pertenecen a escalas diferentes. Comparar la beta de un activo contra un índice nacional con la beta de otro activo contra un índice mundial produce una comparación de dos números no relacionados que casualmente comparten un nombre.

!!! warning "Los dos lados no siempre son el mismo tipo de rendimiento"

    El activo de comparación siempre aporta el rendimiento de su propia serie de precios, mientras que el lado primario mantiene la base de rendimiento de lo que se está analizando — un activo o una cartera completa. El resultado registra qué base se utilizó en el lado primario, y vale la pena verificarlo antes de interpretar un pequeño rendimiento activo como significativo.

!!! warning "Un calendario compartido oculta lo que descarta"

    Solo se comparan las fechas presentes en ambas series. Si la referencia falta precisamente durante el tramo turbulento que más importa, la comparación ve ese tramo como un único paso compuesto — o no lo ve en absoluto, antes de la primera fecha compartida de la referencia — en lugar de como se desarrolló. La cifra de cobertura es lo que hace visible esa pérdida — léala antes de leer la beta.

---

## 🔗 Relacionado {: #related }

- 📈 **[Beta y rendimiento activo](beta-active-return.md)** — las dos cifras que determina esta elección
- 🔗 **[Correlación](correlation.md)** — si la referencia elegida es relevante en absoluto
- 📅 **[Anualización observada](observed-annualization.md)** — por qué el factor se vuelve a medir en la superposición
- 🧪 **[Calidad de datos](data-quality.md)** — qué descarta el calendario compartido, y cómo se informa
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — la pendiente de la línea de riesgo/rendimiento
