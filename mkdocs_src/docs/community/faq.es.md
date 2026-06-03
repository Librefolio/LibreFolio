# ❓ Preguntas Frecuentes (FAQ)

Bienvenido a las FAQ de LibreFolio. Aquí encontrarás respuestas a las preguntas más comunes.

## 💬 Preguntas Generales

### 🤔 ¿Qué es LibreFolio?

LibreFolio es un rastreador de carteras open-source que te ofrece una vista completa y privada de todas tus inversiones. Potentes herramientas de análisis convierten tus datos en información procesable, para que puedas tomar decisiones informadas con total confianza y control absoluto.

### 💰 ¿Es LibreFolio gratuito?

¡Sí! LibreFolio es completamente gratuito y open-source bajo la [licencia AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Puedes instalarlo en tu propio servidor y gestionarlo todo tú mismo sin coste alguno.

!!! info "Próximamente: plataforma alojada ☁️"

    Estamos trabajando en una plataforma online para aquellos que no disponen de tiempo, interés o conocimientos técnicos para el autoalojamiento. La versión alojada ofrecerá todas las funciones sin necesidad de configuración, actualizaciones automáticas y soporte dedicado, disponible mediante una suscripción de pago.

### 🤖 ¿Hay funciones de IA planificadas?

¡Sí! Nuestra hoja de ruta incluye **asistentes impulsados por IA** para ayudarte a analizar tu cartera, detectar tendencias y tomar decisiones mejor informadas.

- **Autoalojado**: puedes conectar tus propios modelos de IA y gestionar todo de forma independiente.
- **Plataforma alojada**: los asistentes de IA estarán totalmente integrados, listos para usar sin requerir configuración, junto con soporte premium.

### 📊 ¿Qué activos puedo rastrear?

LibreFolio soporta:

- **Acciones y ETFs** — Precios obtenidos automáticamente a través de proveedores de datos (ej. yfinance).
- **Criptomonedas** — Próximamente.
- **Bonos** — Se admite la entrada manual.
- **Préstamos P2P** — Activos con rendimiento programado.
- **Efectivo y Depósitos** — Rastrea tu liquidez.

!!! tip "¿Falta algo? 💡"

    Si hay alguna clase de activo o función que te gustaría ver y en la que aún no hemos pensado, ¡nos encantaría saberlo! Abre una [solicitud de función en GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) y cuéntanos.

## 🚀 Primeros Pasos

### 📦 ¿Cómo instalo LibreFolio?

Consulta nuestra [Guía de Instalación](../developer/dev-installation.md) para obtener instrucciones detalladas.

### 👤 ¿Cómo creo una cuenta?

1. Ve a la página de inicio de sesión.
2. Haz clic en "Registrarse".
3. Rellena tus datos.
4. ¡Tu cuenta ya está lista para usar!

### 🔑 He olvidado mi contraseña, ¿qué hago?

Actualmente, el restablecimiento de contraseñas se realiza a través de la CLI. Contacta con el administrador de tu instancia o ejecuta:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Solución de Problemas

### 📉 Los precios de mis activos no se actualizan

Comprueba que:

1. La sincronización automática esté activada en la Configuración Global.
2. Tus activos tengan ISINs válidos o símbolos reconocidos por el **proveedor de datos** configurado (ej. [yfinance](https://pypi.org/project/yfinance/) para acciones y ETFs).
3. El servicio del proveedor esté disponible (revisa los logs del servidor para buscar errores).

### 💱 Mis tipos de cambio FX no se actualizan

Comprueba que:

1. El par de divisas tenga al menos un [proveedor de datos configurado](../user/fx/detail/provider.md).
2. La API del proveedor sea accesible (ECB, FED, BOE, SNB).
3. Hayas ejecutado una [sincronización](../user/fx/sync.md) para el rango de fechas deseado.
4. Revisa la [cadena de suministro del proveedor](../user/fx/detail/provider.md) para ver las opciones de fallback.

### 🔐 No puedo iniciar sesión

- Verifica tu nombre de usuario y contraseña.
- Comprueba si tu cuenta está activada.
- Borra las cookies del navegador e inténtalo de nuevo.

### 📱 ¿Puedo usar LibreFolio como aplicación móvil?

¡Sí! LibreFolio soporta la instalación como **PWA (Progressive Web App)**. Puedes añadirlo a tu pantalla de inicio en Android, iOS o escritorio para obtener una experiencia de pantalla completa similar a una aplicación, sin necesidad de tienda de aplicaciones.

Consulta la guía [Instalar como App (PWA)](../user/pwa.md) para obtener instrucciones paso a paso.

## 🆘 ¿Necesitas más ayuda?

- [Documentación Completa](../index.md)
- [Informar de un Error](https://github.com/Alfystar/LibreFolio/issues)
- [Discusiones de GitHub](https://github.com/Alfystar/LibreFolio/discussions)
