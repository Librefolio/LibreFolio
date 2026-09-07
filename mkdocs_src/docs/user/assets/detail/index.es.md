# 🔍 Página de Detalle del Activo

Haga clic en cualquier activo de la [Lista de Activos](../index.md) para abrir su página de detalle. Aquí puede visualizar, analizar y gestionar los datos de precios de ese activo específico.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Página de Detalle del Activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La página de detalle está organizada en dos pestañas: **Resumen** (todas las funcionalidades a continuación) y **Riesgo y escenarios**.

!!! info "Beta"

    La pestaña **Riesgo y escenarios** pertenece al subsistema de Análisis de Riesgo, actualmente en **beta**. Aún no está cubierta por esta documentación — las secciones siguientes describen la pestaña Resumen.

---

## 🧭 Funcionalidades

### 📈 [Gráfico Interactivo](chart.md)

La vista principal: un gráfico completo impulsado por ECharts con zoom, desplazamiento, filtrado por rango de fechas y conversión de moneda. Los marcadores de eventos (dividendos, splits, intereses) se superponen directamente sobre la línea de precio.

### 📊 [Señales](signals.md)

Superponga en el gráfico cualquiera de los **22 indicadores técnicos del backend** (familias de tendencia, momentum, volatilidad, volumen y riesgo), series de comparación y curvas de referencia sintéticas. Cada señal es calculada por el backend a partir del historial de precios almacenado y puede configurarse y conmutarse de forma independiente.

### 📐 [Medidas](measures.md)

Herramienta de medición de clic a clic. Seleccione dos puntos en el gráfico para ver el delta, el cambio porcentual y el rendimiento anualizado entre ellos.

### 🗂️ [Clasificación](classification.md)

Gráfico circular de sectores, mapa mundial geográfico y desglose por país, siempre que los datos de clasificación estén configurados para el activo.

### ✏️ [Editor de Datos](data-editor.md)

Visualice, añada, edite o elimine puntos de datos de precios individuales directamente en el gráfico.

### 📅 [Eventos](events.md)

Eventos a nivel de activo (dividendos, intereses, splits, ajustes de precios) mostrados como marcadores en el gráfico.

---

## 🔧 Encabezado y Controles

- **Botón Atrás ←**: volver a la lista de activos (o a la página anterior)
- **Información del activo**: nombre, insignia de tipo, moneda, precio actual
- **Editar** (✏️): abrir el modal de edición para modificar las propiedades del activo
- **Sincronizar** (🔄): obtener los datos de precios más recientes del proveedor
- **Actualizar** (↻): recargar los datos desde la base de datos

---

## 🔗 Relacionados

- ➕ **[Crear y Editar](../create-edit.md)** — Creación y configuración de activos
- 📋 **[Descripción General de Activos](../index.md)** — Volver a la página de la lista de activos
