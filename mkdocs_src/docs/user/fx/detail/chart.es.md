# 📉 Gráfico interactivo

El corazón de la página de detalle del par: el historial del tipo de cambio del par durante el periodo seleccionado.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Gráfico de detalle de FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Vista Abs o %

Cambia con **Abs** / **%** en la esquina superior izquierda del gráfico; la página se abre en la vista %.

- 📊 **%** — la variación desde el primer día del periodo. Las superposiciones también parten de 0 %, así que sus movimientos se comparan de un vistazo.
- 📈 **Abs** — el tipo de cambio en sí, p. ej. 1 EUR = 1.0845 USD.

---

## 🔍 Zoom, desplazamiento y periodo

| Acción | Escritorio | Móvil |
|--------|---------|--------|
| **Zoom** | Rueda del ratón | Pellizcar |
| **Desplazar** | Clic y arrastrar | Arrastrar con dos dedos (un dedo desplaza la página) |

- **Periodo**: los preajustes **1S** a **2A**, **YTD** y **Todo**, o **Personalizado** (un número de
  días, semanas, meses o años hacia atrás desde hoy); haz clic en las fechas para elegirlas en un
  calendario. Los dos extremos deben ser días distintos: el primer día en el que haces clic no se
  puede volver a seleccionar, y una fecha escrita igual al otro extremo se vuelve roja. Aparecen más
  preajustes cuando la barra de herramientas tiene espacio. Las páginas de la misma pestaña del
  navegador comparten el periodo.
- En un periodo largo, el gráfico agrupa los tipos de cambio por semana o por mes y muestra una insignia
  **Semanal** o **Mensual**: haz zoom para ver los tipos de cambio diarios.
- En una pantalla estrecha, el eje muestra menos fechas y más cortas; la primera y la última siempre
  se mantienen.

??? info "📅 Historial más corto que el periodo — cuando el gráfico empieza más tarde"

    Un aviso muestra la fecha desde la que hay datos disponibles. **Sincronizar** puede obtener tipos
    de cambio más antiguos, si el proveedor los publica; si no, introdúcelos en el [Editor de datos](data-editor.md).

---

## 💬 Información emergente

Pasa el cursor sobre el gráfico, o tócalo en el móvil, para ver:

- 📅 la **fecha** (o la semana o el mes, cuando el gráfico agrupa los tipos de cambio);
- 💱 el **tipo de cambio** y el valor de cada superposición;
- 📊 la **variación desde el inicio del periodo**: Δ y % en la vista Abs, % en la vista %;
- ⚠️ **Obsoleto: N día(s) de antigüedad** en los días sin un nuevo tipo de cambio, como los fines de semana
  y los días festivos.

---

## 🔁 Rentabilidad móvil {: #rolling-return }

Dos botones encima del gráfico eligen lo que dibuja: **Precios** (el historial de tipos de cambio, como arriba)
y **Rentabilidad móvil**.

En **Rentabilidad móvil** cada punto responde a *¿cuánto se ha movido el tipo de cambio en los
últimos N días?* Compara el tipo de cambio de ese día con el de N días naturales antes. Ejemplo: en
EUR → USD con la ventana móvil **3M** (90 días), si el tipo de cambio es 1.0845 hoy y era 1.0500 hace noventa días,
el punto marca **+3.3 %**. Por encima de cero, la primera moneda compraba más de la segunda que N días
antes; por debajo de cero, menos.

- 🗓️ **Ventana móvil** — junto a los dos botones: **1S**, **1M**, **3M**, **1A** o **Personalizado** (un
  número entero de semanas, meses o años). Hasta que elijas una, la ventana móvil es automática: el mayor
  preajuste que encaja con el periodo en pantalla. La ventana móvil puede ser más larga que el periodo:
  LibreFolio lee los tipos de cambio más antiguos que necesita. El botón **?** abre la
  [misma explicación](../../assets/detail/chart.md#rolling-return) que se da para los activos, y la
  vista previa de [Ajustes del gráfico](../chart-settings.md#rolling-return-view) también dibuja
  esta vista.
- 💱 **Comparar con otro par** — añade un **Par FX** en el panel [Señales](signals.md#data-comparison):
  cada par comparado dibuja su propia rentabilidad móvil, con la misma ventana móvil. En este modo el panel
  ofrece solo estas comparaciones; tus otras señales permanecen guardadas y vuelven con **Precios**.
- 🔄 **Dirección** — la rentabilidad sigue la dirección que muestra la página, EUR → USD o USD → EUR.
- 📏 ✏️ **Medida** y **Editar tipos de cambio** están ocultos: trabajan sobre los tipos de cambio, así que pertenecen a **Precios**.
- 💾 **Recordado** — el modo y la ventana móvil se guardan con los ajustes del gráfico de este par, en este
  navegador. La tarjeta del par en la lista de pares FX los comparte: una tarjeta en **Rentabilidad móvil**
  abre la página en ese modo, y la página se abre de nuevo en el modo en que la dejaste. Volver a
  **Precios** es inmediato.

Cambiar el periodo, la ventana móvil, la dirección o los pares comparados, o hacer clic en **Actualizar**,
vuelve a calcular la rentabilidad, y se muestra un indicador de carga hasta que llega la respuesta. Si
no se puede calcular ninguna rentabilidad, el gráfico muestra el motivo en lugar de una curva.

---

## 🧰 Botones del gráfico

- 📏 **Medida** — consulta [Medidas](measures.md). Solo en **Precios**.
- ✏️ **Editar tipos de cambio** — consulta [Editor de datos](data-editor.md). Solo en **Precios**.
- ⚙️ **Estética** — colores, relleno, cuadrícula y rangos de los ejes, como en [Ajustes del gráfico](../chart-settings.md).
- 📊 El panel **Señales** encima del gráfico — consulta [Señales](signals.md).

---

## 🔗 Relacionado

- ⚙️ **[Ajustes del gráfico](../chart-settings.md)** — Aspecto del gráfico y señales superpuestas
- 📈 **[Señales](signals.md)** — Indicadores técnicos en el gráfico
