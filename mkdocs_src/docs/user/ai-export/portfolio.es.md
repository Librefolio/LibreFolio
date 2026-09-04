# 🧠 Exportación de IA de Cartera

Exportación de IA de Cartera prepara una instantánea del portapapeles con alcance al panel de control o un
prompt de análisis enfocado. LibreFolio nunca envía la exportación a un servicio de IA.

## 📍 Ubicación

Abra **panel de control** y seleccione **Exportación de IA** en la barra de herramientas superior, junto a
**Actualizar/Sincronizar**. El borrador permanece disponible durante 10 minutos en la sesión actual
y se restablece después de cerrar sesión o iniciar una nueva sesión.

## 🎯 Análisis de cartera

| Tarea | Enfoque |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Plan de Inversión Recurrente** | Estructura de la cartera, flujos de efectivo, restricciones y contexto de inversión recurrente. |
| **Reequilibrio de Cartera** | Asignación actual, concentración, diversificación y contexto de asignación objetivo. |
| **Rendimiento de Cartera y Factores de Mercado** | Conciliación de rendimiento más investigación fechada de horizonte corto y largo para cada activo mantenido. |
| **Estrategias de Compensación de Pérdidas de Capital** | Formas condicionales de utilizar pérdidas fiscales disponibles o próximas a vencer contra ganancias potencialmente elegibles, utilizando evidencia económica FIFO y el inventario oficial de pérdidas fiscales del usuario. |

## 🗂️ Alcance y datos

La exportación sigue el filtro de bróker activo, el rango de fechas y la moneda objetivo.
Según la selección, puede incluir totales de cartera, efectivo, posiciones,
asignaciones, rendimiento, contribuciones, ingresos, contexto de calidad de datos y
resultados técnicos calculados por el backend.

El prompt distingue:

- Brókers incluidos en el alcance del cálculo;
- Brókers con posiciones abiertas actuales;
- Brókers con contribución al rendimiento en el período de IA.

Un bróker incluido en el alcance puede no tener posición actual. Las referencias B# siguen siendo consistentes con el
Directorio de Entidades.

!!! note "El FIFO económico no es un tratamiento fiscal legal"

    La exportación general contiene un resumen FIFO económico compacto por activo.
    **Estrategias de Compensación de Pérdidas de Capital** recibe, además, cada lote aplicable.
    Antes de comparar rutas de no acción, de realización de ganancias, escalonadas o de recolección de pérdidas,
    el prompt solicita residencia fiscal, régimen, tipo de cuenta, inventario oficial de pérdidas fiscales
    (por ejemplo, el `cassetto fiscale` italiano), categoría legal,
    montos restantes y utilizados, fechas de origen/vencimiento, reglas de compensación y restricciones.

## 📤 Datos de Exportación y Análisis de Solicitud

- **Exportar Datos** copia un conjunto de datos factual de cartera sin
 instrucciones de análisis ni contrato de respuesta.
- **Solicitar Análisis** añade instrucciones específicas de la tarea, un contrato de respuesta y
 los conjuntos de datos declarados para el Análisis seleccionado.
 El idioma de respuesta solicitado sigue siempre el idioma actual de la interfaz de
 LibreFolio.
- Las notas opcionales se incluyen solo para los análisis que las admiten.

Hay dos exportaciones de datos públicas disponibles:

- **Descripción general e historial de cartera** — posiciones, efectivo, asignaciones, concentración,
 trayectoria de rendimiento, flujos, ingresos, costos, conciliación, resumen FIFO económico,
 historial compacto por activo, Drawdown, cobertura y procedencia;
- **Historial de activos de cartera** — buckets de precios de cierre observados más densos, indicadores,
 estados, eventos, cobertura y amplitud para el universo de activos elegibles.

## 📅 Plan de Inversión Recurrente

El Análisis utiliza primero los hechos proporcionados y solo solicita las preferencias faltantes que
cambian materialmente el plan. Las preguntas se agrupan en:

- frecuencia del capital y de las contribuciones;
- objetivos y horizonte;
- preferencias de riesgo, incluida la volatilidad aceptable o el Drawdown temporal;
- restricciones operativas como liquidez, brókers, órdenes mínimas, exclusiones,
 o si se permiten ventas.

El prompt distingue las respuestas indispensables de los refinamientos opcionales y puede
seguir ofreciendo escenarios condicionales. Nunca inventa presupuesto, objetivos ni
tolerancia al riesgo.

Compara el despliegue inmediato y el escalonado. La espera condicional aparece solo
cuando existe evidencia de declive amplia y persistente en toda la cartera, nunca
de un solo activo o un solo indicador.

El Drawdown de la cartera y una comparación compacta de Drawdown por activo son solo contexto
histórico. No son pronósticos ni señales de compra independientes, y no se añade ningún historial
de Drawdown de activos.

## 📰 Rendimiento y Factores de Mercado

Se instruye a la IA receptora a cubrir cada activo mantenido, citar fuentes fechadas,
evaluar la calidad de las fuentes, proporcionar tesis de horizonte corto y largo, distinguir
cronología/correlación de causalidad y etiquetar los enlaces como respaldados, plausibles,
inferidos, especulativos o inexplicados.

## 📏 Detalle y Muestreo

| Detalle | Muestreo exacto |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Compacto** | Exportación general: 8 puntos de trayectoria de cartera y hasta 6 puntos por activo elegible. Exportación detallada: hasta 5 filas de indicadores no vacías por activo/señal. |
| **Estándar** | Exportación general: 16 puntos de trayectoria de cartera y hasta 12 puntos por activo elegible. Exportación detallada: hasta 10 filas de indicadores. |
| **Completo** | Exportación general: 30 puntos de trayectoria de cartera y hasta 24 puntos por activo elegible. Exportación detallada: cada bucket de indicadores no vacío; esto puede ser muy grande. |

Un conjunto de datos o Análisis puede omitir secciones opcionales no disponibles o no aplicables.
El **período de IA** utiliza 3M, 6M, 1Y o Personalizado cuando se ofrece y siempre termina en la
fecha de la instantánea. Las filas temporales completamente vacías se omiten, mientras que los metadatos
de período/cobertura y los valores cero observados permanecen.

## 🔒 Aplicabilidad, Errores y Privacidad

Las tareas u opciones de detalle no disponibles permanecen deshabilitadas. La Exportación de IA también falla en estado cerrado
cuando los catálogos de navegador y servidor o los contratos de respuesta no coinciden. Los errores
tipados explican la aplicabilidad faltante, entidades inaccesibles, fallos de fuente,
o problemas de contrato sin exponer detalles internos.

El portapapeles puede contener datos financieros sensibles. Revíselo antes de pegarlo
en un servicio de terceros. Consulte la [Descripción general de Exportación de IA](index.md)
para conocer el flujo de trabajo entre dominios y el modelo de seguridad.
