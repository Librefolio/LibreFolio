# ⚙️ Configuración Global

LibreFolio tiene un conjunto de **configuraciones a nivel de sistema** que afectan a todos los usuarios. Estas son gestionadas por los administradores y se almacenan en la base de datos.

---

## 👁️ Visualización y Edición de Configuraciones

### 🖥️ Desde la UI

1. Navegue a **Configuración** (Settings) (icono de engranaje en la barra lateral)
2. Haga clic en la pestaña **Configuración Global** (Global Settings) (visible solo para admin/superuser)
3. Haga clic en el **icono del candado** junto a una configuración para desbloquearla y editarla
4. Modifique el valor y el cambio se guardará automáticamente

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Configuraciones Globales" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Solo Administradores"

    Solo los usuarios con privilegios de **superuser** pueden modificar las configuraciones globales. Los usuarios regulares ven una vista de solo lectura.

### 💻 Desde la CLI

Para inicializar las configuraciones predeterminadas (crea solo las que falten):

```bash
./dev.py user init-settings
```

---

## 📋 Configuraciones Disponibles

| Clave | Tipo | Predeterminado | Descripción |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | Tiempo de expiración del token JWT en horas. Después de este periodo, los usuarios deben iniciar sesión nuevamente. |
| `enable_registration` | bool | `true` | Si se permite el registro de nuevos usuarios. Establezca en `false` para evitar nuevos registros. |
| `require_email_verification` | bool | `false` | Si los nuevos usuarios deben verificar su correo electrónico antes de acceder al sistema. |
| `max_file_upload_mb` | int | `10` | Tamaño máximo de subida de archivos en megabytes. Se aplica a todas las subidas (recursos estáticos e informes de brókers). |
| `scheduler_enabled` | bool | `true` | Habilita o deshabilita el demonio automático de sincronización en segundo plano para tipos de cambio y precios históricos/en tiempo real. |
| `scheduler_current_price_frequency_minutes` | int | `10` | Frecuencia (in minutos) con la que el demonio actualiza los precios actuales en tiempo real (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Horas diarias específicas (hora local del servidor, separadas por comas) para activar la sincronización histórica de cierre. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Días específicos de la semana (separados por comas) para ejecutar la sincronización histórica. |
| `scheduler_history_sync_horizon_days` | int | `14` | Ventana de análisis retrospectivo rodante (en días) utilizada para verificar la falta de precios históricos. |
| `default_currency` | str | `EUR` | Moneda de visualización predeterminada para los usuarios recién registrados. Los usuarios pueden anular esto en su configuración personal. |
| `default_language` | str | `en` | Idioma predeterminado para los usuarios recién registrados. Soportados: `en`, `it`, `fr`, `es`. |

---

## 🗂️ Categorías

Las configuraciones están agrupadas en categorías en la UI:

### 🕐 Sesión
- ⏱️ `session_ttl_hours` — Controla la duración de la sesión

### 🛡️ Seguridad
- 📝 `enable_registration` — Abrir/cerrar el registro
- ✉️ `require_email_verification` — Barrera de verificación de correo electrónico

### 📤 Sincronización y Subidas
- 🕐 `scheduler_enabled` — Habilitar o deshabilitar el programador en segundo plano
- ⚡ `scheduler_current_price_frequency_minutes` — Frecuencia de actualización de precios en tiempo real
- 📅 `scheduler_history_sync_times` — Horas de sincronización histórica diaria
- 📅 `scheduler_history_sync_days` — Días de sincronización histórica semanal
- 🔍 `scheduler_history_sync_horizon_days` — Horizonte de análisis de sincronización histórica (en días)
- 📦 `max_file_upload_mb` — Límite de tamaño de archivo

### 🌍 Valores Predeterminados
- 💰 `default_currency` — Moneda predeterminada para usuarios recién registrados
- 🗣️ `default_language` — Idioma predeterminado para usuarios recién registrados

---

## 🕐 Programador de Datos de Mercado

Cuando el programador en segundo plano está habilitado, los administradores pueden configurar los parámetros de sincronización e inspeccionar los registros de ejecución en segundo plano directamente desde la interfaz de usuario.

### ⚙️ Configurar Programador

Haga clic en el botón **Configurar** en la fila del Programador para personalizar las frecuencias de ejecución y los parámetros:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modal de Configuración del Programador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Current Price Frequency**: La frecuencia (en minutos) con la que el demonio recupera las cotizaciones en tiempo real para mantener actualizada la caché del panel (predeterminado: 10m).
* **History Sync Times**: Horas específicas del día (separadas por comas, ej. `06:00,23:00`) para ejecutar las actualizaciones de cierre diario histórico.
* **History Sync Days**: Días específicos de la semana en los que se realiza la sincronización histórica (normalmente de lunes a sábado).
* **History Horizon**: La ventana de análisis (en días) para verificar la falta de puntos de precios históricos (predeterminado: 14 días).

### 📜 Registros del Programador

Haga clic en **Ver Registros** para abrir el inspector de registros. Este modal muestra una lista de ejecuciones recientes del programador:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modal de Registros del Programador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

El registro informa la marca de tiempo de ejecución, el nombre del trabajo, el estado (Success/Error), la duración de la ejecución y los detalles estructurados de los activos procesados, las fuentes de precios y cualquier traza de error.

---

## 🔧 Notas Técnicas

- 🗃️ Las configuraciones se almacenan como **pares clave-valor** en la tabla `global_settings`
- 🔀 Los valores se almacenan como cadenas y se convierten al tipo apropiado (`int`, `bool`, `str`) al leerlos
- 🔒 En el arranque con múltiples workers, las configuraciones se inicializan con `INSERT ... ON CONFLICT DO NOTHING` para evitar condiciones de carrera
- ⚡ Los cambios surten efecto **inmediatamente** — no se requiere reiniciar el servidor
