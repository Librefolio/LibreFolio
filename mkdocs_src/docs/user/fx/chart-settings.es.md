# ⚙️ Ajustes del gráfico

La ventana **Ajustes del gráfico** cambia el aspecto de los gráficos y qué superposiciones dibujan. Sirve tanto
para la [lista de FX](index.md) como para la [lista de activos](../assets/index.md), y cada lista mantiene su propia
configuración: cambiar los gráficos de FX nunca afecta a los gráficos de activos.

---

## 🔓 Abrir los ajustes del gráfico

- 🌐 **Para todos los gráficos** — haz clic en **Configuración** (⚙️) en la barra de herramientas de la lista. La ventana se titula
  **Ajustes del gráfico**. Aplicarlos reemplaza la configuración personalizada de cada gráfico de la lista, incluidas las páginas
  de detalle, y la ventana te avisa de ello.
- 🎯 **Para un gráfico** — haz clic en ⚙️ en una tarjeta. La ventana se titula **Ajustes del gráfico (Local)**, y
  sus ajustes se aplican solo a ese gráfico.

!!! note "Las páginas de detalle usan paneles en línea"

    En una [página de detalle de par](detail/index.md) (y en una página de detalle de activo), ⚙️ en el gráfico abre
    los mismos ajustes de apariencia en un panel, y el panel **Señales** situado encima del gráfico contiene las
    superposiciones. Son los mismos ajustes que los locales de la tarjeta.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Modal de ajustes del gráfico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Vista previa antes de aplicar

La ventana muestra un gráfico de vista previa con su propio interruptor **Abs** / **%**. Tus gráficos solo cambian cuando
haces clic en **Aplicar**; **Cancelar** pregunta antes de descartar tus cambios.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Modal de ajustes del gráfico con la vista previa en vivo">
</div>

- 🌐 **Para todos los gráficos**, la vista previa dibuja una curva de demostración. El servidor calcula los indicadores sobre ella,
  por lo que se ven exactamente como se verán en tus gráficos reales.
- 🎯 **Para un gráfico**, la vista previa usa los datos reales de ese gráfico. Los indicadores muestran la última configuración
  aplicada hasta que haces clic en **Aplicar**, y un banner te lo recuerda.

---

## 🎨 Apariencia

| Configuración | Qué hace |
|---------|--------------|
| **Colores de línea base** | Verde por encima, rojo por debajo del inicio del periodo |
| **Relleno de área** | Degradado bajo la línea |
| **Líneas de cuadrícula** | Cuadrícula discontinua horizontal |
| **Degradado obsoleto** | Atenúa los días sin un valor nuevo, que repiten uno anterior |

### 📏 Rangos de ejes

La **Escala del eje Y** tiene una fila para cada eje del gráfico: el eje principal (el tipo de cambio, o el porcentaje
en la vista %) y una para cada escala de indicador, como el **eje RSI**. Los indicadores que comparten una
escala comparten una fila.

- **Auto** ajusta los datos en ese eje.
- **Incluir 0** ajusta los datos y también muestra el cero.
- **Personalizado** usa los valores **Mín.** y **Máx.** que escribas.

Las vistas **Abs** y **%** mantienen rangos separados: cambia la vista previa a **%** para ajustar el
del porcentaje.

---

## 📈 Señales superpuestas

Añade superposiciones desde tres menús desplegables, igual que en el [panel Señales](detail/signals.md) de la página de detalle:

- 🧮 **Indicadores técnicos** — 9 indicadores funcionan con tipos de cambio FX (los gráficos de activos ofrecen más), agrupados por
  familia con un cuadro de búsqueda. Las matemáticas están en
  [Indicadores técnicos — Teoría financiera](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Comparación de datos** — otro par FX o un activo en el mismo gráfico.
- 📐 **Benchmarks sintéticos** — curvas de referencia construidas solo a partir de parámetros, no de datos de mercado:
  [Lineal](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
  [Compuesto](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) y
  [Onda senoidal](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Cada señal se convierte en una tarjeta con sus parámetros, un enlace 📖 a su página de teoría y, una vez calculada, un
icono de diagnóstico.

---

## 💾 Dónde se guardan los ajustes

- Los ajustes del gráfico se guardan en **este navegador**, para tu usuario, por separado para las listas de FX y de activos.
  Los ajustes propios de un gráfico se superponen a los ajustes de su lista.
- No se almacenan en el servidor: otro navegador o dispositivo comienza con los valores predeterminados, y
  borrar los datos de navegación de este sitio los restablece.
- El periodo seleccionado no es un ajuste del gráfico: las páginas de la misma pestaña del navegador lo comparten.
