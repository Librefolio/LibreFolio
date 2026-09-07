# 🧠 Exportación IA

La Exportación IA convierte el contexto actual de LibreFolio en texto estructurado que puedes
pegar en un asistente de IA o conservar como una instantánea portátil.

!!! important "Solo exportación al portapapeles"

    LibreFolio **no** contacta con ningún servicio de IA. Construye la instantánea
    financiera y técnica en tu servidor, la renderiza en tu navegador y la copia
    al portapapeles. Tú decides si y dónde pegarla.

## 📋 Qué Hace

La Exportación IA está disponible desde:

- la barra de herramientas del panel de control para tareas de cartera;
- la barra de herramientas del bróker para tareas de bróker;
- la barra de herramientas de la página en las páginas de detalle de Activo y FX.

El backend proporciona valoraciones, rendimiento, asignaciones, datos económicos FIFO,
exposición a FX e indicadores técnicos. El catálogo público expone intencionadamente
solo **ocho opciones autónomas de 'Exportar Datos'** y **once Análisis orientados
a tareas**. Los conjuntos de datos más pequeños del backend permanecen como bloques
internos de composición.

**Exportar Datos** copia una instantánea factual seleccionada sin instrucciones de
análisis. **Solicitar Análisis** añade un objetivo y un contrato de respuesta a una
instantánea autónoma, más una sugerencia pública de exportación complementaria cuando
es útil. Las notas opcionales y el idioma de respuesta solicitado se aplican solo a
los análisis.

## 🚀 Cómo Usarlo

1. Abre la página de cartera, bróker, activo o FX correspondiente.
2. Selecciona **Exportación IA** (:material-brain:).
3. Elige **Exportar Datos** o **Solicitar Análisis** y, a continuación, selecciona un conjunto de datos o un Análisis.
4. Elige el período de IA y el nivel de detalle.
5. Para un análisis, añade notas opcionales cuando el Análisis las admita.
6. Selecciona **Copiar Exportación IA** y pega el resultado en la herramienta de tu elección.

## 🎛️ Opciones de Exportación

| Opción | Significado |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tipo de exportación** | **Exportar Datos** crea un prompt factual de conjunto de datos. **Solicitar Análisis** añade el objetivo del Análisis, instrucciones de verificación, contrato de respuesta y conjuntos de datos relevantes. |
| **Conjunto de datos o análisis** | Las opciones disponibles provienen del catálogo actual del runtime de LibreFolio para la página/dominio. |
| **Período de IA** | **3M**, **6M**, **1Y** o Personalizado cuando se ofrece. El período termina en la fecha de la instantánea. El historial parcial de la fuente se mantiene explícito. |
| **Nivel de detalle** | **Compacto**, **Estándar** y **Completo** mantienen el mismo universo de entidades. Las instantáneas generales usan mini-historiales uniformes progresivamente más densos; las exportaciones de mercado detalladas usan la política de muestreo técnico completa. Completo puede ser grande y no siempre es necesario. |
| **Notas para la IA** | Disponibles para análisis compatibles. Añaden contexto opcional del usuario como un bloque de datos serializado de forma segura. |

El tipo de exportación, la selección, el detalle, el período de IA y las notas
en borrador permanecen en la memoria del navegador durante 10 minutos por contexto de página.
Cerrar el panel o navegar fuera de la página los conserva dentro de esa ventana.
La caducidad, el cierre de sesión o cualquier nuevo inicio de sesión restablecen todos
los paneles de Exportación IA a sus valores predeterminados; los borradores no se
persisten en `localStorage`.

## 📤 Datos de Exportación Disponibles

| Página | Instantánea general | Historial de mercado detallado |
| ---------- | ---------------------------------------- | --------------------------------------- |
| Panel de control | **Descripción general e Historial de cartera** | **Historial de activos de cartera** |
| Bróker | **Descripción general e Historial de bróker** | **Historial de activos de bróker** |
| Activo | **Posición e Historial de Mercado (completo)** | **Solo Historial de Mercado (sin posiciones)** |
| FX | **Mercado y Exposición de FX** | **Historial de Mercado de FX** |

Las instantáneas generales combinan hechos económicos actuales con una ruta histórica
compacta y un contexto de mercado centrado. Los historiales de mercado detallados
contienen precios o tasas observados más densos, indicadores, estados, eventos y cobertura.

## 🗂️ Análisis Disponibles

### 📊 Cartera

| Tarea | Propósito |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Plan de Inversión Recurrente | Revisar la estructura de la cartera, los flujos de caja y las restricciones para inversiones recurrentes. |
| Reequilibrio de Cartera | Comparar la asignación actual con el contexto de diversificación y asignación objetivo. |
| Rendimiento de Cartera y Factores de Mercado | Conciliar el rendimiento e investigar los factores fechados de corto y largo horizonte para cada activo mantenido sin exagerar la causalidad. |
| Estrategias de Compensación de Pérdidas Fiscales | Explorar cómo las pérdidas fiscales disponibles o por vencer podrían compensar ganancias elegibles usando evidencia económica FIFO y un inventario fiscal oficial explícito. |

### 🏦 Bróker

| Tarea | Propósito |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| Revisión de bróker | Resumir posiciones, efectivo, actividad, rendimiento y cobertura de datos para un bróker. |
| Rendimiento de bróker y factores de mercado | Conciliar el rendimiento del bróker seleccionado e investigar los factores fechados para cada activo mantenido. |
| Estrategias de Compensación de Pérdidas Fiscales | Explorar vías de compensación de pérdidas fiscales usando evidencia económica FIFO del bróker seleccionado y el inventario fiscal oficial del usuario. |

### 📈 Activo

| Tarea | Propósito |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Revisión de Posición | Revisar el tamaño, la base de costo, el rendimiento, los ingresos y el contexto de concentración. |
| Análisis de Mercado de Activo | Revisar el historial de cierres observados, rendimientos, tendencia, momentum, volatilidad, Drawdown, estados, eventos y cobertura. |

### 💱 FX

| Tarea | Propósito |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Análisis de Par FX | Revisar la dirección del par, rendimientos, volatilidad, evidencia técnica, cobertura y contexto macro fechado. |
| Impacto de Exposición FX | Revisar los vínculos directos de efectivo, moneda de negociación y moneda de valoración con el par. |

Los análisis que comparan trayectorias futuras usan una **Tesis de Escenario**: evidencia
proporcionada, supuestos, horizonte, compensaciones, condiciones de activación, condiciones
de invalidación y decisiones de usuario faltantes. Es obligatoria para los escenarios de
PAC, reequilibrio y compensación de pérdidas fiscales.

## 🧩 Historial Parcial y Datos Adicionales

LibreFolio puede exportar el historial realmente disponible cuando es más corto que el
período de IA solicitado. El prompt muestra las fechas solicitadas/disponibles, la
cobertura, las advertencias y cualquier señal que esté incompleta u omitida. Nunca usa
precios o tasas futuros.

Un Análisis puede recomendar **Datos Adicionales de LibreFolio** cuando otra exportación
mejoraría sustancialmente la respuesta. El prompt proporciona el nombre público de la
exportación, la ruta de IU, el período/detalle recomendado, la razón y si es requerido
u opcional.

!!! info "El Drawdown es siempre sobre todo el historial"

    Dondequiera que aparezca una sección de Drawdown en una exportación, se calcula
    sobre **todo el historial disponible** — desde el primer precio almacenado para
    un Activo, o desde la primera transacción para una Cartera o Bróker — nunca en
    relación con el período de IA seleccionado. Una ventana de exportación corta aún
    contiene el verdadero máximo-mínimo histórico.

## 🔗 Referencias Locales

El prompt usa referencias locales para unir tablas compactas:

- A# para activos;
- B# para brókers;
- F# para pares FX;
- L# para lotes FIFO.

El Directorio de Entidades resuelve las referencias A#, B# y F#. Los lotes L# son
diferentes: son **filas incrustadas** dentro de las tablas FIFO de la propia
exportación, no entradas del directorio — el modelo las lee en su lugar. El modelo
receptor debe usar nombres legibles en su respuesta; no se necesitan IDs de base de datos.

## 🔒 Alcance y Privacidad

- Las exportaciones de cartera siguen el filtro de bróker activo, el rango de fechas
 y la moneda objetivo.
- Las exportaciones de bróker contienen solo el bróker seleccionado y requieren acceso
 a él.
- Las exportaciones de Activo y FX usan la entidad actual, el rango seleccionado, la
 moneda objetivo y el alcance de brókers accesible del usuario cuando se necesita
 contexto de cartera.
- El texto del portapapeles puede contener datos financieros sensibles. Revísalo antes
 de compartirlo o pegarlo en un servicio de terceros.

## ⚠️ Disponibilidad y Seguridad

La Exportación IA falla de forma segura si el navegador y los catálogos del servidor o
los contratos de respuesta no coinciden. Una opción también puede no estar disponible
cuando sus hechos no aplican—por ejemplo, la Revisión de Posición sin una posición
abierta o el Impacto de Exposición FX sin exposición vinculada directa.

La exportación proporciona contexto factual, no asesoramiento de inversión ni
instrucciones de negociación automatizada.

## 🔗 Páginas Relacionadas

- [Exportación IA de cartera](portfolio.md)
- [Exportación IA de bróker](broker.md)
- [Exportación IA de Activo](asset.md)
- [Exportación IA de FX](fx.md)
