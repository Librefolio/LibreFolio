# 📱 Instalar como Aplicación (PWA)

LibreFolio puede instalarse como una **Aplicación Web Progresiva (PWA)** en tu dispositivo. Esto te brinda una experiencia similar a una aplicación: modo de pantalla completa, sin barra de direcciones del navegador y un icono en la pantalla de inicio, sin necesidad de descargarla de una tienda de aplicaciones.

---

## ✅ Qué obtienes

| Característica | Descripción |
|---------|-------------|
| **Modo pantalla completa** | Sin barra de direcciones ni elementos distractores de la interfaz del navegador |
| **Icono en pantalla de inicio** | Inicia LibreFolio como una aplicación nativa |
| **Sin interferencia de gestos** | Deslizar para volver y zoom de doble toque desactivados |
| **Sesión persistente** | Permanece conectado entre lanzamientos |

!!! note "Online Only"

    La PWA de LibreFolio requiere una conexión de red activa. No existe un modo fuera de línea: tus datos residen en tu servidor.

---

## 📲 Cómo instalar

### Android (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Busca el botón **"Instalar aplicación"** en el menú de **Ayuda y soporte** (icono ❓ arriba a la derecha)
3. Toca **Instalar** cuando se te solicite
4. LibreFolio aparecerá en tu pantalla de inicio

!!! tip "Alternative method"

    Si el botón de instalar no aparece, toca el **menú ⋮ del navegador → "Agregar a la pantalla de inicio"** o **"Instalar aplicación"**.

### iOS (Safari)

1. Abre LibreFolio en **Safari** (obligatorio — otros navegadores no admiten PWA en iOS)
2. Toca el botón **Compartir** (cuadrado con flecha)
3. Desplázate hacia abajo y toca **"Agregar a la pantalla de inicio"**
4. Toca **Agregar**

!!! warning "iOS Limitation"

    El aviso de instalación automática no está disponible en iOS. Utiliza el menú Compartir como se describe anteriormente. El menú de Ayuda mostrará instrucciones si estás en un dispositivo iOS.

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

!!! info "Self-hosted on LAN"

    Si accedes a LibreFolio a través de HTTP en tu red local (ej. `http://192.168.1.100:6040`), el aviso de instalación automática no aparecerá. Aún puedes instalarlo manualmente:

    - **Android**: Menú del navegador → "Agregar a la pantalla de inicio"
    - **iOS**: Compartir → "Agregar a la pantalla de inicio"
    - **Escritorio**: No disponible en HTTP (usa Tailscale para HTTPS)

    Para obtener soporte completo de PWA, expón tu instancia a través de [Tailscale](../admin/tailscale_exposure.md) (HTTPS gratuito y sencillo).

---

## 🔧 Solución de problemas

| Problema | Solución |
|---------|----------|
| El botón de instalación no aparece | Es posible que ya esté instalado, o que estés usando HTTP en LAN |
| iOS: no hay opción de instalar | Debes usar **Safari**; Chrome/Firefox en iOS no admiten PWA |
| La aplicación no se actualiza | Cierra y vuelve a abrir la aplicación; siempre descarga la versión más reciente |
| Sesión perdida tras actualización | Inicia sesión nuevamente; esto es normal tras reinicios del servidor |
