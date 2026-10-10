# ⚙️ Configuración global

La configuración global se aplica a toda la instancia y a todos los usuarios. Se almacena en la base de datos:
todos pueden leerla, solo los administradores pueden cambiarla.

---

## ✏️ Cambiar una configuración

### 🔓 1. Desbloquear la pestaña

Abre **Configuración** (icono de engranaje en la barra lateral), luego la pestaña **Administración**: su panel **Configuración global**
agrupa la configuración por categoría. Haz clic en el **icono de candado** (🔒) en el encabezado para desbloquearla.
Solo los administradores (superusuarios) tienen el candado; todos los demás obtienen una vista de solo lectura.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Configuración global" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Editar y guardar

- No se guarda nada hasta que hagas clic en **Guardar** junto a una configuración, o en **Guardar todo** en el encabezado.
  **Deshacer** y **Deshacer todo** restauran los valores guardados.
- **Restablecer a predeterminado** y **Restablecer todo a predeterminados** rellenan los valores predeterminados, listos para guardar.
- Los valores guardados se aplican de inmediato, sin reiniciar.

??? note "🔒 Bloquear con cambios sin guardar — cuando aparece un diálogo para preguntar primero"

    Al hacer clic en el candado con cambios sin guardar, se pregunta si quieres descartarlos. **Cancelar** conserva tus
    ediciones; **Descartar** restaura los valores guardados y bloquea la pestaña.

??? tip "💻 Configuraciones faltantes — recréalas desde la línea de comandos"

    Cada inicio del servidor recrea cualquier configuración faltante con su valor predeterminado. Para hacerlo sin
    reiniciar, ejecuta la [herramienta de línea de comandos](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    Los valores que cambiaste se conservan.

---

## 📋 Qué hace cada configuración

| Categoría | Configuración | Predeterminado | Qué hace — cuándo cambiarla |
|---|---|---|---|
| ⏳ Sesión | **Duración de la sesión** | 24 horas | Cuánto tiempo permanecen los usuarios con la sesión iniciada. Redúcela en dispositivos compartidos; un nuevo valor se aplica a partir del siguiente inicio de sesión de cada usuario. |
| 🛡️ Seguridad | **Habilitar registro** | Activado | Permite que se registren nuevas personas. Desactívalo cuando todos tengan una cuenta, sobre todo si se puede acceder a la instancia desde internet. La primera cuenta de una instancia nueva siempre se puede crear. |
| 🛡️ Seguridad | **Requerir verificación por correo electrónico** | Desactivado | Aún no está activo: el envío de correos es una función planificada, por lo que el interruptor es de solo lectura y está marcado como **Próximamente**. |
| 🔄 Tarea de actualización | **Planificador habilitado** | Activado | Activa o desactiva las actualizaciones automáticas de precios y tipos de cambio: consulta [Planificador de datos de mercado](#market-data-scheduler). |
| 🧠 Memoria | **Tamaño máximo de archivo subido** | 10 MB | El archivo más grande que los usuarios pueden subir, incluidos los informes del bróker. Auméntalo si se rechaza una exportación grande. |
| 🌍 Predeterminados | **Moneda predeterminada** | `EUR` | La moneda en la que informan los nuevos usuarios. |
| 🌍 Predeterminados | **Idioma predeterminado** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` o 🇪🇸 `es`. |
| 🌍 Predeterminados | **Tema predeterminado** | `auto` | ☀️ `light`, 🌙 `dark`, o 🖥️ `auto`, que sigue al dispositivo. |

Los nuevos usuarios parten de los tres valores predeterminados: la [configuración de bienvenida](../user/getting-started.md#welcome-setup)
muestra su idioma y su moneda ya rellenados. Cambiar un valor predeterminado más adelante no afecta a las
[Preferencias](../user/settings/preferences.md) de los usuarios existentes.

---

## 🕐 Planificador de datos de mercado {: #market-data-scheduler }

El planificador mantiene actualizados por sí solo los precios y los tipos de cambio, incluso cuando no hay nadie con la sesión iniciada:

- 💰 **Actualización del precio actual** — cada pocos minutos, el último precio de cada activo que tenga
  un proveedor de precios.
- 📊 **Sincronización del historial** — en los días y horas que elijas, los precios diarios de esos activos y los
  tipos de cada par FX con un proveedor, durante el **Horizonte de retrospectiva**, para rellenar cualquier hueco. Los pares
  que solo tienen tipos manuales se omiten.

### ⚙️ Configurar la programación

Desbloquea la pestaña, abre **Tarea de actualización** y haz clic en **Configurar…** en la fila **Configuración de la programación**.
El diálogo tiene su propio botón **Guardar**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modal de configuración del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Campo | Predeterminado | Qué establece |
|---|---|---|
| **Zona horaria** | `UTC` | La zona horaria de las horas y los días siguientes; el reloj UTC del servidor se muestra junto a ella. |
| **Actualizar cada** | 10 minutos | Con qué frecuencia se actualizan los precios actuales, de 1 a 1440 minutos. |
| **Horas de sincronización** | `06:00`, `23:00` | Cuándo se ejecuta la sincronización del historial; **Añadir hora** añade una franja. |
| **Días de sincronización** | Lun a Sáb | Los días de la sincronización del historial. |
| **Horizonte de retrospectiva** | 14 días | Cuántos días pasados comprueba cada sincronización del historial, de 1 a 365. |

Mantén al menos una hora y un día. Consejo: una sincronización del historial después del cierre de los mercados (por ejemplo,
`22:00`) obtiene los datos más completos.

??? warning "🌍 Cambiar la zona horaria — las tareas se desplazan en el tiempo"

    Las horas y los días conservan sus valores, pero cuentan en la nueva zona horaria, por lo que las tareas se ejecutan en otro
    momento. También siguen su horario de verano: `06:00` en `Europe/Rome` se ejecuta a las 05:00 UTC
    en invierno y a las 04:00 UTC en verano.

### 📜 Leer el registro del planificador

La fila **Estado del planificador** muestra la última actualización del precio actual, con un punto para su resultado.
Haz clic en la fila (o en **Detalles…**) para abrir el **Registro de ejecución del planificador**. Solo los administradores pueden
leer el estado y el registro.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modal del registro del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Cada entrada es una ejecución: tarea, hora, duración y cuántos elementos se completaron correctamente. 🟢 **OK**: todos,
  o nada que hacer; 🟡 **Parcial**: algunos fallaron; 🔴 **Error**: ninguno se completó correctamente.
- Haz clic en una entrada para ver cada activo o par FX, su proveedor y los precios modificados (**Delta**).
  Pasa el cursor sobre un error para leerlo completo; haz doble clic en él (mantén pulsado en un teléfono) para copiarlo.
- Filtra por tarea, estado o periodo, desde la última hora hasta los últimos 30 días. Solo se conservan las ejecuciones
  más recientes.

---

## 🗄️ Cachés del servidor {: #server-caches }

Para mantenerse rápido, LibreFolio guarda en memoria las respuestas recientes de los proveedores y los resultados calculados. El
panel **Estado de la caché**, al final de la categoría **Memoria**, enumera cada caché con su
**Tamaño / Máx.** y su **TTL** (cuánto tiempo se conserva una entrada). Haz clic en el encabezado de una columna para ordenar;
**Actualizar** refresca los números.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Panel de cachés del servidor en Configuración global (categoría Memoria)">
</div>

Todos pueden ver el panel. Un administrador, con la pestaña desbloqueada, puede vaciar una caché con
**Borrar** o todas con **Borrar todo**, para forzar datos actualizados sin reiniciar. Reiniciar
también vacía todas las cachés.

!!! warning "Vaciar una caché ralentiza la siguiente consulta"

    Ambas acciones piden confirmación primero. Después de vaciar, la siguiente solicitud de esos datos vuelve
    a los proveedores, así que espera una ralentización similar a la de reiniciar el servidor mientras las cachés se vuelven
    a llenar.

??? note "🧵 Varios workers — cuando el servidor se ejecuta con `--workers`"

    Cada proceso worker tiene sus propias cachés. El panel muestra y vacía las del worker que
    respondió; reinicia el servidor para vaciarlas todas.

---

## 🔗 Relacionado

- 📝 **[Variables de entorno](configuration.md)** — La configuración que reside en `.env` en su lugar
- 👤 **[Preferencias de usuario](../user/settings/preferences.md)** — Lo que cada usuario puede cambiar por sí mismo
- 🧑‍💻 Para desarrolladores: **[Sistema de configuración](../developer/architecture/settings.md)**,
  **[Registro de cachés](../developer/architecture/settings_cache.md)** y
  **[Planificador de datos de mercado](../developer/backend/scheduler.md)**
