# ⚙️ Configuración global

LibreFolio dispone de un conjunto de **opciones de configuración de todo el sistema** que afectan a todos los usuarios. Están gestionadas por los administradores y se almacenan en la base de datos.

---

## 👁️ Ver y editar la configuración

### 🖥️ Desde la interfaz de usuario

1. Ve a **Configuración** (icono de engranaje en la barra lateral)
2. Haz clic en la pestaña **Configuración global** (visible para todos los usuarios; solo el administrador/superusuario puede editar)
3. Haz clic en el **icono del candado** junto a un valor de configuración para desbloquearlo y editarlo
4. Modifica el valor y el cambio se guarda automáticamente

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Solo administradores"

    Solo los usuarios con privilegios de **superusuario** pueden modificar la configuración global. Los usuarios normales ven una vista de solo lectura.

### 💻 Desde la CLI

Para inicializar la configuración por defecto (solo crea los valores que faltan):

```bash
./dev.py user init-settings
```

---

## 🕐 Sesión

| Clave | Tipo | Por defecto | Descripción |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | Tiempo de expiración del token JWT en horas. Después de este período, los usuarios deben iniciar sesión de nuevo. |

## 🛡️ Seguridad

| Clave | Tipo | Por defecto | Descripción |
|-----|------|---------|-------------|
| `enable_registration` | bool | `true` | Indica si se permite el registro de nuevos usuarios. Establécelo en `false` para impedir nuevos registros. |
| `require_email_verification` | bool | `false` | **Marcador de posición — aún no se aplica.** Indica si los nuevos usuarios deben verificar su correo electrónico antes de acceder al sistema. El envío de correos electrónicos (SMTP) es una funcionalidad prevista, por lo que en la interfaz este valor de configuración es de solo lectura y lleva una insignia de «próximamente». |

## 🔄 Trabajo de actualización

| Clave | Tipo | Por defecto | Descripción |
|-----|------|---------|-------------|
| `scheduler_enabled` | bool | `true` | Activa o desactiva el demonio de sincronización automática en segundo plano para tipos de cambio y precios históricos/en tiempo real. |

Los parámetros restantes del programador no se muestran como campos individuales: se editan conjuntamente desde la ventana modal **Configurar** de la fila del Programador — consulta [Programador de datos de mercado](#market-data-scheduler) más abajo.

| Clave | Tipo | Por defecto | Descripción |
|-----|------|---------|-------------|
| `scheduler_current_price_frequency_minutes` | int | `10` | Frecuencia (en minutos) con la que el demonio actualiza los precios actuales en tiempo real (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Horas HH:MM separadas por comas para la sincronización histórica diaria, expresadas **en la `scheduler_timezone` configurada**. Las horas se almacenan tal como se introducen (hora de reloj local); el demonio convierte cada franja local en un instante UTC solo cuando decide si un trabajo debe ejecutarse. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Días concretos de la semana (separados por comas) para ejecutar la sincronización histórica. |
| `scheduler_history_sync_horizon_days` | int | `14` | Ventana móvil de análisis retrospectivo (en días) utilizada para comprobar si faltan precios históricos. |
| `scheduler_timezone` | str | `UTC` | Zona horaria IANA utilizada para **almacenar y evaluar** los días y horas de sincronización histórica del programador. Las horas/días que configures son locales a esta zona; los valores no válidos se restablecen a UTC. |

## 🧠 Memoria

| Clave | Tipo | Por defecto | Descripción |
|-----|------|---------|-------------|
| `max_file_upload_mb` | int | `10` | Tamaño máximo de subida de archivos en megabytes. Se aplica a todas las subidas (recursos estáticos e informes de bróker). |

La categoría Memoria también aloja el panel **Cachés del servidor** — consulta [Cachés del servidor](#server-caches) más abajo.

## 🌍 Valores por defecto

| Clave | Tipo | Por defecto | Descripción |
|-----|------|---------|-------------|
| `default_currency` | str | `EUR` | Moneda de visualización por defecto para los nuevos usuarios registrados. Los usuarios pueden modificarla en su configuración personal. |
| `default_language` | str | `en` | Idioma por defecto para los nuevos usuarios registrados. Idiomas compatibles: 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr`, 🇪🇸 `es`. |
| `default_theme` | str | `auto` | Tema por defecto para los nuevos usuarios registrados: ☀️ `light`, 🌙 `dark`, 🖥️ `auto`. |

---

## 🕐 Programador de datos de mercado {: #market-data-scheduler }

Cuando el programador en segundo plano está activado, los administradores pueden configurar los parámetros de sincronización e inspeccionar los registros de ejecución en segundo plano directamente desde la interfaz de usuario.

### ⚙️ Configurar el programador

Haz clic en el botón **Configurar** de la fila del Programador para personalizar las frecuencias y los parámetros de ejecución:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Configuration Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Frecuencia de precio actual**: la frecuencia (en minutos) con la que el demonio obtiene cotizaciones en tiempo real para mantener actualizada la caché del panel de control (por defecto: 10m).
* **Horas de sincronización histórica**: horas diarias concretas (separadas por comas, p. ej., `06:00,23:00`) para ejecutar las actualizaciones de cierre diario histórico. Se trata de horas de reloj local **en la zona horaria del programador configurada**.
* **Días de sincronización histórica**: días concretos de la semana en los que se realiza la sincronización histórica (normalmente de lunes a sábado), evaluados también en la zona horaria del programador.
* **Horizonte histórico**: la ventana de análisis (en días) para comprobar si faltan puntos de precio históricos (por defecto: 14 días).
* **Zona horaria**: la zona horaria IANA (`scheduler_timezone`) en la que se almacenan y evalúan las horas y los días anteriores. La ventana modal muestra el reloj UTC del servidor junto a la zona horaria, para que puedas calcular el desfase; el backend convierte cada franja local en un instante UTC solo cuando decide si un trabajo debe ejecutarse. Los valores no válidos se restablecen a UTC.

### 📜 Registros del programador

Haz clic en **Ver registros** para abrir el inspector de registros. Esta ventana modal muestra una lista de las ejecuciones recientes del programador:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

El registro informa de la marca de tiempo de la ejecución, el nombre del trabajo, el estado (éxito/error), la duración de la ejecución y los detalles estructurados de los activos procesados, las fuentes de precios y cualquier traza de error.

---

## 🗄️ Cachés del servidor {: #server-caches }

LibreFolio mantiene varias **cachés en memoria** en el backend (obtención de precios, resultados de búsqueda, cálculos de cartera, respuestas de proveedores, entre otras) para que las solicitudes repetidas no consulten a los proveedores de datos externos en cada ocasión. La pestaña **Configuración global** termina con un **panel de caché** (categoría Memoria) que enumera cada caché registrada por nombre, con sus columnas de **tamaño actual / tamaño máximo** y **TTL** (tiempo de vida) — se puede hacer clic en cada cabecera de columna para ordenar por nombre, tamaño o TTL; un botón **Actualizar** vuelve a leer las estadísticas en vivo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Server caches panel in Global Settings (Memory category)">
</div>

**Quién puede hacer qué:**

- 👁️ **Leer el estado** está disponible para **cualquier usuario autenticado** (`GET /api/v1/settings/cache/status`).
- 🧹 **Vaciar** es **solo para administradores y requiere que la página esté desbloqueada** (los botones aparecen solo para superusuarios en modo edición): cada fila tiene su propio botón **Vaciar** (`POST /api/v1/settings/cache/clear/{name}`), y el encabezado del panel tiene un botón **Vaciar todo** (`POST /api/v1/settings/cache/clear-all`).

!!! warning "Vaciar una caché ralentiza la siguiente consulta"

    Ambas acciones de vaciado piden confirmación, y con razón: después de un vaciado, la siguiente solicitud de esos datos **vuelve a consultar a los proveedores externos**, por lo que cabe esperar una ralentización comparable a un reinicio del servidor mientras las cachés se rellenan. Las cachés también se vacían en cada reinicio del servidor; vaciarlas solo sirve para forzar datos nuevos sin reiniciar.

---

## 🔧 Notas técnicas

- 🗃️ La configuración se almacena como **pares clave-valor** en la tabla `global_settings`
- 🔀 Los valores se almacenan como cadenas y se convierten al tipo adecuado (`int`, `bool`, `str`) al leerlos
- 🔒 En el arranque con varios trabajadores, la configuración se inicializa con `INSERT ... ON CONFLICT DO NOTHING` para evitar condiciones de carrera
- ⚡ Los cambios surten efecto **de inmediato** — no se requiere reiniciar el servidor
