# 📊 Panel

El panel es el **centro de mando de tu cartera** — una única pantalla que te dice cuánto vale tu cartera, cómo está rindiendo y dónde está asignado tu dinero.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista principal (absoluta)" alt="Panel — Modo absoluto">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista principal (porcentual)" alt="Panel — Modo porcentual">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Asignación" alt="Panel — Asignación">
</div>

## 🗂️ Disposición en pestañas

La interfaz del panel está organizada en cuatro pestañas principales, lo que te permite cambiar entre distintos niveles de detalle:

1. **Resumen** (predeterminado): métricas clave, saldos de efectivo y gráficos visuales de tu cartera.
2. **[Posiciones y análisis](positions.md)**: posiciones abiertas, ponderaciones y análisis detallado de lotes fiscales (FIFO).
3. **[Riesgo](#risk-tab)**: el panel **Riesgo de la cartera**, que responde a cuatro preguntas sobre el riesgo de tu cartera.
4. **Transacciones**: las operaciones del rango de fechas y el ámbito de brókeres seleccionados, como una lista paginada de solo lectura — haz doble clic en una fila para abrir su visor de detalle. Consulta [Transacciones](../transactions/index.md) para la guía completa.

---

## 📈 Pestaña Resumen

La pestaña Resumen es la página de inicio predeterminada. Se estructura en las siguientes secciones:

| Sección | Descripción |
|---------|-------------|
| **[Tarjetas KPI](kpi-cards.md)** | Resumen del patrimonio neto, P&L período y métricas de rentabilidad. |
| **Saldos de efectivo** | Saldos líquidos agrupados por divisa en el ámbito activo de brókeres. |
| **[Gráfico de crecimiento](charts.md#portfolio-growth-chart)** | Valor de la cartera a lo largo del tiempo en tres vistas: valores absolutos (Abs), tasas de rentabilidad (%) y el dinero realmente ganado (P&L). |
| **[Panel de asignación](charts.md#allocation-panel)** | Gráficos de dona e históricos apilados agrupados por tipo, sector y geografía. |

### 🪙 Saldos de efectivo

Justo debajo de las tarjetas KPI, el panel **Saldos de efectivo** muestra tu efectivo líquido total agregado por divisa. Por ejemplo, si tienes USD en el bróker A y EUR en el bróker B, ambos saldos se mostrarán uno al lado del otro.

Cuando aplicas un filtro de brókeres, los saldos de efectivo se actualizan automáticamente para reflejar solo el efectivo mantenido en los brókeres seleccionados.

---

## 🛡️ Pestaña Riesgo {: #risk-tab }

La pestaña Riesgo contiene el panel **Riesgo de la cartera**, que responde a cuatro preguntas sobre el riesgo de tu cartera: **¿Cuánto puede doler?**, **¿Estoy tan diversificado como creo?**, **¿Me están pagando por este riesgo?** y **¿Y si…?** Siempre abarca toda tu cartera — cada bróker que posees con una participación superior al 0 % — y sigue el rango de fechas y la divisa objetivo del panel, pero no el filtro de brókeres: cuando hay un filtro activo, un subtítulo lo indica. Consulta [Pestaña Riesgo](risk.md) para conocer los bloques y las herramientas que muestran.

---

## 🎛️ Rango de fechas, filtros y exportación IA

En la esquina superior derecha del panel dispones de varios controles para personalizar tu vista:

- **Rango de tiempo** — preajustes desde **1W** hasta **All**, o un rango personalizado mediante el selector de fechas.
- **Filtro de brókeres** — filtra las métricas a uno o varios brókeres concretos; la pestaña Riesgo siempre abarca todos los brókeres que posees, y un subtítulo lo indica cuando hay un filtro activo.
- **Divisa objetivo** — convierte todos los activos y saldos de efectivo de forma dinámica a una única divisa seleccionada para verlos de forma agregada. La lista ofrece tu divisa predeterminada y las divisas de tus pares FX configurados — ambos extremos de cada par. Una divisa por la que solo pasa una [ruta en cadena](../fx/add-pair.md) no se ofrece: al sincronizar una cadena solo se almacena el tipo de cambio de su propio par, de modo que LibreFolio no tiene tipos con los que convertir a esa divisa. Para que una divisa esté disponible, dale un par propio: elige **Crear forex…** al final de la lista, o marca **Crear también pares intermedios** cuando añadas un par mediante una ruta en cadena.
- **Exportación IA** (:material-brain:) — abre una exportación al portapapeles. Elige **Instantánea
  de datos** para obtener solo datos fácticos, o una **tarea de análisis** que incluye
  automáticamente sus instrucciones y su contrato de respuesta; después selecciona el **nivel
  de detalle** (Compacto, Estándar o Completo). La instantánea del backend sigue el filtro de
  brókeres, el rango de fechas y la divisa objetivo activos; LibreFolio no contacta con ningún
  servicio de IA. Consulta [Exportación IA para la cartera](../ai-export/portfolio.md) o el
  [resumen de la exportación IA](../ai-export/index.md).

El rango de tiempo, el filtro de brókeres y la divisa objetivo se mantienen tal como los configures durante el resto de tu sesión en esta pestaña del navegador — recargar la página también los conserva — y se restablecen al cerrar sesión. El rango de tiempo se comparte con las demás páginas que también lo tienen (las páginas de Activos y FX, sus páginas de detalle y la página de cada bróker), así que un cambio hecho allí también aparece aquí. Junto a **Exportación IA**, el botón **Actualizar** (:material-refresh:) recalcula todo a petición: consulta [Volver y actualizar](#coming-back-and-refreshing).

!!! tip "El ámbito importa"

    Cuando filtras a un único bróker, las transferencias de fondos *a otros brókeres* se convierten en flujos externos para ese ámbito. Esto afecta a los cálculos de [Capital depositado](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) y de [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "Compartir afecta a estas cifras"

    El panel solo cuenta los brókeres que **posees** con una participación superior al 0 %, y cada importe procedente de ellos se **pondera según tu participación**: un Propietario con una participación del 50 % ve la mitad del valor, los ingresos y el P&L de ese bróker contabilizados en los totales. Los brókeres en los que eres **Editor** o **Lector** — que por regla siempre tienen una participación del 0 % — quedan fuera, igual que aquellos que posees con una participación del 0 %: faltan en los totales, en el filtro de brókeres, en la pestaña Posiciones (incluidos la vista de periodo y el panel de lotes), en la pestaña Riesgo y en la pestaña Transacciones. Los ves en su propia página de bróker, que cuenta el bróker **entero** para cualquier rol. Consulta [Compartir brókeres](../brokers/sharing.md) para más detalles.

La página de un bróker es este mismo panel aplicado a un único bróker, con la pestaña **Info** propia de ese bróker: consulta [La página del bróker es el panel sobre un solo bróker](../brokers/index.md#broker-page-is-dashboard).

---

## 🔄 Volver y actualizar {: #coming-back-and-refreshing }

Vuelve al panel — desde la barra lateral o con el botón **←** de una página de activo — y muestra al instante lo mismo que mostraba cuando lo dejaste: las tarjetas KPI, los gráficos, la pestaña Posiciones con su vista de periodo y su panel de [Análisis de lotes FIFO](positions.md#fifo-lots-analysis), y la pestaña Riesgo. No hay marcadores de carga y las cifras KPI aparecen directamente en su valor en lugar de contar desde cero. Si mientras tanto cambiaste el rango de tiempo en otra página, el panel se abre en ese rango.

- **Si mientras tanto no ha cambiado nada**, eso es todo: LibreFolio no recalcula nada.
- **Si algo ha cambiado** — por ejemplo una transacción; precios, tipos de cambio o eventos introducidos a mano o traídos por una sincronización; un activo editado o fusionado; un cambio en uno de tus brókeres o en tu acceso a él; o el precio en vivo que una página de activo consulta mientras está abierta — las cifras antiguas permanecen en pantalla mientras LibreFolio recalcula en segundo plano y después los números pasan a los nuevos valores. Una sincronización de precios o de tipos que no haya traído nada nuevo no se considera un cambio.

El botón **Actualizar** lo recalcula todo, incluso cuando no ha cambiado nada: las cifras, la vista de periodo, el panel de lotes y la pestaña Riesgo. Mientras tanto, lo que ves permanece en pantalla.

Si un recálculo falla, las cifras que ya están en pantalla se mantienen y un mensaje te lo indica. En la pestaña Riesgo, esto solo se aplica a las cifras del periodo y la divisa que estás viendo: si cambias a un periodo o una divisa para los que la pestaña aún no tiene cifras y el cálculo falla, muestra *No se pudieron cargar los datos de riesgo.* en lugar de sus niveles, en vez de las cifras de tu elección anterior.

---

## 🌡️ Banner de calidad de datos {: #data-quality-banner }

Si falta algún precio o tipo de cambio FX en la fecha final, aparece un banner en la parte superior que explica qué activos no se pudieron valorar.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Banner de calidad de datos del panel con enlaces por activo">
</div>
 Los activos sin proveedor de precios (introducidos manualmente, como los proyectos inmobiliarios de crowdfunding) se valoran al precio de su última compra o venta, salvo que tú introduzcas un precio más reciente — esto es intencionado y no genera ninguna advertencia. Un activo que sí tiene proveedor de precios pero sigue sin precio de mercado en la fecha final, más de dos semanas después de que lo compraras por primera vez, se valora mientras tanto también al precio de su última compra o venta, y el banner lo enumera: por ejemplo, un bono comprado en la emisión, antes de su primera cotización.

Un ajuste registra lo que costaron las unidades, nunca un precio. Una transferencia también lo hace, con una excepción: para un activo que aún no tiene nada más — ni precio de mercado, ni compra o venta, ni ajuste, ni salida anterior — el coste que diste a una transferencia entrante cuenta como su precio, una estimación, hasta que un precio o una operación real lo sustituya. Ese activo se valora a ese coste convertido al tipo de cambio de cada día, de modo que su valor se mueve con el tipo, y el banner lo trata como un activo valorado a su última compra o venta: si tiene proveedor de precios, se enumera más de dos semanas después de que llegara la transferencia, siempre que siga sin precio de mercado. Un activo cotizado trasladado entre tus brókeres conserva su precio de mercado. Un activo que posees sin ningún precio — ni precio de mercado, ni compra o venta, ni una transferencia de ese tipo, como uno que recibiste mediante un ajuste — se valora por lo que te costó, cuando ese coste es conocido, sin ganancia ni pérdida no realizada. Para un activo manual esto es intencionado y no genera ninguna advertencia; para un activo con proveedor de precios, transcurridas más de dos semanas desde que lo adquiriste por primera vez, el banner lo enumera como *valorado a coste* hasta que obtenga un precio.

El banner también te advierte cuando un activo que posees tiene proveedor de precios pero su último precio tiene **más de una semana de antigüedad** en la fecha final: haz clic en **Sincronizar precios** para obtener los precios que faltan, y la advertencia desaparece en cuanto se ponen al día. Los activos manuales nunca se marcan de esta forma, ya que no hay nada que sincronizar.

Lo mismo ocurre con los **tipos de cambio antiguos**. Cuando la cartera se valora en la fecha final con un tipo de cambio cuyo último tipo almacenado tiene **más de una semana de antigüedad**, una fila de advertencia enumera los pares FX afectados, con un único botón **Sincronizar tipos** para todos ellos. Si la sincronización se realiza correctamente pero el proveedor aún no tiene un tipo más reciente, una alerta lo indica — *El proveedor aún no tiene tipos más recientes para USD → EUR: inténtalo más tarde* — en lugar de un simple mensaje de éxito; inténtalo más tarde, y la fila desaparece en cuanto se almacene un tipo más reciente.

También enumera los activos a los que les **falta el coste de compra**: una transferencia o un ajuste que introdujo unidades sin coste base. LibreFolio no puede saber cuánto costaron esas unidades, así que las contabiliza como cero en tu coste de compra y muestra el coste medio y el P&L no realizado de esa posición como no disponibles (`—`). Para corregirlo, busca esa transferencia o ese ajuste entre tus [transacciones](../transactions/index.md) y asígnale su coste base.

También te advierte sobre **códigos de divisa que no son códigos ISO**: un número o un nombre, como `978` o `EURO`, que una versión anterior de LibreFolio guardó tal como lo escribiste. Ahora LibreFolio solo guarda códigos como `EUR`, por lo que los importes en un valor de ese tipo no se pueden convertir, y una fila que lo contenga no se podrá volver a guardar tras una edición hasta que se corrija su código. La advertencia indica el valor y el código que representa (`978` es `EUR`), y no enumera ningún tipo de cambio que añadir para él, ya que ninguno serviría. Cuando el valor es tu propia divisa predeterminada, te indica que la vuelvas a elegir en **Configuración › Preferencias**. Tu administrador puede listar todos esos valores con `./dev.py db currencies` ([Herramientas de administración CLI](../../admin/cli_tools.md), «Códigos de divisa que no son códigos ISO»).

También señala, sin pedirte que corrijas nada, las **transferencias entre brókeres que posees con participaciones distintas**: cada lado cuenta según la participación de su propio bróker, de modo que lo que sale de un bróker y lo que llega al otro difieren, y LibreFolio contabiliza esa diferencia como ganancia o pérdida.

Los tipos de cambio se comprueban para cada transacción hasta la fecha final — cada compra, venta y movimiento de efectivo se convierte al tipo de su propia fecha — y, para valorar lo que posees, en cada día del periodo en pantalla: tus valores y también el efectivo que mantienes en otra divisa, valorado cada día al tipo de ese día. Cuando un par FX configurado con proveedor **no tiene tipo** para alguna de esas fechas, el banner lo enumera con el intervalo de las fechas que faltan. LibreFolio convierte un importe con el tipo más reciente en su fecha o anterior, por antiguo que sea, por lo que estas fechas son *anteriores* al primer tipo almacenado del par — a menudo bastante antes del periodo en pantalla, porque todas las transacciones pasadas cuentan para totales como tu P&L total y tu coste de compra. Haz clic en **Sincronizar tipos** para rellenarlas:

- LibreFolio descarga ese intervalo de fechas con **una semana extra a cada lado** (nunca más allá de hoy), sea cual sea el periodo que muestre el panel. La semana extra cubre los fines de semana y los días festivos, cuando los proveedores no publican nada: ese día en el borde del intervalo toma entonces el tipo del día laborable anterior.
- Cuando termina la descarga, el panel se actualiza y un mensaje informa del resultado de cada par.
- Si la descarga se completa pero los mismos pares siguen marcados, el proveedor no tiene tipos para las fechas que aún faltan — normalmente porque son anteriores al inicio de su historial. El mensaje se convierte entonces en una advertencia que lo indica: introduce esos tipos a mano en el [Editor de datos](../fx/detail/data-editor.md) del par.

Los pares solo con tipos manuales (sin proveedor) reciben su propia advertencia: su botón **Ver FX** abre la página del primer par que enumera, donde añades los tipos tú mismo.

!!! tip "Rellena todo el historial de un par de una vez"

    Abre la [página FX](../fx/index.md), elige el rango **All** y haz clic en [Sincronizar todo](../fx/sync.md): LibreFolio descarga todo lo que los proveedores publican para tus pares, hasta hoy. Un par que añadas con proveedor hace esto por sí solo — consulta [Añadir un par de divisas](../fx/add-pair.md).

---

## 🔗 En esta sección

- 💰 **[Tarjetas KPI](kpi-cards.md)** — explicación del patrimonio neto, el P&L período y las rentabilidades
- 📊 **[Gráficos](charts.md)** — explicación del gráfico de crecimiento y del panel de asignación
- 🔍 **[Posiciones y análisis](positions.md)** — posiciones abiertas, vistas de tabla frente a mapa y análisis detallado de lotes fiscales FIFO.

## 🔗 Teoría relacionada

- **[NAV / Patrimonio neto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valor contable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L período](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capital depositado y P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Resumen de las métricas de rendimiento](../../financial-theory/technical-analysis/performance-metrics/index.md)**
