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
- **Restablecer** y **Restablecer Todo** rellenan los valores predeterminados, listos para guardar.
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
| ⏳ Sesión | **Duración de Sesión** | 24 horas | Cuánto tiempo permanecen los usuarios con la sesión iniciada. Redúcela en dispositivos compartidos; un nuevo valor se aplica a partir del siguiente inicio de sesión de cada usuario. |
| 🛡️ Seguridad | **Habilitar registro** | Activado | Permite que se registren nuevas personas. Desactívalo cuando todos tengan una cuenta, sobre todo si se puede acceder a la instancia desde internet. La primera cuenta de una instancia nueva siempre se puede crear. |
| 🛡️ Seguridad | **Verificación Email Requerida** | Desactivado | Las cuentas nuevas deben abrir un enlace enviado por correo a su dirección antes de poder iniciar sesión; la primera cuenta nunca espera, y las cuentas existentes no cambian. Solo se activa mientras el correo funciona y `LIBREFOLIO_PUBLIC_URL` se puede usar: hasta entonces el interruptor aparece en gris. Consulta *Email Verification* en [Correo](email.md). |
| 🔄 Tarea de actualización | **Planificador Activado** | Activado | Activa o desactiva las actualizaciones automáticas de precios y tipos de cambio: consulta [Planificador de datos de mercado](#market-data-scheduler). |
| 🧠 Memoria | **Tamaño Máx. Subida** | 10 MB | El archivo más grande que los usuarios pueden subir, incluidos los informes del bróker. Auméntalo si se rechaza una exportación grande. |
| 🌍 Predeterminados | **Divisa predeterminada** | `EUR` | La moneda en la que informan los nuevos usuarios. |
| 🌍 Predeterminados | **Idioma predeterminado** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` o 🇪🇸 `es`. |
| 🌍 Predeterminados | **Tema predeterminado** | `auto` | ☀️ `light`, 🌙 `dark`, o 🖥️ `auto`, que sigue al dispositivo. |

Los nuevos usuarios parten de los tres valores predeterminados: la [configuración de bienvenida](../user/getting-started.md#welcome-setup)
muestra su idioma y su moneda ya rellenados. Cambiar un valor predeterminado más adelante no afecta a las
[Preferencias](../user/settings/preferences.md) de los usuarios existentes.

---

## 🕐 Planificador de datos de mercado {: #market-data-scheduler }

El planificador mantiene actualizados por sí solo los precios y los tipos de cambio, incluso cuando no hay nadie con la sesión iniciada:

- 💰 **Actualización de Precios Actuales** — cada pocos minutos, el último precio de cada activo que tenga
  un proveedor de precios.
- 📊 **Sincronización Histórica** — en los días y horas que elijas, los precios diarios de esos activos y los
  tipos de cada par FX con un proveedor, durante al menos el **Horizonte de recuperación**, para rellenar cualquier
  hueco. Para un activo o un par cuyo último precio o tipo guardado es más antiguo, se remonta hasta ese día, como
  máximo un año; un activo sin ningún precio guardado solo recibe el horizonte, porque el planificador nunca descarga
  un historial completo. Los pares que solo tienen tipos manuales se omiten.

Si el servidor está apagado o en suspensión a una hora de sincronización, la sincronización histórica
que se ha perdido se ejecuta en cuanto el servidor vuelve, sin esperar a la siguiente hora de sincronización: un
servidor apagado durante semanas rellena todo su hueco.

### ⚙️ Configurar la programación

Desbloquea la pestaña, abre **Tarea de actualización** y haz clic en **Configurar…** en la fila **Configuración del Horario**.
El diálogo tiene su propio botón **Guardar**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modal de configuración del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Campo | Predeterminado | Qué establece |
|---|---|---|
| **Zona horaria** | `UTC` | La zona horaria de las horas y los días siguientes; el reloj UTC del servidor se muestra junto a ella. |
| **Actualizar cada** | 10 minutos | Con qué frecuencia se actualizan los precios actuales, de 1 a 1440 minutos. |
| **Horarios de sincronización** | `06:00`, `23:00` | Cuándo se ejecuta la sincronización del historial; **Agregar horario** añade una franja. |
| **Días de sincronización** | Lun a Sáb | Los días de la sincronización del historial. |
| **Horizonte de recuperación** | 14 días | Cuántos días pasados comprueba como mínimo cada sincronización del historial, de 1 a 365. Se remonta más atrás, hasta un año, cuando el último precio o tipo guardado de un activo o de un par es más antiguo. |

Mantén al menos una hora y un día. Consejo: una sincronización del historial después del cierre de los mercados (por ejemplo,
`22:00`) obtiene los datos más completos.

??? warning "🌍 Cambiar la zona horaria — las tareas se desplazan en el tiempo"

    Las horas y los días conservan sus valores, pero cuentan en la nueva zona horaria, por lo que las tareas se ejecutan en otro
    momento. También siguen su horario de verano: `06:00` en `Europe/Rome` se ejecuta a las 05:00 UTC
    en invierno y a las 04:00 UTC en verano.

### 📜 Leer el registro del planificador

La fila **Estado del planificador** muestra la última actualización del precio actual, con un punto para su resultado.
Mientras haya un reintento pendiente, una línea más indica su hora: **Fallido: nuevo intento a las …** tras una
actualización que no pudo terminar; si no, **Elementos en pausa reintentados a las …** para los precios aplazados
porque su proveedor está en pausa.
Haz clic en la fila (o en **Detalles…**) para abrir el **Registro de ejecución del planificador**. Solo los administradores pueden
leer el estado y el registro.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modal del registro del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Cada entrada es una ejecución: tarea, hora, duración y cuántos elementos se completaron correctamente. 🟢 **OK**: todos,
  o nada que hacer; 🟡 **Parcial**: algunos fallaron, o se aplazaron porque su proveedor está en pausa tras demasiadas
  solicitudes; 🔴 **Error**: ninguno se completó correctamente y ninguno se aplazó.
- Haz clic en una entrada para ver cada activo o par FX, su proveedor y los precios modificados (**Delta**).
  Pasa el cursor sobre un error para leerlo completo; haz doble clic en él (mantén pulsado en un teléfono) para copiarlo.
- Un elemento aplazado muestra un icono de pausa y **Aplazado: proveedor en pausa**: pasa el cursor sobre la etiqueta
  para leer el mensaje del proveedor. La entrada cuenta los elementos aplazados con ⏸, junto a ✓ y ✗ (por ejemplo
  `3/5 ✓ · 1 ⏸ · 1 ✗`), y **Reintento a las …** en su encabezado indica la hora fijada para reintentarlos.
- Filtra por tarea, estado o periodo, desde la última hora hasta los últimos 30 días. Solo se conservan las ejecuciones
  más recientes.

---

## 🗄️ Cachés del servidor {: #server-caches }

Para mantenerse rápido, LibreFolio guarda en memoria las respuestas recientes de los proveedores y los resultados calculados. El
panel **Estado de la caché**, al final de la categoría **Memoria**, enumera cada caché con su
**Tam. / Máx** y su **TTL** (cuánto tiempo se conserva una entrada). Haz clic en el encabezado de una columna para ordenar;
**Actualizar** refresca los números.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Panel de cachés del servidor en Configuración global (categoría Memoria)">
</div>

Todos pueden ver el panel. Un administrador, con la pestaña desbloqueada, puede vaciar una caché con
**Vaciar** o todas con **Vaciar todo**, para forzar datos actualizados sin reiniciar. Reiniciar
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
