# 📁 Archivos y Cargas

La página de **Archivos** (`/files`) es su centro neurálgico para gestionar todo el contenido cargado en LibreFolio. Cuenta con dos secciones distintas con diferentes reglas de visibilidad.

---

## 📂 Dos Pestañas, Dos Propósitos

### 📁 Recursos Estáticos

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-tab" alt="Pestaña de Archivos Estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los recursos estáticos son **visibles para todos los usuarios** del sistema. Aquí es donde encontrará:

- 🖼️ **Avatares** de usuario y fotos de perfil
- 🏷️ **Iconos** y logotipos de brókers
- 📄 Cualquier **documento compartido** o imágenes cargadas por los usuarios

Estos archivos se encuentran en el directorio `custom-uploads/` del servidor.

Puede alternar entre la **vista de lista** y la **vista de cuadrícula** para obtener una vista previa visual de los archivos de imagen:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista de Cuadrícula de Archivos Estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Informes de bróker

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Pestaña de Informes de bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los informes de bróker tienen **visibilidad restringida**: solo puede ver los informes de los brókers a los que tiene acceso (como propietario, editor o visor). Estos archivos incluyen:

- 📋 **Exportaciones de transacciones** en CSV o Excel de su bróker
- ✅ **Resultados analizados** del sistema de importación automática (BRIM)
- ❌ Archivos que **fallaron el análisis** (conservados para depuración)

---

## ⬆️ Carga de Archivos

Para cargar un archivo:

1. Haga clic en el **área de carga** o **arrastre y suelte** los archivos directamente
2. Para **archivos de imagen**, la [Herramienta de Recorte de Imagen](../misc/image-crop.md) se abre automáticamente, permitiéndole cambiar el tamaño y recortarla antes de cargar
3. Para **archivos que no sean imágenes** (CSV, PDF, etc.), puede renombrar el archivo antes de confirmar

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zona de Carga de Archivos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Límite de Tamaño de Archivo"

    El tamaño máximo de carga es configurado por el administrador del sistema en [Configuración Global](../../admin/settings.md). El valor predeterminado suele ser 10 MB.

---

## 📤 Carga de Informes de bróker

Si desea importar transacciones de su bróker:

1. Vaya a la pestaña de **Informes de bróker**
2. Cargue el archivo CSV o Excel exportado de su bróker (Degiro, Interactive Brokers, eToro, Directa, etc.)
3. Elija con qué **bróker asociar** el archivo; en este bróker se almacenarán las transacciones importadas
4. El sistema intentará posteriormente **detectar automáticamente** el formato del archivo a través del sistema de importación BRIM y analizará las transacciones

!!! info "Asociación ≠ Análisis"

    El bróker que elija al cargar es solo para la **asociación**: determina qué cuenta de bróker recibe las transacciones importadas. La detección del formato y el análisis ocurren en un paso separado y son **independientes** del bróker: el mismo plugin de BRIM puede funcionar para múltiples brókers si exportan en el mismo formato.

!!! note "Trabajo en Progreso"

    La interfaz de usuario completa de importación de informes de bróker (BRIM) se encuentra en desarrollo activo. Actualmente, puede cargar informes y asociarlos con brókers, pero el asistente de importación guiada aún no está disponible.

---

## 🔒 Seguridad

- 🌐 Los **archivos estáticos** son accesibles para cualquier persona con una cuenta de LibreFolio
- 🔐 Los **informes de bróker** respetan el control de acceso del bróker: solo los usuarios con acceso a ese bróker pueden ver sus informes
- 🚫 Los **archivos ejecutables** (`.exe`, `.sh`, `.py`, etc.) están bloqueados por seguridad
- 🔍 El **tipo MIME** del archivo se valida en el servidor para evitar suplantaciones de tipo (por ejemplo, renombrar un `.exe` a `.jpg`)
