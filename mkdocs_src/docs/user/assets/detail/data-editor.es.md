# ✏️ Editor de Datos

El Editor de Datos le permite ver, añadir, editar o eliminar manualmente puntos de datos de precios y eventos de activos directamente desde la página de detalles del activo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-editor" alt="Asset Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Cómo utilizarlo

1. Haga clic en el botón **Editar datos** (✏️📊) en la barra de herramientas
2. Se abre el panel del editor con dos pestañas: **Precios** y **Eventos**
3. En cada pestaña puede:
 - **Añadir** una nueva fila: haga clic en ➕ Añadir fila y complete los campos
 - **Editar** una fila existente: haga clic en una celda para modificarla
 - **Eliminar** una fila: selecciónela y haga clic en 🗑️ Eliminar
 - **Importar CSV**: haga clic en 📥 Importar CSV para añadir datos en masa
4. Los cambios se rastrean mediante una insignia de recuento de cambios (dirty count). Haga clic en **Guardar** para confirmar todos los cambios, o en **Cancelar** para descartarlos.
5. Haga clic en **Cerrar** (✕) para salir; los demás paneles (señales, medidas) se restauran automáticamente.

---

## 💰 Pestaña de Precios

La pestaña de Precios muestra todos los puntos de datos de precios del activo. Columnas:

| Columna | Requerido | Descripción |
|--------|----------|-------------|
| **Date** | ✅ | Fecha en formato AAAA-MM-DD |
| **Currency** | ✅ | Código de moneda ISO 4217 (ej., USD, EUR) |
| **Close** | ✅ | Precio de cierre |
| **Open** | | Precio de apertura |
| **High** | | Precio máximo del día |
| **Low** | | Precio mínimo del día |
| **Volume** | | Volumen de negociación |

### Formato de Importación CSV

```
date;currency;close
2024-01-15;USD;145.50
2024-01-16;USD;146.10
```

Formato extendido con columnas opcionales:
```
date;currency;close;open;high;low;volume
2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
```

---

## 📅 Pestaña de Eventos

La pestaña de Eventos muestra todos los [eventos de activos](../../../financial-theory/instruments/asset-events/index.md) (dividendos, splits, etc.). Columnas:

| Columna | Requerido | Descripción |
|--------|----------|-------------|
| **Date** | ✅ | Fecha en formato AAAA-MM-DD |
| **Currency** | | Código ISO 4217 |
| **Type** | ✅ | Tipo de evento (DIVIDEND, INTEREST, SPLIT, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT) |
| **Amount** | ✅ | Valor numérico (ej., dividendo por acción, relación de split) |
| **Notes** | | Descripción opcional |

!!! info "Eventos Automáticos vs Manuales"

    Los eventos generados por un proveedor (ej., Inversión Programada) se marcan como **auto** y aparecen como filas de solo lectura. Pueden eliminarse pero no editarse. Los eventos manuales son totalmente editables.

### Formato de Importación CSV

```
date;currency;type;amount;notes
2024-03-15;USD;DIVIDEND;1.25;Q1 payout
2024-06-01;;SPLIT;2;2:1 split
```

---

## ⚠️ Interruptor de Filas Obsoletas

La barra de herramientas incluye un **interruptor de filas obsoletas** (switch). Las filas obsoletas son puntos de datos de relleno hacia atrás (backward-filled): entradas de relleno de huecos copiadas del punto de datos real más cercano. El interruptor le permite mostrarlas u ocultarlas para centrarse en los datos reales. Un contador indica cuántas filas obsoletas existen.

---

## 🖱️ Navegación Gráfico ↔ Editor

Haga **doble clic** en un punto del gráfico de precios (o mantenga presionado en móviles) para desplazarse directamente a esa fila en el editor:

- Doble clic en un **punto de precio** $\rightarrow$ se desplaza a la pestaña de Precios
- Doble clic en un **marcador de evento** $\rightarrow$ se desplaza a la pestaña de Eventos

---

!!! note "Cuándo utilizar el Editor de Datos"

    El Editor de Datos es útil para:

    - Corregir datos de precios erróneos de un proveedor
    - Añadir datos históricos para activos que no tienen proveedor
    - Rellenar huecos en el historial de precios (ej., fechas faltantes)
    - Registrar eventos corporativos (dividendos, splits) no capturados por los proveedores

---

## 🔗 Relacionado

- 📈 **[Gráfico Interactivo](chart.md)** — Visualización de gráficos con marcadores de eventos
- 📅 **[Eventos de Activos](events.md)** — Tipos de eventos y sus fuentes
- 📚 **[Eventos de Activos (Teoría Financiera)](../../../financial-theory/instruments/asset-events/index.md)** — Análisis detallado del impacto de cada tipo de evento
- 🔌 **[Proveedores](../providers/index.md)** — Obtención automática de precios
