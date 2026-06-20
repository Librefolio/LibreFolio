# 🛡️ Configuración Global

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Configuración Global (Administrador)">
</div>

!!! warning "Admin access required"

    La pestaña de **Configuración Global** solo es visible para los usuarios con el rol de **ADMIN**.

La configuración global afecta a todos los usuarios de la instancia:

| Configuración | Descripción |
|---------|-------------|
| **Registro** | Activar o desactivar el autoregistro de nuevos usuarios |
| **Idioma Predeterminado** | Idioma fallback para nuevos usuarios |
| **Moneda Predeterminada** | Moneda base predeterminada para cuentas nuevas |
| **Tiempo de Espera de Sesión** | Tiempo de espera por inactividad en minutos |
| **Programador** | Activar o desactivar el demonio de sincronización automática de datos de mercado en segundo plano |

---

## 🕐 Programador de Datos de Mercado

Cuando el programador de segundo plano está activado, los administradores pueden configurar los parámetros de sincronización e inspeccionar los registros de ejecución en segundo plano directamente desde la interfaz de usuario.

### ⚙️ Configurar Programador

Haga clic en el botón **Configurar** en la fila del Programador para personalizar las frecuencias y los parámetros de ejecución:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modal de Configuración del Programador">
</div>

* **Frecuencia de Precio Actual**: La frecuencia (en minutos) con la que el demonio obtiene cotizaciones en tiempo real para mantener actualizada la caché del panel de control (predeterminado: 10m).
* **Horas de Sincronización de Historial**: Horas específicas del día (separadas por comas, ej. `06:00,23:00`) para ejecutar las actualizaciones del cierre diario histórico.
* **Días de Sincronización de Historial**: Días específicos de la semana en los que se ejecuta la sincronización histórica (generalmente de lunes a sábado).
* **Horizonte de Historial**: La ventana de análisis retrospectivo (en días) para verificar si faltan puntos de precios históricos (predeterminado: 14 días).

### 📜 Registros del Programador

Haga clic en **Ver Registros** para abrir el inspector de registros. Este modal muestra una lista de las ejecuciones recientes del programador:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modal de Registros del Programador">
</div>

Informa la marca de tiempo de ejecución, el nombre del trabajo, el estado (Success/Error), la duración de la ejecución y los detalles estructurados de los activos procesados, las fuentes de precios y cualquier traza de error.

---

## 🔗 Relacionados

- ⚙️ **[Descripción General de la Configuración](index.md)** — Descripción general de la configuración
- 👤 **[Preferencias de Usuario](preferences.md)** — Preferencias de perfil y visualización
- ℹ️ **[Acerca de](about.md)** — Información de versión y licencia
