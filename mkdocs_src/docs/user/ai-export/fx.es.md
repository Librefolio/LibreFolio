# 🧠 Exportación AI de FX

La Exportación AI de detalle de FX prepara una instantánea del portapapeles o un prompt
de análisis enfocado para el par de divisas canónico actualmente abierto. LibreFolio nunca
lo envía a un servicio de AI.

## 📍 Ubicación

Abre una página de detalle de FX. En el encabezado **Señales**, selecciona **Exportación AI**. Tu
borrador permanece disponible durante 10 minutos en la sesión actual y se restablece
después de cerrar sesión o de un nuevo inicio de sesión.

## 🎯 Análisis de FX

| Tarea | Enfoque |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| **Análisis de par FX** | Dirección del par, rentabilidades, volatilidad, evidencia técnica, cobertura y contexto macro fechado. |
| **Impacto de exposición FX** | Vínculos directos del efectivo, la divisa de negociación y la divisa de valoración con el par. |

## 🗂️ Alcance y datos

La exportación utiliza el par canónico de la página, el rango de fechas seleccionado, la divisa objetivo,
el historial de tipos de cambio, el contexto del proveedor y los resultados técnicos calculados por el backend.

## 📤 Datos de exportación y solicitud de análisis

- **Exportar datos** copia solo un conjunto de datos FX basado en hechos.
- **Solicitar análisis** añade instrucciones específicas de la tarea, un contrato de respuesta y
 los conjuntos de datos declarados para el análisis.
 El idioma de respuesta solicitado sigue el idioma actual de la interfaz de
 LibreFolio.
- Las notas opcionales se incluyen solo cuando el análisis seleccionado las admite.

Hay dos exportaciones de datos públicas disponibles:

- **Mercado de FX y exposición** — tipo de cambio actual de cotización por base, 8/16/30 puntos
 de trayectoria observados, tendencia/impulso/volatilidad enfocados, rentabilidades a 30 y 91 días,
 posición en el rango, cobertura de fuentes, entradas de usuario faltantes y exposición directa;
- **Historial del mercado de FX** — grupos de tipos de cambio más densos, rentabilidades, indicadores,
 estados, eventos y cobertura.

## 📉 Historial parcial

Cuando el período de AI solicitado comienza antes del historial de tipos de cambio almacenado,
LibreFolio exporta el historial real que puede utilizar e informa de:

- fechas solicitadas y disponibles;
- cobertura;
- recuentos observados y rellenados hacia atrás;
- señal parcial;
- señal omitida y motivos;
- advertencias de historial insuficiente.

No se utiliza ningún tipo de cambio futuro. Una señal parcial no se presenta como equivalente
a un historial completo.

## 📏 Detalle y muestreo

| Detalle | Muestreo exacto |
| ------------- | --------------------------------------------------------------------------------------------------------------- |
| **Compacto** | Exportación general: hasta 8 puntos de tipo de cambio observados uniformemente. Exportación detallada: hasta 5 filas de indicador no vacías por señal. |
| **Estándar** | Exportación general: hasta 16 puntos. Exportación detallada: hasta 10 filas de indicador. |
| **Completo** | Exportación general: hasta 30 puntos. Exportación detallada: todos los grupos de indicador no vacíos; puede ser extensa. |

Un conjunto de datos o un análisis puede omitir secciones opcionales no disponibles o no aplicables.
El **período de AI** finaliza en la fecha de la instantánea.

## 🔒 Aplicabilidad, errores y privacidad

Los análisis o las opciones de detalle pueden desactivarse cuando faltan los datos necesarios.
Los desajustes entre el catálogo y el contrato de respuesta se rechazan en modo cerrado (fail closed).
Los errores tipificados informan de problemas de aplicabilidad, fuente, entidad o contrato.

El portapapeles puede contener datos sensibles de exposición a divisas y de cartera.
Revísalo antes de compartirlo. Consulta la [descripción general de Exportación AI](index.md)
para conocer el flujo de trabajo entre dominios y el modelo de seguridad.
