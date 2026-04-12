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
| `auto_sync_fx_rates` | bool | `true` | Habilitar la sincronización diaria automática de los tipos de cambio FX desde los proveedores configurados. |
| `auto_sync_prices` | bool | `true` | Habilitar la sincronización automática de los precios de activos desde los proveedores (Yahoo Finance, etc.). |
| `price_sync_interval_hours` | int | `6` | Frecuencia de sincronización de los precios de los activos, en horas. |
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
- 💱 `auto_sync_fx_rates` — Sincronización automática de tipos de cambio FX
- 📈 `auto_sync_prices` — Sincronización automática de precios de activos
- ⏰ `price_sync_interval_hours` — Frecuencia de sincronización de precios
- 📦 `max_file_upload_mb` — Límite de tamaño de archivo

### 🌍 Valores Predeterminados
- 💰 `default_currency` — Moneda predeterminada para usuarios recién registrados
- 🗣️ `default_language` — Idioma predeterminado para usuarios recién registrados

---

## 🔧 Notas Técnicas

- 🗃️ Las configuraciones se almacenan como **pares clave-valor** en la tabla `global_settings`
- 🔀 Los valores se almacenan como cadenas y se convierten al tipo apropiado (`int`, `bool`, `str`) al leerlos
- 🔒 En el arranque con múltiples workers, las configuraciones se inicializan con `INSERT ... ON CONFLICT DO NOTHING` para evitar condiciones de carrera
- ⚡ Los cambios surten efecto **inmediatamente** — no se requiere reiniciar el servidor
