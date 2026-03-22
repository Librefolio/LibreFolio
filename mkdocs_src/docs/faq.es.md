# ❓ Preguntas Frecuentes (FAQ)

¡Bienvenido/a al FAQ de LibreFolio! Aquí encontrarás respuestas a preguntas comunes.

## 💬 Preguntas Generales

### 🤔 ¿Qué es LibreFolio?

LibreFolio es un rastreador de carteras **autohospedado** y de código abierto diseñado para inversores preocupados por la privacidad. Te permite **seguir** tus inversiones, analizar su rendimiento y mantener el control total de tus datos financieros.

### 💰 ¿Es LibreFolio gratuito?

¡Sí! LibreFolio es completamente gratuito y de código abierto bajo la licencia MIT.

### 📊 ¿Qué activos puedo seguir?

LibreFolio es compatible con:

- **Acciones y ETFs** - Precios obtenidos automáticamente de yfinance
- **Criptomonedas** - Próximamente
- **Bonos** - Permite entrada manual
- **Préstamos P2P** - Activos con rendimientos periódicos
- **Efectivo y Depósitos** - Sigue tu liquidez

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

### 📉 Mis precios no se actualizan

Verifica que:

1. La sincronización automática esté activada en **configuración global**
2. Tus activos tengan ISINs o símbolos válidos
3. El proveedor yfinance esté funcionando (revisa los registros)

### 🔐 No puedo iniciar sesión

- Verifica tu nombre de usuario y contraseña
- Comprueba si tu cuenta está activada
- Borra las cookies del navegador e inténtalo de nuevo

## 🆘 ¿Necesitas más ayuda?

- [Documentación completa](index.md)
- [Reportar un error](https://github.com/Alfystar/LibreFolio/issues)
- [Debates en GitHub](https://github.com/Alfystar/LibreFolio/discussions)

---
