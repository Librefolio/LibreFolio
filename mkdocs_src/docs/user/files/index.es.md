# 📁 Archivos y Subidas

La página **Archivos** (`/files`) es tu centro neurálgico para gestionar todo el contenido subido en LibreFolio. Tiene dos secciones distintas con diferentes reglas de visibilidad.

---

## 📂 Dos Pestañas, Dos Propósitos

### 📁 Recursos estáticos

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-tab" alt="Pestaña de Archivos Estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los recursos estáticos son **visibles para todos los usuarios** del sistema. Aquí es donde encontrarás:

- 🖼️ **Avatares** de usuario y fotos de perfil
- 🏷️ **Iconos** de broker y logotipos
- 📄 Cualquier **documento compartido** o imágenes subidas por usuarios

Estos archivos residen en el directorio `custom-uploads/` del servidor.

Puedes alternar entre la **vista de lista** y la **vista de cuadrícula** para una vista previa visual de los archivos de imagen:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista de Cuadrícula de Archivos Estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Informes de Broker

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Pestaña de Informes de Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los informes de broker tienen **visibilidad restringida** — solo puedes ver los informes de los brokers a los que tienes acceso (como Propietario, Editor o Visor). Estos archivos incluyen:

- 📋 Exportaciones de **transacciones** en CSV o Excel de tu broker
- ✅ **Resultados del procesamiento** del sistema de importación automática (BRIM)
- ❌ Archivos que **no se pudieron procesar** (se mantienen para depuración)

---

## ⬆️ Subida de Archivos

Para subir un archivo:

1. Haz clic en el **área de subida** o **arrastrar y soltar** los archivos directamente
2. Para **archivos de imagen**, la [Herramienta de recorte de imágenes](../misc/image-crop.md) se abre automáticamente, permitiéndote redimensionar y recortar antes de subir
3. Para **archivos que no son imágenes** (CSV, PDF, etc.), puedes renombrar el archivo antes de confirmar

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zona de Arrastre para Subida de Archivos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! consejo "Límite de Tamaño de Archivo"

    El tamaño máximo de subida está configurado por el administrador del sistema en [Configuración Global](../../admin/settings.md). El valor predeterminado suele ser de 10 MB.

---

## 📤 Subida de Informes de Broker

Si quieres importar transacciones desde tu broker:

1. Ve a la pestaña **Informes de Broker**
2. Sube el archivo CSV o Excel exportado de tu broker (Degiro, Interactive Brokers, eToro, Directa, etc.)
3. Elige a qué **broker asociar** el archivo — es donde se guardarán las transacciones importadas
4. El sistema intentará luego **detectar automáticamente** el formato del archivo mediante el sistema de importación BRIM y procesar las transacciones

!!! info "Asociación ≠ Análisis"

    El broker elegido al subir el archivo es solo para **asociación** — determina qué cuenta de broker recibe las transacciones importadas. La detección del formato y el análisis ocurren en un paso separado y son **independientes** del broker: el mismo plugin BRIM puede funcionar para varios brokers si exportan en el mismo formato.

!!! note "En desarrollo"

    La interfaz completa para importar informes de broker (BRIM) está en desarrollo activo. Actualmente, puedes subir informes y asociarlos con brokers, pero el asistente de importación paso a paso aún no está disponible.

---

## 🔒 Seguridad

- 🌐 Los **archivos estáticos** son accesibles para cualquier persona con una cuenta de LibreFolio
- 🔐 Los **informes de broker** respetan el control de acceso del broker — solo los usuarios con acceso a ese broker pueden ver sus informes
- 🚫 Los **archivos ejecutables** (`.exe`, `.sh`, `.py`, etc.) están bloqueados por seguridad
- 🔍 El **tipo MIME** del archivo se valida **en el servidor** para evitar el **enmascaramiento de tipo de archivo** (por ejemplo, renombrar un `.exe` a `.jpg`)
