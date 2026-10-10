# 🧠 Exportación IA

La exportación IA copia tus datos de LibreFolio como texto listo para pegar, con una pregunta enfocada si la quieres,
para que puedas preguntar al asistente de IA que elijas sobre tu cartera, un bróker, un activo o un
par de divisas. LibreFolio nunca contacta por sí mismo con un servicio de IA.

---

## 🎯 Para qué sirve

- **Revisar con cifras reales**: un bróker, una posición, un par de divisas y tu exposición a él.
- **Planificar**: inversiones recurrentes, un rebalanceo o cómo las pérdidas fiscales que expiran podrían compensar ganancias.
- **Explicar**: qué impulsó tu rendimiento, activo por activo, con fuentes fechadas.
- **Guardar una instantánea**: solo los hechos, listos para tu propia pregunta.

Lo que copias es contexto factual, no asesoramiento de inversión.

---

## 🚀 Cómo abrirla

Selecciona **Exportación IA** (:material-brain:) en la barra de herramientas de una de estas páginas:

| Página | Qué cubre la exportación | Guía |
| :--- | :--- | :--- |
| **Panel** | Tu cartera, tal como la muestra el Panel | [Cartera](portfolio.md) |
| Una página de detalle de **Bróker** | Solo ese bróker | [Bróker](broker.md) |
| Una página de detalle de **Activo** | Ese activo y, si lo tienes, tu posición | [Activo](asset.md) |
| Una página de detalle de **FX** | Ese par de divisas y tu exposición directa a él | [FX](fx.md) |

La exportación se fecha el **último día del rango de fechas de la página**: mueve esa fecha para exportar un
momento anterior.

---

## 🧭 Elige qué exportar

El panel se abre con una selección lista para usar: cambia solo lo que necesites.

### 📤 Paso 1: Elige el tipo de exportación

Bajo **Tipo de exportación**:

- **Exportar datos** copia solo los hechos: guarda una instantánea o plantea tu propia pregunta.
- **Solicitar análisis** añade una pregunta enfocada, reglas para comprobar las cifras y la
  estructura de la respuesta esperada.

### 🗂️ Paso 2: Elige un conjunto de datos o un análisis

Abre **Conjunto de datos o análisis**: cada entrada tiene una descripción de una línea. Cada página ofrece una exportación general
de datos, un historial de mercado detallado y de dos a cuatro análisis, listados en las guías de más arriba.

### 🔍 Paso 3: Establece el nivel de detalle

Elige **Compacto**, **Estándar** (el predeterminado) o **Completo**. Los tres cubren los mismos activos,
indicadores y período; solo conservan más o menos historial. **Completo** puede ser muy extenso.

### 📅 Paso 4: Establece el período de IA

Elige **3M** (el predeterminado), **6M**, **1A** o **Personalizado** (días, semanas, meses o años), terminando
en la fecha de exportación. Si LibreFolio tiene menos historial, la exportación lo marca como parcial: nunca
inventa precios ni usa precios futuros.

### 📝 Paso 5: Añade notas (solo análisis)

Con **Solicitar análisis**, añade contexto o preguntas en **Notas para la IA**: un presupuesto mensual, una
asignación objetivo, lo que te preocupa. La IA las lee como información, no como nuevas reglas.

### 📋 Paso 6: Copia

Selecciona **Copiar exportación IA**. Después de **Preparando exportación…**, un mensaje confirma la copia con su
tamaño estimado.

??? warning "📏 Prompt largo — cuando el texto es extenso"

    El panel muestra primero el **Tamaño final del prompt** con una advertencia. Elige **Usar Compacto** para un
    texto más corto (no se muestra en Compacto), o **Copiar de todos modos**: con la misma configuración, se copiará sin
    preguntar durante un tiempo.

LibreFolio recuerda tus últimas elecciones en cada página durante unos minutos; cerrar sesión las restablece.

---

## 🤖 Pégalo en tu asistente de IA

Copias texto sin formato: un encabezado breve (qué se exportó, la fecha, el período, la divisa y el nivel de detalle)
y tus datos en tablas compactas. **Solicitar análisis** añade la pregunta y la estructura de respuesta esperada
alrededor de ellos.

1. Abre un chat nuevo en un asistente de IA en el que confíes con datos financieros.
2. Pega el texto y envíalo. Con **Solicitar análisis**, la pregunta ya está incluida.
3. Responde a las preguntas de la IA: se le indica que pregunte solo por lo que cambia el resultado (un presupuesto, un
   objetivo, tu situación fiscal) y que nunca lo adivine.

Conviene saber:

- Con **Solicitar análisis**, se le pide a la IA que responda en el idioma de tu interfaz de LibreFolio y
  que mantenga tus cifras separadas de su interpretación.
- Los análisis de **Rendimiento e impulsores del mercado** necesitan un asistente que pueda buscar en la web;
  sin él, la respuesta lo indica en lugar de inventar fuentes.
- Los activos, brókers, pares de divisas y lotes aparecen como códigos cortos (A1, B1, F1, L1) explicados en
  el texto; se le pide a la IA que responda con los nombres reales.
- Un análisis puede sugerir una exportación más en **Datos adicionales de LibreFolio**, con dónde
  encontrarla. Si la IA la pide, copia también esa exportación y pégala en el mismo chat.

---

## 🔒 Privacidad

- LibreFolio no envía la exportación a ningún sitio: solo la escribe en tu portapapeles.
- El texto contiene tus **cifras reales** y los nombres de tus brókers y activos, incluso con
  el modo privacidad activado.
- Cada página exporta solo su propio ámbito:
    - **Panel**: los brókers que posees con una participación superior al 0%, acotados por el filtro de brókers;
    - **Bróker**: solo ese bróker;
    - **Activo** y **FX**: todos los brókers que puedes abrir, incluidos los brókers compartidos contigo.
- Revisa el texto antes de pegarlo en cualquier sitio; aparece un recordatorio después de cada copia.

---

## 🛠️ Cuando algo va mal

- **Exportación IA está atenuada**: la página todavía se está cargando o, en el Panel, no posees ningún bróker
  con una participación superior al 0%.
- *Esta selección no es aplicable a los datos actuales.*: elige otro análisis.
  **Revisión de posición** necesita una posición en el activo; **Impacto de exposición FX** necesita efectivo o una
  posición vinculada al par.
- Un mensaje que termina en *Actualiza y vuelve a intentarlo.*: recarga la página.
- *El acceso al portapapeles no está disponible. Comprueba los permisos del navegador.*: permite el acceso al portapapeles para
  LibreFolio en tu navegador.

---

## 🔗 Relacionado

- 🛠️ **[Cómo funciona la exportación IA](../../developer/architecture/patterns/ai_export_snapshot.md)** — para desarrolladores
