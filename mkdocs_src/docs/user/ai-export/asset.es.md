# 🧠 Exportación IA de Activos

La Exportación IA de Detalle de Activo prepara una instantánea del portapapeles o un prompt de análisis enfocado
para el activo actualmente abierto. LibreFolio nunca lo envía a un servicio de IA.

## 📍 Ubicación

Abra una página de detalle de Activo. En el encabezado **Señales**, seleccione **Exportación IA**. Su
borrador permanece disponible durante 10 minutos en la sesión actual y se restablece
tras cerrar sesión o iniciar una nueva.

## 🎯 Análisis de Activos

| Tarea | Enfoque |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Revisión de Posición** | Tamaño de la posición, base de costo, rendimiento, ingresos y concentración. |
| **Análisis de Mercado del Activo** | Historial de cierres observados, rendimientos, tendencia, impulso, volatilidad, Drawdown, estados, eventos y cobertura. |

## 🗂️ Alcance y Datos

La exportación utiliza el activo actual, el rango de fechas seleccionado, la moneda de visualización/objetivo
y el alcance del bróker accesible del usuario cuando se requiere contexto de cartera.
Según la selección, puede incluir identificadores, precios, rendimientos, valoración,
hechos de posición y FIFO, ingresos, eventos corporativos y resultados técnicos calculados
por el backend. El navegador no recalcula indicadores.

## 📤 Exportación de Datos y Solicitud de Análisis

- **Exportar Datos** copia un conjunto de datos fáctico seleccionado de activos sin instrucciones
 de análisis ni interpretación.
- **Solicitar Análisis** utiliza hechos relevantes y añade instrucciones específicas de la tarea
 más un contrato de respuesta para que la IA receptora pueda interpretarlos. El idioma
 de respuesta solicitado sigue el idioma actual de la interfaz de LibreFolio.
- Las notas opcionales se incluyen solo cuando el Análisis seleccionado las admite.

Dos exportaciones de datos públicas están disponibles:

- **Posición e Historial del Activo** — posiciones por Bróker, costo, valor, P&L,
 semántica del período registrado en cero, lotes económicos con comisiones/impuestos asignados, historial
 de mercado compacto, Drawdown y procedencia;
- **Historial de Mercado del Activo** — segmentos de cierre observados, rendimientos, indicadores, estados,
 eventos, Drawdown y cobertura.

## 📏 Detalle y Muestreo

| Detalle | Muestreo exacto |
| ------------ | --------------------------------------------------------------------------------------------------------------------- |
| **Compacto** | Exportación de posición: hasta 8 puntos uniformes de historial observado. Exportación de mercado: hasta 5 filas de indicadores no vacías por Señal. |
| **Estándar** | Exportación de posición: hasta 16 puntos. Exportación de mercado: hasta 10 filas de indicadores. |
| **Completo** | Exportación de posición: hasta 30 puntos. Exportación de mercado: cada segmento de indicador no vacío y puede llegar a ser grande. |

Un conjunto de datos o Análisis puede omitir secciones opcionales no disponibles o no aplicables.
El **período de IA** finaliza en la fecha de la instantánea. Las fechas disponibles, la cobertura, la Señal
parcial y las razones de omisión siguen siendo explícitas.

## 🔒 Aplicabilidad, Errores y Privacidad

La Revisión de Posición requiere contexto de posición. Otras tareas pueden deshabilitarse cuando
faltan hechos necesarios. Los desajustes de catálogo y de contrato de respuesta fallan en modo cerrado.
Los errores tipificados informan aplicabilidad, entidades faltantes, fallos de fuente o
problemas de contrato.

El portapapeles puede contener datos sensibles de posiciones y rendimiento. Revíselo
antes de compartirlo. Consulte la [descripción general de Exportación IA](index.md) para
el flujo de trabajo entre dominios y el modelo de seguridad.
