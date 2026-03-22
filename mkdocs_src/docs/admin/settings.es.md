# ⚙️ Configuraciones Globales

LibreFolio tiene un conjunto de **configuraciones de sistema** que afectan a todos los usuarios. Estos son gestionados por administradores y almacenados en la base de datos.

---

## 👁️ Visualización y Edición de Configuraciones

### 🖥️ Desde la Interfaz

1. Navegar a **Configuraciones** (icono de engranaje en la barra lateral)
2. Hacer clic en la pestaña **Configuraciones Globales** (visible solo para administradores y superusuarios)
3. Hacer clic en el **icono de candado** junto a una configuración para desbloquearla y poder editarla
4. Modificar el valor y el cambio se guarda automáticamente

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Configuraciones Globales" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Solo Administradores"
 Solo los usuarios con privilegios de **superusuario** pueden modificar las configuraciones globales. Los usuarios no administradores ven una vista de solo lectura.

### 💻 Desde la CLI

Para inicializar las configuraciones predeterminadas (solo crea las que faltan):

```bash
./dev.py user init-settings
```

---

## 📋 Configuraciones Disponibles

| Clave | Tipo | Predeterminado | Descripción |
|-----|------|----------------|-------------|
| `session_ttl_hours` | int | `24` | Tiempo de expiración del token JWT en horas. Tras este periodo, los usuarios deben iniciar sesión nuevamente. |
| `enable_registration` | bool | `true` | Si está permitido el registro de nuevos usuarios. Establezca a `false` para prevenir nuevos registros. |
| `require_email_verification` | bool | `false` | Si los nuevos usuarios deben verificar su correo electrónico antes de acceder al sistema. |
| `max_file_upload_mb` | int | `10` | Tamaño máximo de archivo subido en megabytes. Aplica a todas las subidas (recursos estáticos e informes de corredor). |
| `auto_sync_fx_rates` | bool | `true` | Habilitar la sincronización diaria automática de tipos de cambio de divisas desde los proveedores configurados. |
| `auto_sync_prices` | bool | `true` | Habilitar la sincronización automática de precios de activos desde proveedores (Yahoo Finance, etc.). |
| `price_sync_interval_hours` | int | `6` | Frecuencia de sincronización de precios de activos, en horas. |
| `default_currency` | str | `EUR` | Moneda de visualización predeterminada para usuarios recién registrados. Los usuarios pueden anular esto en su configuración personal. |
| `default_language` | str | `en` | Idioma predeterminado para usuarios recién registrados. Soportados: `en`, `it`, `fr`, `es`. |

---

## 🗂️ Categorías

Las configuraciones se agrupan en categorías en la interfaz:

### 🕐 Sesión
- ⏱️ `session_ttl_hours` — Controla la duración de la sesión de usuario

### 🛡️ Seguridad
- 📝 `enable_registration` — Abrir/cerrar el registro
- ✉️ `require_email_verification` — Requerir verificación de correo electrónico

### 📤 Sincronización y Subidas
- 💱 `auto_sync_fx_rates` — Sincronización automática de tipos de cambio
- 📈 `auto_sync_prices` — Sincronización automática de precios de activos
- ⏰ `price_sync_interval_hours` — Frecuencia de sincronización de precios
- 📦 `max_file_upload_mb` — Límite de tamaño de archivo

### 🌍 Valores Predeterminados
- 💰 `default_currency` — Moneda predeterminada para nuevos usuarios
- 🗣️ `default_language` — Idioma predeterminado para nuevos usuarios

---

## 🔧 Notas Técnicas

- 🗃️ Las configuraciones se almacenan como **pares clave-valor** en la tabla `global_settings`
- 🔀 Los valores se almacenan como cadenas y se convierten al tipo apropiado (`int`, `bool`, `str`) al ser leídos
- 🔒 Al inicio de múltiples procesos de trabajo, las configuraciones se inicializan con `INSERT ... ON CONFLICT DO NOTHING` para evitar condiciones de carrera
- ⚡ Los cambios surten efecto **inmediatamente** — no se requiere reiniciar el servidor
