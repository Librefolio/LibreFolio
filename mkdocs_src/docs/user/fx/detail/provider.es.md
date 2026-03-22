# 🔌 Configuración de Proveedores

Cada par de divisas en LibreFolio cuenta con el respaldo de uno o más **proveedores de datos**[^1] —bancos centrales que suministran los datos de tipo de cambio—. La Configuración de Proveedores le permite ver y modificar qué proveedores se utilizan para un par específico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuración de Proveedores" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Cómo acceder

Haga clic en el botón **Proveedor** (⚙️) en la barra de herramientas del gráfico, en la página de detalle del par. Esto abre el modal de configuración de proveedores que muestra la configuración de rutas[^1] actual.

---

## 📋 Lo que verá

El modal muestra:

- 🛤️ **Ruta(s) actual(es)** — La(s) fuente(s) de datos activa(s) para este par, en orden de prioridad
- 🔀 **Tipo de ruta** — Si es una **ruta directa** (proveedor único) o una **ruta en cadena**[^2] (que implica múltiples conversiones intermediarias a través de una moneda intermediaria)
- 🏛️ **Detalles de cada proveedor** — Nombre, icono y moneda base de cada proveedor en la ruta

---

## 🔧 Cambiar proveedores

Para cambiar la fuente de datos de un par:

1. Abra el modal de Configuración de Proveedores
2. **Elimine** la ruta actual si es necesario
3. **Añada una nueva ruta** — el sistema descubrirá las rutas disponibles (igual que al [añadir un nuevo par](../add-pair.md))
4. Seleccione la nueva ruta y **confirme**

La siguiente sincronización obtendrá datos del nuevo proveedor.

---

## 🔢 Prioridad y Respaldo

Cuando se configuran múltiples rutas para un par:

- Las rutas se prueban **en orden de prioridad** (superior = mayor prioridad)
- Si el proveedor principal falla (timeout, error de API), el sistema automáticamente **recurre**[^3] a la siguiente ruta
- Puede **reordenar** las rutas para cambiar las prioridades

!!! example "Ejemplo de Respaldo"
 EUR/USD configurado con:

 1. **BCE**[^4] (principal) — Banco Central Europeo
 2. **FED**[^5] (respaldo) — Reserva Federal

 Si la API del BCE no está disponible durante la sincronización, el sistema utilizará automáticamente la FED.

---

## 📚 Relacionado

- ➕ **[Añadir un par](../add-pair.md)** — Descubrimiento completo de rutas (directas + en cadena)
- 🔄 **[Sincronización](../sync.md)** — Cómo la sincronización utiliza los proveedores configurados
- 📋 **[Lista de Proveedores de FX](../../../developer/backend/fx/providers_list.md)** — Detalles técnicos de cada proveedor (BCE[^4], FED[^5], BOE[^6], SNB[^7])

!!! tip "🔗 Cómo se calculan las rutas en cadena"
 Para ver el algoritmo matemático detrás de las cadenas de conversión multi-salto, consulte [Algoritmo de Cadena FX](../../../developer/frontend/fx-chain-algorithm.md).

[^1]: En este contexto, "proveedor" y "ruta" se refieren a la secuencia específica de uno o más bancos centrales (y monedas intermediarias, en caso de rutas en cadena) de los cuales el sistema obtiene los tipos de cambio para un par de divisas. "Ruta" no implica un camino geográfico, sino una vía de datos técnica.
[^2]: "Ruta en cadena" (chain route) es un término técnico que describe una conversión de divisas que requiere múltiples pasos, pasando por una o más monedas intermediarias (ej: EUR → USD → JPY). Se contrapone a "ruta directa", donde la conversión es inmediata entre las dos divisas del par.
[^3]: "Respaldo" (fallback) se refiere al mecanismo automático por el cual, si la fuente de datos principal (proveedor o ruta) falla, el sistema cambia a la siguiente fuente en orden de prioridad sin intervención del usuario.
[^4]: BCE: Banco Central Europeo.
[^5]: FED: Reserva Federal de los Estados Unidos (Federal Reserve System). Aunque se usa la sigla "FED" comúnmente, su nombre oficial en español es "Reserva Federal".
[^6]: BOE: Bank of England (Banco de Inglaterra).
[^7]: SNB: Swiss National Bank (Banco Nacional Suizo).
