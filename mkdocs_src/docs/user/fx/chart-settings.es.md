# ⚙️ Ajustes del gráfico

La ventana **Ajustes del gráfico** cambia el aspecto de los gráficos y qué superposiciones dibujan. Sirve tanto para la [lista de FX](index.md) como para la [lista de activos](../assets/index.md), y cada lista conserva su propia configuración: cambiar los ajustes de los gráficos de FX nunca afecta a los de activos.

---

## 🔓 Abrir los ajustes del gráfico

- 🌐 **Para todos los gráficos** — haz clic en **Configuración** (⚙️) en la barra de herramientas de la lista. La ventana se titula **Ajustes del gráfico**. Al aplicarla se reemplaza la configuración personalizada de todos los gráficos de la lista, incluidas las páginas de detalle, y la ventana te advierte de ello.
- 🎯 **Para un solo gráfico** — haz clic en ⚙️ en una tarjeta. La ventana se titula **Ajustes del gráfico (local)** y sus ajustes se aplican solo a ese gráfico.

!!! note "Las páginas de detalle usan paneles en línea"

    En una [página de detalle de par](detail/index.md) (y en una página de detalle de activo), ⚙️ en el gráfico abre la misma configuración de apariencia en un panel, y el panel **Señales** situado encima del gráfico contiene las superposiciones. Son los mismos ajustes locales de la tarjeta.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Ventana modal de ajustes del gráfico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Vista previa antes de aplicar

La ventana muestra un gráfico de vista previa con un selector de vista. Es la vista guardada del gráfico, y **Aplicar** la guarda: **Abs**, **%** o **Retorno móvil**. Es el mismo gráfico que en las páginas de detalle del [par](detail/index.md) y del [activo](../assets/detail/chart.md), solo que más alto que el gráfico de una tarjeta: una línea (sin velas), sin la barra de herramientas, los marcadores de eventos ni la herramienta de medición, y puedes hacer zoom con la rueda del ratón como en la página de detalle. Se dibuja con el aspecto y los rangos de ejes que estás editando, y una señal de comparación muestra el icono y el tipo de su activo en la información emergente. Tus gráficos solo cambian cuando haces clic en **Aplicar**; **Cancelar** pide confirmación antes de descartar los cambios.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Ventana modal de ajustes del gráfico con la vista previa en vivo">
</div>

- 🌐 **Para todos los gráficos**, la vista previa dibuja una curva de demostración. El servidor calcula los indicadores sobre ella, de modo que se ven exactamente como lo harán en tus gráficos reales.
- 🎯 **Para un solo gráfico**, la vista previa usa los datos reales de ese gráfico. Los indicadores muestran los últimos ajustes aplicados hasta que hagas clic en **Aplicar**, y un aviso te lo recuerda.

Una señal se ve igual en la vista previa que en la tarjeta, así que lo que ves aquí es lo que la tarjeta dibuja después de **Aplicar**.

### 🔁 Vista de retorno móvil {: #rolling-return-view }

En **Retorno móvil**, la vista previa dibuja el retorno móvil del tipo de cambio o del activo, junto con los retornos móviles de sus comparaciones. Para un solo gráfico, usa los datos reales de la tarjeta y, en un gráfico de FX, los pares FX comparados en él; para todos los gráficos, dibuja una curva de demostración. Hay otros dos controles para elegir la ventana móvil: **1W**, **1M**, **3M**, **1Y** o una cantidad personalizada. Hasta que elijas una, la ventana móvil es automática: el mayor preajuste que se ajuste al período mostrado en la lista. La lista Señales muestra solo las comparaciones que dibuja esta vista, con otro par FX en un gráfico de FX y con otro activo en el gráfico de un activo; los indicadores técnicos y los índices de referencia permanecen guardados, pero se ocultan hasta que vuelvas a cambiar la vista previa a **Abs** o **%**.

---

## 🎨 Apariencia

| Ajuste | Qué hace |
|---------|--------------|
| **Colores de línea base** | Verde por encima y rojo por debajo del inicio del período, con una línea base discontinua. Se aplica a las tarjetas de las listas, a las páginas de detalle y a la vista previa |
| **Relleno de área** | Degradado bajo la línea |
| **Líneas de cuadrícula** | Cuadrícula horizontal discontinua |
| **Degradado obsoleto** | Atenúa los días sin un valor nuevo, que repiten un valor anterior |

### 📏 Rangos de ejes

**Escala del eje Y** tiene una fila por cada eje del gráfico: el eje principal (el tipo de cambio, o el porcentaje en la vista %) y una por cada escala de indicador, como el **eje RSI**. Los indicadores que comparten una escala comparten una fila.

- **Automático** ajusta los datos a ese eje.
- **Incluir 0** ajusta los datos y también muestra el cero.
- **Personalizado** usa los valores **Mín.** y **Máx.** que escribas.

Las vistas **Abs** y **%** mantienen rangos separados: cambia la vista previa a **%** para configurar el rango del porcentaje.

---

## 📈 Señales de superposición

Añade superposiciones desde tres menús desplegables, igual que en el [panel Señales](detail/signals.md) de la página de detalle:

- 🧮 **Indicadores técnicos** — 10 indicadores operan sobre tipos de cambio FX (los gráficos de activos ofrecen más), agrupados por
  familia con un cuadro de búsqueda. Las matemáticas están en
  [Indicadores técnicos — Teoría financiera](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Comparación de datos** — otro par FX o un activo en el mismo gráfico. En una tarjeta de FX, la línea de
  un activo es su precio en la propia divisa del activo, sin conversión, exactamente como la
  [página de detalle del par](detail/index.md) la dibuja: léela en la vista **%**, donde empieza en su propio
  primer valor como el tipo de cambio. En **Abs** se sitúa en el eje del tipo de cambio. La lista carga los precios diarios de
  los activos comparados una vez para todas las tarjetas, y no solicita nada cuando ninguna tarjeta compara un activo. En la
  ventana abierta para **todos los gráficos** no se dibuja una comparación con un activo, porque la curva de demostración
  no tiene un activo real con el que comparar (como en la [lista de activos](../assets/index.md)).
  Un activo se elige en el mismo panel que el de la comparación de riesgo: un cuadro de búsqueda, filtros de **Tipo** y
  **Divisa**, cada fila con el icono, el nombre, el tipo y la divisa del activo, y los índices de referencia
  listados primero; con un clic se elige y se cierra. El propio activo del gráfico aparece atenuado, y uno que
  ya usa otra comparación lleva una marca de advertencia, pero aún puede elegirse.
- 📐 **Benchmarks sintéticos** — curvas de referencia construidas solo a partir de parámetros, no de datos de mercado:
  [Lineal](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
  [Compuesto](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) y
  [Onda sinusoidal](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Cada señal se convierte en una tarjeta con sus parámetros, un enlace 📖 a su página de teoría y, una vez calculada, un icono de diagnóstico.

---

## 💾 Dónde se guarda la configuración

- Los ajustes del gráfico se guardan en **este navegador**, para tu usuario, por separado para las listas de FX y de activos. Los ajustes propios de un gráfico se superponen a los de su lista.
- No se almacenan en el servidor: otro navegador o dispositivo parte de los valores predeterminados, y borrar los datos de navegación de este sitio los restablece.
- El período seleccionado no es un ajuste del gráfico: las páginas de la misma pestaña del navegador lo comparten.
