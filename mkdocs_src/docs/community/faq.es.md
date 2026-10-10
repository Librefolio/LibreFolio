# ❓ Preguntas frecuentes (FAQ)

Bienvenido a las preguntas frecuentes de LibreFolio. Aquí encontrarás respuestas a preguntas comunes.

## 💬 Preguntas generales

### 🤔 ¿Qué es LibreFolio?

LibreFolio es un rastreador de carteras de código abierto que te ofrece una visión completa y privada de todas tus inversiones. Potentes herramientas de análisis convierten tus datos en información práctica — para que puedas tomar decisiones informadas con total confianza y control absoluto.

### 💰 ¿LibreFolio es gratis?

¡Sí! LibreFolio es completamente gratis y de código abierto bajo la [licencia AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Puedes instalarlo en tu propio servidor y gestionarlo todo tú mismo sin coste alguno.

!!! info "Próximamente: plataforma alojada ☁️"

    Estamos trabajando en una plataforma en línea para quienes no tienen el tiempo, el interés o las habilidades técnicas para autoalojarla. La versión alojada ofrecerá todas las funciones sin necesidad de configuración, actualizaciones automáticas y soporte dedicado — disponible como suscripción de pago.

### 🤖 ¿Puedo usar LibreFolio con un asistente de IA?

Sí. **[Exportación IA](../user/ai-export/index.md)** copia tus datos como texto listo para pegar, con una pregunta específica si lo deseas, para que puedas preguntar al asistente de IA que elijas sobre tu cartera, un bróker, un activo o un par FX. LibreFolio en sí nunca contacta con un servicio de IA.

En la próxima plataforma alojada, los asistentes de IA estarán totalmente integrados: listos para usar sin configuración, junto con soporte premium.

### 📊 ¿Qué activos puedo seguir?

LibreFolio admite:

- **Acciones, ETF y fondos** — precios obtenidos automáticamente de proveedores de datos (p. ej., yfinance)
- **Bonos** — precios de un proveedor, o introducidos manualmente
- **Criptoactivos** — se rastrean como activos de la cartera, no como divisas
- **Crowdfunding y préstamos P2P** — valorados con un rendimiento programado
- **Materias primas, bienes inmuebles** y activos sin precio de mercado (arte, coleccionables, acciones no cotizadas)
- **Efectivo** — el saldo de cada bróker, en cada divisa

La lista completa está en [Tipos de activos](../financial-theory/instruments/asset-types/index.md).

!!! tip "¿Falta algo? 💡"

    Si hay una clase de activo o una función que te gustaría ver y que aún no se nos ha ocurrido, ¡nos encantaría saber de ti! Abre una [solicitud de función en GitHub](https://github.com/Librefolio/LibreFolio/issues/new?labels=enhancement) y cuéntanoslo.

## 🚀 Primeros pasos

### 📦 ¿Cómo instalo LibreFolio?

Sigue la [Guía de instalación con Docker](../user/installation.md), la forma recomendada, o la [Guía de instalación en host](../admin/host_installation.md) para ejecutarlo con Pipenv.

### 👤 ¿Cómo creo una cuenta?

1. Abre la página de inicio de sesión.
2. Haz clic en **Regístrate aquí**, junto a *¿No tienes una cuenta?*
3. Rellena tus datos: tu cuenta está lista para usar.

En una instancia nueva, la primera cuenta creada se convierte en administrador. Después de eso, el registro solo funciona mientras el administrador mantenga **Habilitar registro** activado en la [Configuración global](../admin/settings.md); de lo contrario, pídele una cuenta.

### 🔑 Olvidé mi contraseña, ¿qué hago?

La recuperación por correo electrónico aún no está disponible: pídele a tu administrador de instancia que establezca una nueva contraseña desde la línea de comandos ([Restablecer una contraseña](../admin/cli_tools.md#reset-a-password-or-lock-an-account)).

## 🔧 Solución de problemas

### 📉 Los precios de mis activos no se actualizan

Comprueba que:

1. **Planificador habilitado** esté activado en la [Configuración global](../admin/settings.md#market-data-scheduler): ejecuta las actualizaciones automáticas
2. Tus activos tengan ISIN o símbolos válidos reconocidos por el **proveedor de datos** configurado (p. ej., [yfinance](https://pypi.org/project/yfinance/) para acciones y ETF)
3. El servicio del proveedor esté disponible (revisa los registros del servidor en busca de errores)

### 💱 Mis tipos de cambio no se actualizan

Comprueba que:

1. **Planificador habilitado** esté activado en la [Configuración global](../admin/settings.md#market-data-scheduler)
2. El par FX tenga al menos un [proveedor de datos configurado](../user/fx/detail/provider.md)
3. La API del proveedor sea accesible (ECB, FED, BOE, SNB)
4. Hayas ejecutado una [sincronización](../user/fx/sync.md) para el rango de fechas deseado
5. Consulta la [cadena de suministro del proveedor](../user/fx/detail/provider.md) para opciones de fallback

### 🔐 No puedo iniciar sesión

- Verifica tu nombre de usuario y contraseña
- Con una contraseña incorrecta siempre obtienes el mismo mensaje *Usuario o contraseña no válidos*, exista o no la cuenta; con la contraseña correcta, si la cuenta está deshabilitada se te informa de ello: pide a tu administrador que la vuelva a habilitar
- Borra las cookies del navegador e inténtalo de nuevo

### 📱 ¿Puedo usar LibreFolio como aplicación móvil?

¡Sí! LibreFolio admite la instalación como **PWA (Progressive Web App)**. Puedes añadirlo a tu pantalla de inicio en Android, iOS o escritorio para obtener una experiencia a pantalla completa similar a una aplicación — sin necesidad de tienda de aplicaciones.

Consulta la guía [Instalar como aplicación (PWA)](../user/pwa.md) para obtener instrucciones paso a paso.

## 🆘 ¿Necesitas más ayuda?

- [Documentación completa](../index.md)
- [Informar de un error](https://github.com/Librefolio/LibreFolio/issues)
- [Debates de GitHub](https://github.com/Librefolio/LibreFolio/discussions)
