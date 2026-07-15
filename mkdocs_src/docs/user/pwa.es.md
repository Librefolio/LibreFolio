# 📱 Instalar como aplicación (PWA)

LibreFolio se puede instalar como una **Aplicación Web Progresiva (PWA)** en tu dispositivo. Esto te brinda una experiencia similar a una aplicación nativa: modo de pantalla completa, sin barra de direcciones del navegador y un icono en la pantalla de inicio, sin necesidad de descargarla desde una tienda de aplicaciones.

---

## ✅ Lo que obtienes

| Característica | Descripción |
|-------------------|------------------------------------------|
| **Modo de pantalla completa** | Sin barra de direcciones ni interfaz del navegador |
| **Icono en la pantalla de inicio** | Inicia LibreFolio como una aplicación nativa |
| **Sin interferencia de gestos** | Deslizar hacia atrás y zoom con doble toque desactivados |
| **Sesión persistente** | Permanece conectado entre inicios |

!!! note "Solo con conexión"

    La PWA de LibreFolio requiere una conexión de red activa. No hay modo sin conexión: tus datos residen en tu servidor.

---

## 📲 Cómo instalar

### Android (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Busca el botón **"Instalar aplicación"** en el menú **Ayuda y soporte** (icono ❓ en la esquina superior derecha)
3. Toca **Instalar** cuando se te solicite
4. LibreFolio aparece en tu pantalla de inicio

!!! tip "Método alternativo"

    Si el botón de Instalar no aparece, toca el menú **⋮ del navegador → "Agregar a la pantalla de inicio"** o **"Instalar aplicación"**.

### iOS (Safari)

1. Abre LibreFolio en **Safari** (obligatorio: otros navegadores no admiten PWA en iOS)
2. Toca el botón **Compartir** (cuadrado con flecha)
3. Desplázate hacia abajo y toca **"Agregar a la pantalla de inicio"**
4. Toca **Agregar**

!!! warning "Limitación de iOS"

    La solicitud automática de instalación no está disponible en iOS. Usa el menú Compartir como se describe arriba. El menú de Ayuda mostrará instrucciones si estás en un dispositivo iOS.

### Escritorio (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Haz clic en el botón **"Instalar aplicación"** en el menú Ayuda y soporte
3. O haz clic en el icono de instalación (⊕) en la barra de direcciones del navegador
4. LibreFolio se abre en su propia ventana

---

## 🌐 HTTP vs HTTPS

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 45%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Configuración</th>
 <th style="width: 25%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Instalación PWA</th>
 <th style="width: 30%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Solicitud automática</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, proxy inverso)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Soporte completo</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Chrome muestra el banner</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>http://localhost</code></td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Funciona</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Funciona</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap; background-color: rgba(244, 67, 54, 0.04);"><code>http://192.168.x.x</code> (LAN)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ No disponible (HTTPS requerido)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Sin solicitud automática</td>
 </tr>
 </tbody>
</table>

!!! warning "Requisito de conexión HTTPS para PWA"

    Para instalar LibreFolio como PWA, **los navegadores modernos exigen estrictamente una conexión HTTPS segura** (excepto cuando se accede a través de `localhost` o `127.0.0.1` para desarrollo local).

    Si abres LibreFolio a través de HTTP simple en tu red local (por ejemplo, `http://192.168.1.100:6040`), la instalación de la PWA no estará disponible y la aplicación no podrá ejecutarse en modo independiente.

    Puedes elegir cualquier método que prefieras para habilitar HTTPS en tu instancia, pero recomendamos encarecidamente nuestra guía simple y gratuita: **[Guía de exposición con Tailscale](../admin/service_exposure.md)**. Te proporciona una URL HTTPS segura sin necesidad de configurar certificados SSL ni abrir puertos del enrutador.

---

## 🔧 Solución de problemas

| Problema | Solución |
|---------|----------|
| El botón Instalar no aparece | Puede que ya lo tengas instalado, o estés usando HTTP en la LAN |
| iOS: sin opción de instalar | Debes usar **Safari** — Chrome/Firefox en iOS no admiten PWA |
| La aplicación no se actualiza | Ciérrala y vuélvela a abrir: siempre obtiene la versión más reciente |
| Sesión perdida tras la actualización | Vuelve a iniciar sesión; esto es normal después de reiniciar el servidor |
