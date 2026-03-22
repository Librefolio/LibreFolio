# 🔄 Sincronización de Divisas

Una vez que un par de divisas está configurado con un proveedor de datos, LibreFolio puede **sincronizar automáticamente** los tipos de cambio desde fuentes oficiales de bancos centrales.

---

## 🔄 Sincronizar Todo

En la página de la lista de divisas, utiliza el botón **Sincronizar Todo** para sincronizar todos los pares configurados a la vez:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progreso de Sincronización" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La ventana emergente de sincronización muestra:

- 📊 **Progreso** de cada par que se está sincronizando
- ✅ **Indicadores de estado** (éxito, error, omitido)
- 🆕 Número de **nuevos puntos de datos** para cada par

---

## 🎯 Sincronización de un Par Individual

También puedes sincronizar un único par desde su [página de detalle](detail/index.md) usando el botón de sincronización. Esto es útil cuando deseas actualizar solo un par específico.

---

## ⚙️ Cómo Funciona la Sincronización

El proceso de sincronización:

1. Obtiene los tipos de cambio desde la API del proveedor configurado (BCE, FED, BOE, SNB, etc.)
2. **Sobrescribe** los puntos de datos existentes en el rango de fechas descargado con los valores del proveedor — el proveedor se considera la fuente autorizada
3. Añade nuevos puntos para las fechas no presentes en la base de datos
4. Si el proveedor principal falla, el sistema recurre automáticamente al siguiente proveedor configurado

Después de la sincronización, verás el número de **puntos descargados** y cuántos eran **realmente nuevos** (no presentes previamente en la base de datos).

!!! warning "El proveedor es autoritativo"
    Volver a sincronizar un par sobrescribirá cualquier valor editado manualmente en el rango sincronizado. Para preservar las ediciones manuales, configura el par con el proveedor MANUAL (sin fuente de datos automática).

!!! info "Precisión en las conversiones en cadena"
    Al usar rutas en cadena (ej. RON → EUR → JPY), cada conversión intermedia introduce un mínimo error de redondeo. Aunque es despreciable en la mayoría de los casos, los tipos convertidos por cadena pueden diferir ligeramente de las cotizaciones directas del mercado.

---

## 🌐 Cadenas de Suministro de Datos

Para usuarios avanzados: LibreFolio utiliza un **sistema de enrutamiento sofisticado** para los datos de divisas. Cada par de divisas puede tener múltiples proveedores configurados con prioridades y cadenas de respaldo.

Esto significa:

- 🔄 Si tu proveedor principal (p.ej., BCE) no está disponible, el sistema recurre al proveedor de respaldo configurado (p.ej., FED)
- 🔀 Los pares exóticos utilizan cadenas de varios pasos a través de monedas intermedias (p.ej., RON → EUR → JPY)
- ⚙️ Puedes personalizar qué proveedor utilizar para cada par

Para la lista de proveedores soportados, consulta la [Lista de Proveedores de Divisas](../../developer/backend/fx/providers_list.md).

Para detalles técnicos sobre el algoritmo de enrutamiento y la configuración, consulta la documentación para desarrolladores: [Configuración y Enrutamiento de Divisas](../../developer/backend/fx/configuration.md).
