# ❓ Preguntas Frecuentes (FAQ)

Bienvenido a las FAQ de LibreFolio. Aquí encontrarás respuestas a las preguntas más comunes.

## 💬 Preguntas Generales

### 🤔 ¿Qué es LibreFolio?

LibreFolio es un rastreador de carteras open-source que te ofrece una vista completa y privada de todas tus inversiones. Potentes herramientas de análisis dan vida a tus datos — para que puedas tomar decisiones informadas con plena confianza y pleno control.

### 💰 ¿Es LibreFolio gratuito?

¡Sí! LibreFolio es completamente gratuito y open-source bajo la [licencia AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Puedes instalarlo en tu propio servidor y gestionarlo todo tú mismo sin coste alguno.

!!! info "Próximamente: plataforma en línea ☁️"

    Estamos trabajando en una plataforma en línea para quienes no tienen el tiempo, el interés o los conocimientos técnicos para instalar LibreFolio por su cuenta. La versión alojada ofrecerá todas las funcionalidades sin configuración alguna, con actualizaciones automáticas y soporte dedicado — disponible mediante suscripción.

### 🤖 ¿Hay funciones de IA previstas?

¡Sí! Nuestra hoja de ruta incluye **asistentes basados en inteligencia artificial** para ayudarte a analizar tu cartera, detectar tendencias y tomar decisiones más informadas.

- **Autoalojado**: puedes conectar tus propios modelos de IA y gestionarlo todo de forma independiente
- **Plataforma en línea**: los asistentes de IA estarán totalmente integrados — listos para usar sin configuración alguna, con soporte premium

### 📊 ¿Qué activos puedo rastrear?

LibreFolio es compatible con:

- **Acciones y ETFs** — Precios obtenidos automáticamente a través de proveedores de datos (ej. yfinance)
- **Criptomonedas** — Próximamente
- **Bonos** — Soporte para entrada manual
- **Préstamos P2P** — Activos con rendimiento pactado
- **Efectivo y Depósitos** — Rastrea tu liquidez

!!! tip "¿Falta algo? 💡"

    Si hay alguna clase de activo o funcionalidad que te gustaría ver y que aún no hemos considerado, ¡nos encantaría saberlo! Abre una [solicitud de funcionalidad en GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) y háznoslo saber.

## 🚀 Primeros Pasos

### 📦 ¿Cómo instalo LibreFolio?

Consulta nuestra [Guía de Instalación](developer/dev-installation.md) para obtener instrucciones detalladas.

### 👤 ¿Cómo creo una cuenta?

1. Navega a la página de inicio de sesión
2. Haz clic en "Registrarse"
3. Completa tus datos
4. ¡Tu cuenta ya está lista para usar!

### 🔑 Olvidé mi contraseña, ¿qué hago?

Actualmente, el restablecimiento de la contraseña se realiza a través de la CLI. Contacta con el administrador de tu instancia o ejecuta:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Resolución de Problemas

### 📉 Los precios de mis activos no se actualizan

Comprueba que:

1. La sincronización automática esté activada en la Configuración Global
2. Tus activos tengan ISINs válidos o símbolos reconocidos por el **proveedor de datos** configurado (ej. [yfinance](https://pypi.org/project/yfinance/) para acciones y ETFs)
3. El servicio del proveedor esté disponible (revisa los registros del servidor para buscar errores)

### 💱 Mis tipos de cambio FX no se actualizan

Comprueba que:

1. El par de divisas tenga al menos un [proveedor de datos configurado](user/fx/detail/provider.md)
2. La API del proveedor sea accesible (ECB, FED, BOE, SNB)
3. Hayas ejecutado una [sincronización](user/fx/sync.md) para el rango de fechas deseado
4. Revisa la [cadena de suministro del proveedor](user/fx/detail/provider.md) para ver las opciones de fallback

### 🔐 No puedo iniciar sesión

- Verifica tu nombre de usuario y contraseña
- Comprueba si tu cuenta está activada
- Borra las cookies del navegador e inténtalo de nuevo

## 🆘 ¿Necesitas más ayuda?

- [Documentación Completa](index.md)
- [Informar de un Error](https://github.com/Alfystar/LibreFolio/issues)
- [Discusiones de GitHub](https://github.com/Alfystar/LibreFolio/discussions)
