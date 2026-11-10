# 🔍 Comprobar la seguridad de la conexión

En la parte inferior de la barra lateral, cada usuario ve con qué seguridad habla el navegador con el servidor:
**Conexión: segura**, **Conexión: red local** o **Conexión: no segura**.
Los tres niveles, explicados a los usuarios: [Seguridad de la conexión](../user/connection-security.md).

Esta página es para quien administra el servidor: cómo comprobar que tu despliegue muestra **Conexión: segura** y cómo arreglarlo cuando no es así.

El objetivo:

- una dirección HTTPS, de Tailscale Serve o Funnel ([Exposición segura](service_exposure.md)) o de un proxy inverso con certificado ([Detrás de un proxy inverso](connection_proxy.md#reverse-proxy));
- una cookie de sesión marcada como `Secure`.

!!! info "📚 Esta guía tiene varias páginas"

    Esta página es la lista de comprobación: qué muestra el indicador, cómo mirar la vista del servidor y la cookie de sesión, qué hacer cuando falla una comprobación.
    Si ejecutas LibreFolio detrás de un proxy inverso, [Comprobar la seguridad de la conexión: detrás de un proxy inverso](connection_proxy.md) explica las cabeceras que debe enviar y cómo LibreFolio averigua la dirección del visitante.

---

## ✅ Lista de comprobación {: #checklist }

Recórrela cuando tu dirección HTTPS funcione, y de nuevo después de cualquier cambio en el proxy o en `.env`.
Necesitas una cuenta de administrador y, para las dos últimas comprobaciones, un teléfono con los datos móviles activados.

1. **Abre la dirección HTTPS e inicia sesión.**

    El indicador muestra 🟢 **Conexión: segura**; los detalles dicen que la conexión está cifrada con HTTPS.

2. **Busca la línea de la cookie.** Como administrador, los detalles muestran:

    - ese motivo y el enlace **Cómo conectarse de forma segura**;
    - un enlace a las [comprobaciones de seguridad](settings.md#security-tab) cuando listan errores o advertencias, por ejemplo **2 avisos de seguridad**.

    Una línea más sobre la cookie de sesión significa que LibreFolio no sabe nada del HTTPS: consulta [Detrás de un proxy inverso](connection_proxy.md#reverse-proxy).

3. **Pregunta al servidor.** En una pestaña nueva, abre:

    ```text
    https://<your address>/api/v1/system/connection
    ```

    La respuesta contiene `"cookie_secure":true` ([La vista del servidor](#server-view)).

4. **Mira la cookie.** Abre las herramientas de desarrollo del navegador.

    La cookie `session` está marcada como `Secure` ([La cookie de sesión](#session-cookie)).

5. **Desde fuera, abre la dirección HTTPS.** En el teléfono, con el Wi-Fi apagado.

    La página se carga y, tras iniciar sesión, el indicador muestra 🟢 **Conexión: segura**.

    | Dirección | Tailscale en el teléfono |
    | --- | --- |
    | Funnel o proxy inverso | Apagado |
    | Tailscale Serve (solo tu tailnet la abre) | Encendido |

6. **Desde fuera, prueba HTTP sin cifrar.** En el mismo teléfono, abre:

    ```text
    http://<your public IP or name>:6040
    ```

    O tu propio `PORT`. La página **no** se carga.

    Si aparece la página de inicio de sesión, el HTTP sin cifrar está abierto a internet:

    - no inicies sesión ahí: la contraseña viajaría en texto claro;
    - cierra el puerto ([Cuando falla una comprobación](#when-a-check-fails)).

    Quien inicie sesión desde esa dirección ve 🔴 **Conexión: no segura**, o 🏠 **Conexión: red local** con un motivo *Incierta* cuando el servidor no puede ver de dónde vienen los visitantes ([Límites](#limits)).

¿Han pasado todas las comprobaciones? Pide a tus usuarios que usen la dirección HTTPS en todos sus dispositivos y que actualicen sus marcadores antiguos ([Cómo conectarse de forma segura](../user/connection-security.md#https-address)).

!!! note "📶 ¿Todavía no hay dirección HTTPS?"

    Con el nivel 1 o 2 de [Exposición segura](service_exposure.md), los usuarios llegan a LibreFolio por HTTP sin cifrar.
    Comprueba el nivel que obtiene cada dirección ([Qué muestra el indicador](#indicator)) y que el HTTP sin cifrar no se cargue desde fuera (comprobación 6).
    Las comprobaciones de la cookie no se aplican: por HTTP sin cifrar la cookie de sesión no es `Secure`, y se espera `"cookie_secure":false`.

---

## 🚦 Qué muestra el indicador {: #indicator }

El navegador juzga la dirección que abrió.
Después, el servidor informa de desde dónde ve llegar la solicitud: puede confirmar el veredicto o volverlo incierto, nunca hacerlo seguro.

| Cómo llegan los usuarios a LibreFolio | Ejemplo | Nivel |
| --- | --- | --- |
| Tailscale Serve o Funnel, o un proxy inverso con certificado | `https://librefolio.your-tailnet.ts.net` | 🟢 **segura**: HTTPS |
| En el propio servidor | `http://localhost:6040` | 🟢 **segura**: `localhost` |
| IP de Tailscale o nombre MagicDNS completo, HTTP sin cifrar (nivel 1) | `http://100.a.b.c:6040` | 🟢 **segura**: VPN (Tailscale) |
| Nombre MagicDNS corto, HTTP sin cifrar: un nombre sin puntos cuenta como local | `http://your-server:6040` | 🏠 **red local** |
| Dirección local, también a través de un subnet router (nivel 2) | `http://192.168.1.100:6040` | 🏠 **red local** |
| Un puerto abierto en el router, HTTP sin cifrar | `http://myhome.duckdns.org:6040` | 🔴 **no segura** |

Cuando el servidor no puede ver las direcciones de los visitantes, la última fila muestra 🏠 **red local** con un motivo *Incierta* en su lugar ([Límites](#limits)).
Las reglas exactas de cada nivel (rangos de direcciones, nombres, casos *Incierta*): [Seguridad de la conexión](../user/connection-security.md#connection-secure).

---

## 🔎 La vista del servidor {: #server-view }

En cada carga de página, el indicador pregunta al servidor cómo ve la conexión: `GET /api/v1/system/connection`.

Para leer la misma respuesta:

1. **Inicia sesión en LibreFolio.**

2. **Abre esta dirección en una pestaña nueva del mismo navegador**, con tu dirección de LibreFolio en lugar de la del ejemplo:

    ```text
    https://librefolio.your-tailnet.ts.net/api/v1/system/connection
    ```

    El navegador muestra una respuesta de una línea:

    ```json
    {"client_class":"public","cookie_secure":true}
    ```

Conviene saber:

- sirve cualquier cuenta, no solo la de administrador;
- `{"detail":"Not authenticated"}` significa que no hay sesión en esa dirección: las sesiones pertenecen a una dirección, así que iniciar sesión en `http://192.168.1.100:6040` no te inicia sesión en la dirección HTTPS;
- el indicador pregunta una sola vez por carga de página: recarga LibreFolio tras un cambio para ver el nuevo veredicto.

**`cookie_secure`**: si una cookie de sesión establecida en esta solicitud sería `Secure`, según [`SESSION_COOKIE_SECURE`](#session-cookie).

| Dirección | Valor esperado |
| --- | --- |
| HTTPS | `true`. `false` muestra la línea del administrador sobre la cookie ([Detrás de un proxy inverso](connection_proxy.md#reverse-proxy)) |
| HTTP sin cifrar | `false` |

**`client_class`**: desde dónde ve el servidor que llega la solicitud.
Lee el último valor de `X-Forwarded-For`, el que añadió el proxy más cercano, si es una dirección IP; si no, la dirección de la propia conexión.
Solo sale del servidor la clase: la dirección nunca se devuelve ni se registra.

| `client_class` | La solicitud llega desde |
| --- | --- |
| `loopback` | El propio servidor: `127.0.0.0/8` o `::1` |
| `vpn` | Tailscale o Headscale: `100.64.0.0/10` o `fd7a:115c:a1e0::/48` |
| `lan` | Una red local: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` o `fc00::/7` |
| `public` | Cualquier otra dirección: internet |
| `unknown` | Ninguna dirección, o una que no se puede leer |

La clase cuenta solo por HTTP sin cifrar, y no en el propio servidor (`localhost`):

| Dirección en el navegador | `client_class` | Efecto en el veredicto |
| --- | --- | --- |
| Pública | `public` o `unknown` | Confirma **Conexión: no segura** |
| Pública | `loopback`, `vpn` o `lan` | Pasa a **Conexión: red local**: veredicto incierto |
| Local o de Tailscale | `public` | Veredicto incierto |
| Local o de Tailscale | Cualquier otra | Ninguno |

En la dirección HTTPS la clase no cambia nada, pero te dice si el servidor ve las direcciones de los visitantes.
Desde el teléfono con datos móviles, con Tailscale apagado:

- `public`: el servidor las ve;
- `lan` o `loopback`: no las ve ([Límites](#limits)).

---

## 🍪 La cookie de sesión {: #session-cookie }

La cookie que mantiene tu sesión iniciada se llama `session`.
LibreFolio la establece al iniciar sesión, siempre con `HttpOnly` (los scripts de la página no pueden leerla) y `SameSite=Lax`.

Que además sea `Secure`, es decir, que se envíe solo por HTTPS, depende de `SESSION_COOKIE_SECURE` en `.env`:

| Valor | `Secure` |
| --- | --- |
| `auto` (predeterminado) | Cuando la solicitud es HTTPS: vista directamente, o porque el primer valor de `X-Forwarded-Proto` enviado por un proxy inverso es `https` |
| `always` | Siempre |
| `never` | Nunca |

Las mayúsculas y los espacios alrededor del valor no importan.
Cualquier otro valor detiene LibreFolio al arrancar.
Cuándo `always` o `never` es la elección correcta: [Configuración](configuration.md#session-cookie-secure).

La marca se decide al iniciar sesión: una cookie que ya está en el navegador conserva la marca que recibió entonces.
Tras arreglar el proxy o la opción, cierra sesión y vuelve a iniciarla.

Para ver la marca en el navegador:

1. **Inicia sesión en la dirección HTTPS.**

2. **Abre las herramientas de desarrollo**: `F12`, o clic derecho en la página → **Inspeccionar**.

    Safari las muestra solo cuando las funciones de desarrollo están activadas en sus ajustes.

3. **Abre las cookies de tu dirección de LibreFolio.**

    | Navegador | Ruta |
    | --- | --- |
    | Chrome, Edge | **Aplicación** → **Cookies** |
    | Firefox, Safari | **Almacenamiento** → **Cookies** |

4. **Lee la fila `session`.**

    **Secure** está marcada (`true` en Firefox), igual que **HttpOnly**; **SameSite** indica `Lax`.

La consola no puede mostrarlo: `document.cookie` omite las cookies `HttpOnly`.

---

## 🛠️ Cuando falla una comprobación {: #when-a-check-fails }

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| La dirección HTTPS no muestra **Conexión: segura** | La página no está en HTTPS: la barra de direcciones muestra `http://` | Abre la dirección `https://` y haz que el proxy redirija `http://` a ella |
| La línea sobre la cookie de sesión, o `"cookie_secure":false` en la dirección HTTPS | El proxy no envía `X-Forwarded-Proto: https`, o `SESSION_COOKIE_SECURE` es `never` | Arregla el proxy ([Detrás de un proxy inverso](connection_proxy.md#reverse-proxy)) o vuelve a poner la opción en `auto`, y recarga |
| `"cookie_secure":true`, pero la cookie `session` no es `Secure` | La cookie se estableció antes del arreglo | Cierra sesión y vuelve a iniciarla |
| `{"detail":"Not authenticated"}` | No hay sesión en esta dirección | Inicia sesión en esta dirección, en el mismo navegador |
| Cada inicio de sesión acaba otra vez en la página de inicio de sesión | La cookie es `Secure`, pero el navegador usa HTTP sin cifrar: `SESSION_COOKIE_SECURE=always`, o un proxy que envía `X-Forwarded-Proto: https` a un navegador con HTTP sin cifrar | Usa la dirección HTTPS o arregla el proxy: [Configuración](configuration.md#session-cookie-secure) |
| Desde fuera, la dirección HTTPS no se carga | Una dirección de Tailscale Serve es privada; un Funnel nuevo necesita aprobación y unos minutos | Enciende Tailscale en el teléfono, o usa Funnel; aprueba el Funnel y espera ([Exposición segura: acceso público con Funnel](service_exposure_funnel.md#step-2-approve-and-wait-for-propagation)) |
| Desde fuera, se carga `http://…:6040` sin cifrar | El puerto de LibreFolio está abierto a internet: una redirección de puertos en el router, o un servidor con dirección pública | Ciérralo: quita la redirección de puertos o bloquea el puerto en el cortafuegos del servidor. Tailscale no necesita ningún puerto abierto, un proxy inverso solo el suyo |
| `client_class` muestra `lan` o `loopback` desde datos móviles, o el HTTP sin cifrar desde internet muestra **Conexión: red local**, *Incierta* | El servidor no puede ver de dónde vienen los visitantes | Consulta [Límites](#limits); con Nginx, añade la línea `X-Forwarded-For` |
| Una dirección de Tailscale muestra **Conexión: red local** | Un nombre MagicDNS corto no tiene puntos, así que cuenta como local | Usa la IP de Tailscale, el nombre completo `.ts.net` o, mejor, la dirección HTTPS |

---

## ⚠️ Límites {: #limits }

El indicador es un consejo, no una comprobación: no bloquea nada.
Dos límites importan cuando compruebas un despliegue.

**No siempre ve de dónde vienen los visitantes.**

- Con Docker Desktop expuesto directamente, o detrás de un proxy que no pasa la dirección del visitante en `X-Forwarded-For`, el servidor ve a todos los visitantes como locales: `lan`, o `loopback` para un proxy en la misma máquina.
- Entonces el HTTP sin cifrar desde internet muestra **Conexión: red local**, con un veredicto incierto, en lugar de **Conexión: no segura**.
- Las direcciones HTTPS no se ven afectadas: muestran **Conexión: segura** en ambos casos.
- Docker Engine en Linux conserva la dirección del visitante por IPv4.
- Por IPv6, a menos que el contenedor tenga una dirección IPv6 propia, los visitantes IPv6 llegan a través del proxy de Docker, desde la puerta de enlace de la red del contenedor: todos comparten esa única dirección local, para el indicador y para los límites por dirección del visitante, que por tanto los cuentan juntos.
- El proxy de Docker no añade ninguna cabecera de reenvío, así que LibreFolio no puede notarlo: su advertencia sobre un proxy en el que no confía necesita una cabecera de ese tipo.
- Un proxy inverso por delante que vea la dirección de cada visitante, configurado como explica [La dirección del visitante](connection_proxy.md#client-address), lo evita.

**No comprueba los certificados.**

- Un certificado autofirmado que un usuario aceptó en el navegador muestra **Conexión: segura**: el tráfico está cifrado, pero nadie garantiza que el servidor sea realmente tuyo.

Ni el indicador ni la cookie de sesión necesitan una lista de proxies de confianza:

- un `X-Forwarded-For` falsificado solo engaña al indicador de quien lo envió;
- `X-Forwarded-Proto` solo puede activar `Secure`, así que un `https` falsificado solo rompe el propio inicio de sesión del remitente.

Los límites por dirección del visitante son otra cuestión: [La dirección del visitante](connection_proxy.md#client-address).

---

## 🔗 Relacionado

- 📄 **[Comprobar la seguridad de la conexión: detrás de un proxy inverso](connection_proxy.md)** — En qué proxies confía LibreFolio, la dirección del visitante, Tailscale con Docker
- 🔐 **[Seguridad de la conexión](../user/connection-security.md)** — La guía de usuario: los tres niveles y qué hacer en cada uno
- 🌐 **[Exposición segura](service_exposure.md)** — Tailscale, de una VPN privada a una dirección HTTPS pública
- 🐳 **[Docker avanzado](docker_advanced.md)** — Archivo Compose, variables de entorno, proxy inverso
- 📝 **[Configuración](configuration.md)** — `SESSION_COOKIE_SECURE` y todas las demás opciones de `.env`
