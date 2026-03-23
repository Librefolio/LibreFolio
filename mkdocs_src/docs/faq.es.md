# ❓ Preguntas Frecuentes (FAQ)

¡Bienvenido/a al FAQ de LibreFolio! Aquí encontrarás respuestas a preguntas comunes.

## 💬 Preguntas Generales

### 🤔 ¿Qué es LibreFolio?

LibreFolio es un rastreador de carteras **autohospedado** y de código abierto diseñado para inversores preocupados por la privacidad. Te permite **seguir** tus inversiones, analizar su rendimiento y mantener el control total de tus datos financieros.

### 💰 ¿Es LibreFolio gratuito?

¡Sí! LibreFolio es completamente gratuito y de código abierto bajo la licencia [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html).

### 📊 ¿Qué activos puedo seguir?

LibreFolio es compatible con:

- **Acciones y ETFs** - Precios obtenidos automáticamente de yfinance
- **Criptomonedas** - Próximamente
- **Bonos** - Permite entrada manual
- **Préstamos P2P** - Activos con rendimientos periódicos
- **Efectivo y Depósitos** — Sigue tu liquidez

!!! tip "¿Falta algo? 💡"

    Si hay un tipo de activo o una función que te gustaría ver y en la que no hemos pensado, ¡nos encantaría saberlo! Abre una [solicitud de mejora en GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement).

## 🚀 Primeros Pasos

### 📦 ¿Cómo instalo LibreFolio?

Consulta nuestra [Guía de Instalación](developer/dev-installation.md) para instrucciones detalladas.

### 👤 ¿Cómo creo una cuenta?

1. Ve a la página de inicio de sesión
2. Haz clic en "Registrarse"
3. Completa tus datos
4. ¡Tu cuenta está lista para usar!

### 🔑 He olvidado mi contraseña, ¿qué hago?

Actualmente, el restablecimiento de contraseña se realiza mediante la CLI. Contacta al administrador de tu instancia o ejecuta:

```bash
./dev.py user reset <usuario> <nueva_contraseña>
```

## 🔧 Solución de Problemas

### 📉 Los precios de mis activos no se actualizan

Verifica que:

1. La sincronización automática esté activada en la configuración global
2. Tus activos tengan ISINs o símbolos válidos reconocidos por el **proveedor de datos** configurado (ej. [yfinance](https://pypi.org/project/yfinance/) para acciones y ETFs)
3. El servicio del proveedor esté disponible (revisa los registros del servidor)

### 💱 Mis tipos de cambio no se actualizan

Verifica que:

1. El par de divisas tenga al menos un [proveedor de datos configurado](user/fx/detail/provider.md)
2. La API del proveedor sea accesible (BCE, FED, BOE, SNB)
3. Hayas ejecutado una [sincronización](user/fx/sync.md) para el rango de fechas deseado

### 🔐 No puedo iniciar sesión

- Verifica tu nombre de usuario y contraseña
- Comprueba si tu cuenta está activada
- Borra las cookies del navegador e inténtalo de nuevo

## 🆘 ¿Necesitas más ayuda?

- [Documentación completa](index.md)
- [Reportar un error](https://github.com/Alfystar/LibreFolio/issues)
- [Debates en GitHub](https://github.com/Alfystar/LibreFolio/discussions)

---
