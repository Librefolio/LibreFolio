# 🔄 Sincronización de FX

Los pares FX con un proveedor obtienen sus tipos de fuentes oficiales de bancos centrales. LibreFolio los descarga
cuando añades un par FX, cada vez que lo solicites y —si tu administrador lo ha activado— según una programación.

---

## 🔄 Sincronizar todos los pares FX

1. En la [página de FX](index.md), elige el periodo en el selector de fechas. Selecciona **Todo** para todo
   el historial.
2. Haz clic en **Sincronizar todo**. La ventana **Sincronizar tipos de cambio FX** enumera cada par FX con un proveedor: los pares FX que solo
   tienen tipos manuales no tienen nada que descargar.
3. Haz clic en **Iniciar sincronización**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progreso de la sincronización" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Lectura de los resultados

- Cada fila muestra un par FX, el proveedor que respondió, **↓** los tipos descargados y **Δ** los tipos
  que eran nuevos o cambiaron.
- Una fila ámbar significa que el proveedor no envió tipos para el periodo; una fila roja significa que la sincronización falló.
  Pasa el cursor sobre el mensaje para leerlo en su totalidad y haz clic en el botón ↻ de la fila para intentar ese par FX de nuevo.
- El resumen en la parte inferior muestra cuántos pares FX se sincronizaron y los totales. **Reintentar N fallidos** vuelve a ejecutar
  todos los pares FX fallidos.
- Un historial largo puede necesitar más tiempo: si la ventana informa *Se agotó el tiempo de espera de la solicitud*, aumenta su
  **Tiempo de espera** y luego haz clic en **Reintentar N fallidos**.

---

## 🎯 Sincronizar un par FX

- En la página de FX, el botón **Sincronizar** de la tarjeta de un par FX, o de una fila de la tabla, descarga los tipos de ese par FX
  para el periodo seleccionado. Un mensaje informa del resultado.
- En la [página de detalle](detail/index.md) del par FX, **Sincronizar** abre la ventana de sincronización para el par FX y para
  cualquier par FX o activo con el que lo compares en el gráfico.

**Sincronizar** aparece atenuado para los pares FX que solo tienen tipos manuales.

---

## ⚠️ Qué cambia una sincronización

- Las fechas del periodo que ya están almacenadas toman el valor del proveedor; las fechas que faltan se añaden.
- Las fechas fuera del periodo no se modifican.
- Si la primera ruta de un par FX falla, LibreFolio prueba la siguiente: consulta
  [Configuración del proveedor](detail/provider.md).

!!! warning "El proveedor tiene la última palabra"

    Una sincronización sobrescribe los tipos que editaste a mano dentro de su periodo. Para conservar tus propios tipos, usa un par FX
    sin proveedor (solo tipos manuales).

??? tip "🕰️ Falta historial más antiguo — cuando el gráfico de un par FX empieza más tarde de lo esperado"

    Un par FX que añades con un proveedor descarga todo su historial por sí mismo. Si el gráfico de un par FX más antiguo
    empieza más tarde que el historial del proveedor, establece el periodo en la página de FX a **Todo** y haz clic en
    **Sincronizar todo** una vez: LibreFolio descarga todo lo que publican los proveedores, hasta hoy.

---

## 🕐 Sincronización automática

Cuando tu administrador activa el planificador en segundo plano, LibreFolio actualiza por su cuenta los tipos recientes de
todos los pares FX con un proveedor, en los momentos que elijan: consulta
[Planificador de datos de mercado](../../admin/settings.md#market-data-scheduler).

---

## 🔗 Relacionado

- ➕ **[Añadir un par FX](add-pair.md)** — Rutas directas y en cadena
- 🔌 **[Proveedores de FX](providers/index.md)** — Los bancos centrales de los que LibreFolio lee los tipos
- ⚙️ **[Configuración del proveedor](detail/provider.md)** — Rutas, prioridades y fallbacks de un par FX
- 🧑‍💻 Para desarrolladores: **[Configuración y enrutamiento de FX](../../developer/backend/fx/configuration.md)**
