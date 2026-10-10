# 📱 Instalar como aplicación (PWA)

LibreFolio se puede instalar como una **aplicación web progresiva (PWA)** en tu teléfono, tableta u ordenador:
se abre como una aplicación nativa, desde su propio icono, sin necesidad de una tienda de aplicaciones.

---

## ✅ Lo que obtienes

- 🖥️ **Pantalla completa** — sin barra de direcciones ni barra de herramientas del navegador.
- 🏠 **Icono en la pantalla de inicio** — inicia LibreFolio como cualquier otra aplicación.
- 👆 **Sin gestos accidentales** — el gesto de deslizar hacia atrás y el zoom con doble toque están desactivados.
- 🔐 **Mantén la sesión iniciada** entre aperturas, hasta que tu sesión caduque.

!!! note "Solo en línea"

    La aplicación necesita conexión con tu servidor de LibreFolio: no hay modo sin conexión — tus datos
    residen en tu servidor. Si abres la aplicación cuando no se puede alcanzar el servidor, aparece una
    página **Servidor inaccesible** y vuelve a intentarlo por sí sola.

---

## 📲 Cómo instalar

### 🤖 Android (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge.
2. Abre el menú **Ayuda y soporte** (❓, arriba a la derecha) y toca **Instalar aplicación**.
3. Confirma con **Instalar**: LibreFolio aparece en tu pantalla de inicio.

¿No aparece el diálogo de instalación? Usa el menú **⋮** del navegador → **Instalar aplicación** o **Añadir a pantalla de inicio**.

### 🍎 iOS (Safari)

1. Abre LibreFolio en **Safari**.
2. Toca el botón **Compartir** (cuadrado con flecha).
3. Desplázate hacia abajo, toca **Añadir a pantalla de inicio** y luego **Añadir**.

iOS no tiene diálogo de instalación: en un iPhone o iPad, **Instalar aplicación** en el menú Ayuda y soporte muestra estas instrucciones en su lugar.

### 💻 Escritorio (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge.
2. Haz clic en **Instalar aplicación** en el menú **Ayuda y soporte**, o en el icono de instalación (⊕) de la barra de direcciones.
3. LibreFolio se abre en su propia ventana.

---

## 🌐 HTTP vs HTTPS

| Dirección | Instalar como aplicación | Diálogo de instalación desde **Instalar aplicación** |
|---|---|---|
| `https://…` (Tailscale, proxy inverso) | ✅ | ✅ |
| `http://localhost` | ✅ | ✅ |
| `http://192.168.x.x` (LAN) | ❌ Se requiere HTTPS | ❌ solo una sugerencia |

!!! warning "Requisito de conexión HTTPS para PWA"

    Los navegadores solo instalan una aplicación desde una dirección segura **HTTPS** — `localhost` y `127.0.0.1` son
    las únicas excepciones. Con HTTP sin cifrar en tu red (por ejemplo `http://192.168.1.100:6040`)
    LibreFolio sigue funcionando en el navegador, pero no se puede instalar.

    Cualquier configuración HTTPS sirve. La opción más sencilla y gratuita es nuestra
    **[Guía de exposición de Tailscale](../admin/service_exposure.md)**: una dirección HTTPS segura sin
    tener que gestionar certificados SSL ni abrir puertos del router.

---

## 🔧 Solución de problemas

| Problema | Solución |
|---------|----------|
| **Instalar aplicación** no está en el menú | Ya estás en la aplicación instalada: el elemento está oculto allí |
| **Instalar aplicación** muestra una sugerencia en lugar de instalar | El navegador no ofreció una opción de instalación: comprueba que usas HTTPS (o `localhost`), o que la aplicación no esté ya instalada, y luego sigue la sugerencia |
| iOS: no aparece **Añadir a pantalla de inicio** | Abre la página en **Safari** y busca esa opción en su menú **Compartir** |
| La aplicación no se actualiza | Cierra y vuelve a abrir la aplicación — siempre carga la última versión desde tu servidor |
| Se cerró la sesión tras una actualización | Inicia sesión de nuevo — reiniciar el servidor puede cerrar todas las sesiones |

---

## 🔗 Relacionado

- 🌐 **[Guía de exposición de Tailscale](../admin/service_exposure.md)** — Una dirección HTTPS gratuita para tu instancia
- 🛠️ **[Optimizaciones PWA y móviles](../developer/frontend/pwa.md)** — Cómo se construye la parte de la aplicación (para desarrolladores)
