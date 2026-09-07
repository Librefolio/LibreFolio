# 📁 Archivos y Cargas

La página **Archivos** (`/files`) es su centro neurálgico para gestionar todo el contenido cargado en LibreFolio. Consta de dos secciones diferenciadas con distintas reglas de visibilidad.

---

## 📂 Dos Pestañas, Dos Propósitos

### 📁 Recursos Estáticos

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los recursos estáticos son **visibles para todos los usuarios** del sistema. Aquí encontrará:

- 🖼️ **Avatares** y fotos de perfil de usuario
- 🏷️ **Iconos** y logotipos de brókers
- 📄 Cualquier **documento compartido** o imagen subida por los usuarios

Estos archivos se guardan en el directorio `custom-uploads/` del servidor.

**Menú Contextual**: Haga clic derecho en cualquier fila de archivo (en la vista de lista) para acceder a las acciones rápidas (Vista previa, Copiar Enlace, Descargar, Eliminar).

Puede cambiar entre **vista de lista** y **vista de cuadrícula** para ver una vista previa visual de los archivos de imagen:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Informes de Bróker {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los informes de bróker tienen una **visibilidad restringida**: solo puede ver los informes de los brókers a los que tiene acceso (como propietario, editor o lector). Estos archivos incluyen:

- 📋 **Exportaciones de transacciones** en formato CSV o Excel de su bróker
- ✅ **Resultados de la lectura** del sistema de importación automática (BRIM)
- ❌ Archivos cuya **lectura falló** (guardados para depuración)

**Menú Contextual**: Haga clic derecho en cualquier fila de informe para acceder a las acciones rápidas (Vista previa, Descargar, Eliminar).

---

## ⬆️ Carga de Archivos

Para cargar un archivo:

1. Haga clic en el **área de carga** o **arrastre y suelte** los archivos directamente en ella.
2. En el caso de **archivos de imagen**, la [herramienta de recorte de imágenes](../misc/image-crop.md) se abrirá automáticamente para poder cambiar el tamaño y recortarla antes de subirla.
3. Para **archivos que no son de imagen** (CSV, PDF, etc.), puede cambiar el nombre del archivo antes de confirmar la subida.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Límite de Tamaño de Archivo"

    El tamaño máximo de subida lo configura el administrador del sistema en la [Configuración Global](../../admin/settings.md). El valor predefininto suele ser de 10 MB.

---

## 📤 Gestión de Informes de Brókers

Si desea importar transacciones o gestionar informes existentes:

1. Vaya a la pestaña **Informes de Bróker**.
2. Suba el archivo CSV o Excel exportado de su bróker (Degiro, Interactive Brokers, eToro, Directa SIM, etc.).
3. Elija a qué **bróker asociar** el archivo: esto determina qué cuenta de bróker recibirá las transacciones importadas.
4. El archivo se almacena y aparece en la lista de informes. **Todavía no se ejecuta ninguna importación**: para analizarlo de verdad e importar las transacciones, abra el **[Asistente de Importación](../transactions/import/index.md)** (Transacciones → **Importar**) — su paso *Seleccionar Archivos* lista los informes ya subidos, así puede elegir uno en lugar de subirlo de nuevo.

### ⚙️ Acciones en Informes Existentes

Haga clic derecho en cualquier informe en la tabla para abrir su menú contextual:
- 👁️ **Vista previa (Preview)**: Inspecciona el contenido del archivo sin salir de la página.
- 📥 **Descargar (Download)**: Descarga el archivo sin procesar original.
- 🗑️ **Eliminar (Delete)**: Elimina el archivo y sus metadatos. Las transacciones ya importadas desde él **permanecen en el libro mayor** — eliminar un informe nunca elimina transacciones.

!!! info "Asociación ≠ Lectura"

    El bróker que elija durante la carga sirve únicamente para la **asociación**: determina qué cuenta de bróker recibe las transacciones importadas. La detección del formato y la lectura ocurren en un paso aparte y son **independientes** del bróker: el mismo complemento BRIM puede funcionar para múltiples brókers si exportan en el mismo formato.

---

## 🔒 Seguridad

- 🌐 Los **archivos estáticos** están accesibles para cualquier persona con una cuenta de LibreFolio.
- 🔐 Los **informes de brókers** respetan el control de acceso del bróker: solo los usuarios con acceso a ese bróker pueden ver sus informes.
- 🚫 Los **archivos ejecutables** (`.exe`, `.sh`, `.py`, etc.) están bloqueados por motivos de seguridad.
- 🔍 El **tipo MIME** del archivo se valida en el servidor para evitar la falsificación de tipo de archivo (por ejemplo, renombrar un `.exe` a `.jpg`).
