# :heart: Apoya a LibreFolio

LibreFolio es un proyecto **open-source**, licenciado bajo AGPL-3.0. El código fuente está disponible gratuitamente y cualquier persona con los conocimientos y la infraestructura necesarios puede instalarlo y ejecutarlo de forma independiente; esa es la belleza del open-source.

Si utilizas LibreFolio y te resulta valioso, nos encantaría contar con tu apoyo, ya sea a través de **código**, **ideas** o una **pequeña donación**. Cada contribución impulsa el crecimiento del proyecto.

---

## :coffee: Invítame a un café

Si LibreFolio te ayuda a gestionar mejor tus inversiones, considera apoyar el desarrollo con un café:

<a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" style="height: 60px !important;width: 217px !important;" ></a>

Cada donación —por pequeña que sea— ayuda a cubrir las herramientas de desarrollo, la infraestructura de pruebas y motiva la mejora continua.

---

## :rocket: Contribuciones de alto impacto

Para nosotros, **una gran idea o una contribución de código es tan valiosa como una donación**. Estas son las áreas donde tu ayuda puede marcar la mayor diferencia:

### :electric_plug: Nuevos Plugins

LibreFolio utiliza un [Sistema de Registro y Plugins](../developer/architecture/patterns/registry_pattern.md) con auto-descubrimiento. Añadir un nuevo plugin es una de las contribuciones más impactantes que puedes realizar:

| Tipo | Guía | Qué hace |
|------|-------|-------------|
| 📥 **BRIM** | [Guía de Plugins BRIM](../developer/architecture/patterns/brim_plugin_guide.md) | Importar transacciones desde un nuevo bróker (CSV/Excel) |
| 📈 **Asset** | [Guía de Plugins de Activos](../developer/architecture/patterns/asset_plugin_guide.md) | Obtener precios de una nueva fuente de datos |
| 💱 **FX** | [Guía de Plugins FX](../developer/architecture/patterns/fx_plugin_guide.md) | Añadir un nuevo proveedor de tipos de cambio |
| 📊 **Señales de gráfico** | *Guía próximamente* | Nuevos indicadores técnicos y superposiciones de gráficos (EMA, MACD, RSI, Bollinger…) |

* **Si no eres desarrollador**: puedes solicitar un nuevo plugin completando nuestro [Formulario de Solicitud de Plugins](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml). Además de los detalles de la solicitud, es necesario que proporciones ejemplos reales y anonimizados (ej. archivos CSV o Excel) del reporte de tu bróker.
* **Si eres desarrollador**: puedes proceder directamente por tu cuenta a implementarlos. Consulta la [Guía del Registry & Plugin System](../developer/architecture/patterns/registry_pattern.md) y las guías específicas enlazadas en la tabla de arriba para aprender cómo crearlos.

### :art: Ideas de UI/UX

Mejoras estéticas, sugerencias de diseño, mejoras de accesibilidad — si ves algo que podría verse o funcionar mejor, ¡cuéntanos abriendo un reporte a través de nuestro [Formulario de Sugerencias de UX/Ideas](https://github.com/Librefolio/LibreFolio/issues/new?template=idea.yml) en GitHub!

### :bug: Reportes de errores

Encontrar y reportar errores de forma clara es increíblemente útil. Abre un nuevo reporte utilizando nuestro [Formulario de Reporte de Errores](https://github.com/Librefolio/LibreFolio/issues/new?template=bug_report.yml) en GitHub.

El formulario te guiará para ingresar la información del navegador, el método de despliegue y los registros de error.

---

## :rocket: Solicitudes de Funciones

Propón funciones específicas con casos de uso claros completando nuestro [Formulario de Solicitud de Feature](https://github.com/Librefolio/LibreFolio/issues/new?template=feature_request.yml) en GitHub.

Cada solicitud será evaluada y asumida tan pronto como haya capacidad para desarrollarla. Las solicitudes bien descritas con ejemplos concretos se priorizan más rápido.

---

## :computer: Contribuye con código

Si eres desarrollador y quieres contribuir directamente:

1. Haz un **Fork** del [repositorio](https://github.com/Librefolio/LibreFolio)
2. **Crea una rama (branch)** para tu función o corrección
3. **Desarrolla y prueba** en tu propio repositorio
4. **Envía un Pull Request** con una descripción clara y el prefijo de palabra clave en el título:

| Palabra clave | Cuándo usarla |
|---------|------------|
| **`[FIX]`** | Correcciones de errores |
| **`[FEAT]`** | Nuevas funciones o mejoras |
| **`[PLUGIN]`** | Nuevo plugin (BRIM, Activo, FX, Señal) |
| **`[DOCS]`** | Mejoras de la documentación |

!!! warning "Merge policy"

    Un PR se fusionará **solo si todas las pruebas existentes sigan pasando**. Si tus cambios requieren actualizaciones de las pruebas, inclúyelas en el PR; esto es perfectamente normal y esperado.

Consulta el [Manual del Desarrollador](../developer/index.md) para obtener detalles sobre la arquitectura, convenciones de codificación y pautas de prueba.

---

## :star: Dale una estrella al proyecto

Una forma sencilla pero poderosa de ayudar: **¡dale una estrella al repositorio** en GitHub! Esto aumenta la visibilidad y ayuda a otros usuarios a descubrir LibreFolio.

[:octicons-star-fill-24: Dar estrella en GitHub](https://github.com/Librefolio/LibreFolio){ .md-button .md-button--primary }

---

## :globe_with_meridians: ¿Qué sigue? — LibreFolio Cloud

Para aquellos que quieran usar LibreFolio pero no tengan el tiempo, los conocimientos o la infraestructura para autoalojarlo, estamos planeando una **plataforma alojada**: **LibreFolio Cloud**. Ofrecerá todas las mismas funciones potentes sin necesidad de configuración técnica, además de próximas **analíticas impulsadas por IA** para ayudarte a tomar decisiones de inversión más inteligentes.

Para mantener la infraestructura, el mantenimiento y el desarrollo continuo, la plataforma en la nube se ofrecerá como un **servicio de suscripción**; el precio se determinará más adelante.

---

!!! tip "¡Gracias!"

    Cada forma de apoyo —código, ideas, reportes de errores o donaciones— es profundamente apreciada. ¡Juntos podemos construir el mejor rastreador de cartera autoalojado! :rocket:
