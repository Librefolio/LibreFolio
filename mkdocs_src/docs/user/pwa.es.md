# 📱 Instalar como Aplicación (PWA)

LibreFolio puede instalarse como una **Aplicación Web Progresiva (PWA)** en tu dispositivo. Esto te brinda una experiencia similar a la de una app: modo de pantalla completa, sin barra de direcciones del navegador y un icono en la pantalla de inicio, sin necesidad de descargarla de una tienda de aplicaciones.

---

## ✅ Qué obtienes

| Característica | Descripción |
|---------|-------------|
| **Modo de pantalla completa** | Sin barra de direcciones ni elementos distractores de la interfaz del navegador |
| **Icono en la pantalla de inicio** | Inicia LibreFolio como si fuera una aplicación nativa |
| **Sin interferencias de gestos** | Desactiva el deslizamiento para volver y el zoom de doble toque |
| **Sesión persistente** | Permanece conectado entre lanzamientos |

!!! note "Solo en línea"

    La PWA de LibreFolio requiere una conexión de red activa. No existe un modo offline: tus datos residen en tu servidor.

---

## 📲 Cómo instalar

### Android (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Busca el botón **"Instalar aplicación"** en el menú de **Ayuda y soporte** (icono ❓ arriba a la derecha)
3. Toca **Instalar** cuando se te solicite
4. LibreFolio aparecerá en tu pantalla de inicio

!!! tip "Método alternativo"

    Si el botón de Instalación no aparece, toca el **menú ⋮ del navegador → "Agregar a la pantalla de inicio"** o **"Instalar aplicación"**.

### iOS (Safari)

1. Abre LibreFolio en **Safari** (obligatorio; otros navegadores no son compatibles con PWA en iOS)
2. Toca el botón **Compartir** (cuadrado con flecha)
3. Desliza hacia abajo y toca **"Agregar a la pantalla de inicio"**
4. Toca **Agregar**

!!! warning "Limitación de iOS"

    El aviso de instalación automática no está disponible en iOS. Utiliza el menú de Compartir como se describió anteriormente. El menú de Ayuda mostrará instrucciones si estás en un dispositivo iOS.

### Escritorio (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Haz clic en el botón **"Instalar aplicación"** en el menú de Ayuda y soporte
3. O haz clic en el icono de instalación (⊕) en la barra de direcciones del navegador
4. LibreFolio se abrirá en su propia ventana

---

## 🌐 HTTP vs HTTPS

| Configuración | Instalación PWA | Aviso automático |
|-------|-------------|-------------|
| `https://` (Tailscale, proxy inverso) | ✅ Soporte completo | ✅ Chrome muestra banner |
| `http://localhost` | ✅ Funciona | ✅ Funciona |
| `http://192.168.x.x` (LAN) | ⚠️ Solo manual | ❌ Sin aviso automático |

!!! info "Autoalojado en LAN"

    Si accedes a LibreFolio vía HTTP en tu red local (ej. `http://192.168.1.100:6040`), el aviso de instalación automática no aparecerá. Aún puedes instalarlo manualmente:

    - **Android**: Menú del navegador → "Agregar a la pantalla de inicio"
    - **iOS**: Compartir → "Agregar a la pantalla de inicio"
    - **Escritorio**: No disponible en HTTP (usa Tailscale para HTTPS)

    Para obtener soporte completo de PWA, expón tu instancia a través de [Tailscale](../admin/tailscale_exposure.md) (HTTPS gratuito y sencillo).

---

## 🔧 Resolución de problemas

| Problema | Solución |
|---------|----------|
| El botón de instalación no aparece | Es posible que ya lo tengas instalado o que estés accediendo a través de HTTP en tu red local (LAN) |
| iOS: no aparece la opción de instalar | Debes usar **Safari**; Chrome/Firefox en iOS no son compatibles con PWA |
| La aplicación no se actualiza | Cierra y vuelve a abrir la aplicación; siempre descarga la versión más reciente |
| Sesión perdida después de una actualización | Inicia sesión nuevamente; esto es normal tras reiniciar el servidor |
