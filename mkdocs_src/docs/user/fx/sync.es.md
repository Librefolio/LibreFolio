# 🔄 Sincronización de FX

Una vez que se ha configurado un par de divisas con un proveedor de datos, LibreFolio puede **sincronizar automáticamente** los tipos de cambio desde fuentes oficiales de bancos centrales.

---

## 🔄 Sincronizar Todo

Desde la página de la lista de FX, utilice el botón **Sincronizar Todo** para sincronizar todos los pares configurados a la vez:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progreso de Sincronización" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

El modal de sincronización muestra:

- 📊 **Progreso** de cada par que se está sincronizando
- ✅ Indicadores de **Estado** (éxito, error, omitido)
- 🆕 Recuento de **nuevos puntos de datos** para cada par

---

## 🎯 Sincronización de un par individual

También puede sincronizar un solo par desde su [página de detalles](detail/index.md) utilizando el botón de sincronización. Esto es útil cuando desea actualizar solo un par específico.

---

## ⚙️ Cómo funciona la sincronización

El proceso de sincronización:

1. Obtiene los tipos de cambio de la API del proveedor configurado (ECB, FED, BOE, SNB, etc.)
2. **Sobrescribe** los puntos de datos existentes en el rango de fechas descargado con los valores del proveedor; el proveedor se trata como la fuente oficial
3. Añade nuevos puntos de datos para fechas que aún no están en la base de datos
4. Si el proveedor primario falla, el sistema hace un fallback automáticamente al siguiente proveedor configurado

Después de la sincronización, verá el número de **puntos descargados** y cuántos eran **realmente nuevos** (no estaban presentes previamente en la base de datos).

!!! warning "El proveedor es la fuente oficial"

    Volver a sincronizar un par sobrescribirá cualquier valor editado manualmente en el rango de fechas sincronizado. Si necesita preservar las ediciones manuales, considere utilizar un par configurado con el proveedor MANUAL (sin fuente de datos automática).

!!! info "Precisión de conversión en cadena"

    Al utilizar rutas en cadena (por ejemplo, RON → EUR → JPY), cada conversión intermedia introduce un error de redondeo mínimo. Aunque es insignificante para la mayoría de los propósitos, tenga en cuenta que los tipos de cambio convertidos en cadena pueden diferir ligeramente de las cotizaciones directas del mercado.

---

## 🌐 Cadenas de Suministro de Datos

Para usuarios avanzados: LibreFolio utiliza un **sistema de enrutamiento** sofisticado para los datos de FX. Cada par de divisas puede tener múltiples proveedores configurados con prioridades y cadenas de fallback.

Esto significa que:

- 🔄 Si su proveedor primario (por ejemplo, ECB) no está disponible, el sistema hace un fallback al siguiente proveedor (por ejemplo, FED)
- 🔀 Los pares exóticos utilizan cadenas de varios pasos a través de divisas intermedias (por ejemplo, RON → EUR → JPY)
- ⚙️ Puede personalizar qué proveedor utilizar para cada par

Para obtener la lista de proveedores compatibles, consulte los [Proveedores de FX](providers/index.md).

Para obtener detalles técnicos sobre el algoritmo de enrutamiento y la configuración, consulte la documentación para desarrolladores: [FX Configuration & Routing](../../developer/backend/fx/configuration.md).
