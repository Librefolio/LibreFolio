# 📉 Gráfico interactivo

El corazón de la página de detalle del par: el historial de cotización del par durante el periodo seleccionado.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Gráfico de detalle FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Vista Abs o %

Cambia con **Abs** / **%** en la esquina superior izquierda del gráfico; la página se abre en la vista %.

- 📊 **%** — el cambio desde el primer día del periodo. Las superposiciones también empiezan desde 0 %, así que sus movimientos se pueden comparar de un vistazo.
- 📈 **Abs** — la cotización en sí, p. ej. 1 EUR = 1.0845 USD.

---

## 🔍 Zoom, desplazamiento y periodo

| Acción | Escritorio | Móvil |
|--------|---------|--------|
| **Zoom** | Rueda del ratón | Pellizcar |
| **Desplazar** | Clic y arrastrar | Arrastrar con dos dedos (un dedo desplaza la página) |

- **Periodo**: los preajustes **1W** a **2Y**, **YTD** y **Todo**, o **Personalizado** (un número de días, semanas, meses o años hacia atrás desde hoy); haz clic en las fechas para elegirlas en un calendario. Aparecen más preajustes cuando la barra de herramientas tiene espacio. Las páginas de la misma pestaña del navegador comparten el periodo.
- En un periodo largo, el gráfico agrupa las cotizaciones por semana o mes y muestra una insignia **Semanal** o **Mensual**: amplía para ver las cotizaciones diarias.
- En una pantalla estrecha, el eje muestra menos fechas y estas más cortas; la primera y la última siempre permanecen.

??? info "📅 Historial más corto que el periodo — cuando el gráfico empieza más tarde"

    Un banner muestra la fecha a partir de la cual hay datos disponibles. **Sincronizar** puede obtener cotizaciones más antiguas, si el proveedor las publica; de lo contrario, introdúcelas en el [Editor de datos](data-editor.md).

---

## 💬 Información emergente

Pasa el cursor sobre el gráfico, o tócalo en el móvil, para ver:

- 📅 la **fecha** (o la semana o el mes, cuando el gráfico agrupa las cotizaciones);
- 💱 la **cotización** y el valor de cada superposición;
- 📊 el **cambio desde el inicio del periodo**: Δ y % en la vista Abs, % en la vista %;
- ⚠️ **Obsoleto: N día(s) de antigüedad** en días sin una nueva cotización, como fines de semana y días festivos.

---

## 🧰 Botones del gráfico

- 📏 **Medida** — consulta [Medidas](measures.md).
- ✏️ **Editar cotizaciones** — consulta [Editor de datos](data-editor.md).
- ⚙️ **Estética** — colores, relleno, cuadrícula y rangos de ejes, como en [Ajustes del gráfico](../chart-settings.md).
- 📊 El panel **Señales** por encima del gráfico — consulta [Señales](signals.md).

---

## 🔗 Relacionado

- ⚙️ **[Ajustes del gráfico](../chart-settings.md)** — Aspecto del gráfico y señales de superposición
- 📈 **[Señales](signals.md)** — Indicadores técnicos en el gráfico
