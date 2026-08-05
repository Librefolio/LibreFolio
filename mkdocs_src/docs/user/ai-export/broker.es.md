# 🧠 Exportación AI del Bróker

La exportación AI del Bróker prepara una instantánea del portapapeles o un prompt
de análisis limitados a un bróker accesible. LibreFolio nunca la envía a un
servicio de AI.

## 📍 Ubicación

Abra la página de detalle de un bróker y seleccione **Exportación AI** en la
barra de herramientas superior. El borrador permanece disponible durante 10
minutos en la sesión actual y se restablece después de cerrar sesión o de
iniciar una nueva sesión.

## 🎯 Análisis del Bróker

| Tarea | Enfoque |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Revisión del Bróker** | Posiciones, efectivo, actividad, rendimiento y cobertura de datos. |
| **Rendimiento del Bróker y Factores de Mercado** | Conciliación de rendimiento más investigación fechada para cada activo mantenido a través del bróker. |
| **Estrategias de Compensación de Pérdidas de Capital** | Formas condicionales de utilizar pérdidas fiscales disponibles o que expiran contra plusvalías potencialmente elegibles utilizando evidencia económica FIFO del bróker seleccionado. |

## 🗂️ Alcance y Datos

La exportación se limita al bróker seleccionado, al rango de fechas actual y a la
moneda objetivo. Según la selección, puede incluir saldos de efectivo,
posiciones, transacciones, rendimiento, costos, asignación, concentración,
ingresos y resúmenes de lotes FIFO. Las comprobaciones de acceso del lado del
servidor evitan exportar un bróker que el usuario actual no puede leer.

!!! important "Los costos asignados y no asignados se mantienen diferenciados"

    Las filas FIFO contienen solo comisiones e impuestos asignados de forma
    determinista a los lotes. Los costos no asignados a nivel de bróker
    permanecen en la evidencia financiera general y nunca se presentan como
    costos de lote cero.

## 📤 Exportar Datos y Solicitar Análisis

- **Exportar Datos** copia solo un conjunto de datos fáctico del bróker.
- **Solicitar Análisis** agrega instrucciones específicas de la tarea, un
 contrato de respuesta y los conjuntos de datos declarados para el análisis.
 El idioma de respuesta solicitado se ajusta al idioma actual de la interfaz
 de LibreFolio.
- Las notas opcionales se incluyen solo cuando el análisis seleccionado las
 admite.

Hay dos exportaciones de datos públicas disponibles:

- **Descripción general e Historial del Bróker** — posiciones del bróker seleccionado,
 efectivo, concentración, trayectoria de rendimiento, flujos, costos, ratios,
 resumen económico FIFO, historial compacto por activo, Drawdown, cobertura y
 procedencia;
- **Historial de Activos del Bróker** — cubos de precios de cierre observados
 acotados al bróker, indicadores, estados, eventos, amplitud y razones
 explícitas de los activos actuales excluidos de la elegibilidad técnica.

## 🧾 Estrategias de Compensación de Pérdidas de Capital

El prompt utiliza lotes económicos FIFO del bróker seleccionado para identificar
candidatos condicionales de plusvalías y minusvalías, pero nunca los trata
automáticamente como legalmente elegibles. Primero solicita la residencia
fiscal, el régimen, el tipo de cuenta, el inventario oficial de pérdidas
fiscales, los importes por categoría legal, las fechas de origen y vencimiento,
los saldos ya utilizados, las reglas de compensación y si los saldos entre
brókers/cuentas pueden combinarse.

Luego puede comparar la no acción, la realización de plusvalías elegibles antes
del vencimiento, la realización escalonada alineada con el rebalanceo y la
cosecha de pérdidas cuando sea relevante. Cada vía muestra costos, cambios de
exposición, liquidez, concentración, momento e incertidumbre legal; no se
recomienda ninguna operación únicamente por razones fiscales.

## 📏 Detalle y Muestreo

| Detalle | Muestreo exacto |
| ------------- | ---------------------------------------------------------------------------------- |
| **Compacto** | El mismo universo de datos con los cubos temporales soportados más dispersos (hasta 30 días). |
| **Estándar** | El mismo universo de datos con cubos temporales de hasta 14 días. |
| **Completo** | El mismo universo de datos con cubos temporales de hasta 7 días. |

La exportación general utiliza 8/16/30 puntos de trayectoria del bróker y hasta
6/12/24 puntos de historial compacto por activo elegible. La exportación
detallada mantiene la política completa de muestreo técnico y puede ser extensa.

Un conjunto de datos o un análisis puede omitir secciones opcionales no disponibles
o no aplicables. El **período de AI** termina en la fecha de la instantánea. El
historial parcial y la cobertura se mantienen explícitos.

## 🔒 Aplicabilidad, Errores y Privacidad

Los análisis pueden no estar disponibles cuando los hechos requeridos no
existen. Las opciones también fallan en modo cerrado ante una discrepancia de
catálogo o contrato. Los errores específicos informan de problemas de acceso,
aplicabilidad, fuente o contrato.

El portapapeles puede contener datos sensibles de cuentas y transacciones.
Revíselo antes de compartirlo. Consulte la [descripción general de Exportación AI](index.md)
para conocer el flujo de trabajo entre dominios y el modelo de seguridad.
