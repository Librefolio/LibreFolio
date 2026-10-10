# 🧠 Exportación IA de cartera

Exporta toda tu cartera, tal como la muestra el Panel, para preguntar a una IA sobre su estructura, su
rendimiento, un plan de inversión recurrente o tus minusvalías fiscales. Las opciones y cómo pegar están en
el [Resumen de la exportación IA](index.md).

---

## 📍 Dónde encontrarla

En el **Panel**, selecciona **exportación IA** en la barra de herramientas, junto a **Actualizar**. Se abre primero en
**Plan de inversión recurrente**.

La exportación sigue el [Panel](../dashboard/index.md):

- los brókeres que **posees** con una participación superior al 0%, restringidos por el filtro de brókeres cuando está activado;
  los brókeres compartidos contigo como editor o lector se omiten;
- la divisa del Panel, con el último día de su rango de fechas como fecha de exportación.

El botón se activa una vez que el Panel ha cargado tus brókeres, y permanece desactivado si no posees ninguno
con una participación superior al 0%.

---

## 📤 Datos de exportación

| Elección | Qué obtienes |
| :--- | :--- |
| **Resumen e historial de la cartera** | Posiciones, efectivo, asignaciones, rendimiento, flujos, ingresos, costes registrados, un resumen económico FIFO, un contexto de mercado compacto por activo y caída |
| **Historial de activos de la cartera** | Precios detallados, rendimientos, indicadores, estados y eventos para cada activo que posees, con cobertura |

---

## 🎯 Análisis

| Análisis | Qué hace la IA |
| :--- | :--- |
| **Plan de inversión recurrente** | Planifica inversiones recurrentes condicionales a partir de tus cifras, preguntando solo lo que le falta |
| **Rebalanceo de cartera** | Compara tu asignación con los objetivos que le das y plantea rutas de rebalanceo condicionales |
| **Rendimiento de la cartera y factores del mercado** | Explica tu resultado e investiga factores de mercado con fecha para cada activo que posees: usa una IA que pueda buscar en la web |
| **Estrategias de compensación de minusvalías** | Explora cómo las minusvalías fiscales disponibles o que expiran podrían compensar plusvalías, usando tus lotes FIFO |

??? note "📅 Plan de inversión recurrente — qué te preguntará la IA"

    La IA parte de tus datos y pregunta solo lo que cambia el plan: cuánto puedes invertir y
    con qué frecuencia, tu objetivo y horizonte, cuánta caída puedes soportar y límites prácticos como
    la liquidez, los brókeres, las órdenes mínimas o los activos que hay que evitar. Nunca adivina estas respuestas, puede
    esbozar escenarios condicionales mientras tanto, y compara invertir de una vez con invertir
    por etapas.

??? note "🧾 Estrategias de compensación de minusvalías — ten a mano tus datos fiscales"

    Los lotes FIFO son el cálculo económico de LibreFolio, no tu posición fiscal legal. Antes de comparar
    rutas, la IA pregunta por tu residencia y régimen fiscal, el tipo de cuenta y tu inventario oficial
    de minusvalías fiscales (por ejemplo, el italiano *cassetto fiscale*) con importes, categorías y
    fechas de vencimiento. Nunca sugiere una operación solo por motivos fiscales.

---

## 🔗 Relacionado

- 🧠 **[Resumen de la exportación IA](index.md)** — opciones, pegado y privacidad
- 📊 **[Panel](../dashboard/index.md)** — el alcance que sigue esta exportación
