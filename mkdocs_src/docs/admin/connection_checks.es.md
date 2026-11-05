# 🔍 Comprobación de la seguridad de la conexión

Todos los usuarios ven, en la parte inferior de la barra lateral de LibreFolio, con qué seguridad se comunica su navegador con el servidor: **Conexión: segura**, **Conexión: red local** o **Conexión: no segura**. La guía de usuario, [Seguridad de la conexión](../user/connection-security.md), les explica los tres niveles. Esta página está dirigida a quien administra el servidor: cómo comprobar que tu despliegue ofrece a sus usuarios **Conexión: segura** y cómo solucionarlo cuando no es así.

El objetivo es una dirección HTTPS, de Tailscale Serve o Funnel
([Exposición segura](service_exposure.md)) o de un proxy inverso con certificado
([Detrás de un proxy inverso](connection_proxy.md#reverse-proxy)), y una cookie de sesión marcada como `Secure`.

!!! info "📚 Esta guía consta de varias páginas"

    Esta página es la lista de comprobación: qué muestra el indicador, cómo consultar la vista del servidor y la cookie de sesión, y qué hacer cuando falla una comprobación. Si ejecutas LibreFolio detrás de un proxy inverso, [Comprobación de la seguridad de la conexión: detrás de un proxy inverso](connection_proxy.md) explica las cabeceras que debe enviar y cómo LibreFolio averigua la dirección del visitante.

---

## ✅ Lista de comprobación {: #checklist }

Recórrela cuando tu dirección HTTPS funcione y de nuevo después de cualquier cambio en el proxy o en `.env`.
Necesitas una cuenta de administrador y, para las dos últimas comprobaciones, un teléfono con datos móviles.

1. **Abre la dirección HTTPS e inicia sesión.** El indicador muestra 🟢 **Conexión: segura**, y sus
   detalles indican que la conexión está cifrada con HTTPS.
2. **Busca la línea de la cookie.** Con la sesión iniciada como administrador, los detalles muestran ese motivo y el
   enlace **Cómo conectarse de forma segura**, además de, cuando las [comprobaciones de seguridad](settings.md#security-tab) enumeran
   errores o advertencias, un enlace a ellas, como **2 advertencias de seguridad**. Una línea más, sobre la
   cookie de sesión, significa que LibreFolio no tiene constancia de que se use HTTPS: consulta
   [Detrás de un proxy inverso](connection_proxy.md#reverse-proxy).
3. **Pregunta al servidor.** En una pestaña nueva, abre `https://<your address>/api/v1/system/connection`: la
   respuesta contiene `"cookie_secure":true` ([La vista del servidor](#server-view)).
4. **Examina la cookie.** En las herramientas de desarrollo del navegador, la cookie `session` está
   marcada como `Secure` ([La cookie de sesión](#session-cookie)).
5. **Desde fuera, abre la dirección HTTPS.** En el teléfono, con el Wi-Fi desactivado, la página se carga y, cuando
   inicias sesión, el indicador muestra 🟢 **Conexión: segura**. Mantén Tailscale desactivado en el teléfono para una
   dirección de Funnel o de proxy inverso; actívalo para una dirección de Tailscale Serve, a la que solo puede acceder tu
   tailnet.
6. **Desde fuera, prueba HTTP sin cifrar.** En el mismo teléfono, `http://<your public IP or name>:6040`, o
   tu propio `PORT`, no se carga. Si aparece la página de inicio de sesión, HTTP sin cifrar está abierto a internet:
   no inicies sesión ahí, ya que la contraseña viajaría en texto claro, y cierra el puerto
   ([Cuando falla una comprobación](#when-a-check-fails)). Quien inicie sesión a través de esa dirección verá
   🔴 **Conexión: no segura**, o 🏠 **Conexión: red local** con un motivo *Poco claro* cuando
   el servidor no pueda ver de dónde vienen los visitantes ([Límites](#limits)).

¿Han pasado todas las comprobaciones? Pide a tus usuarios que usen la dirección HTTPS en todos sus dispositivos y que actualicen sus marcadores antiguos ([Cómo conectarse de forma segura](../user/connection-security.md#https-address)).

!!! note "📶 ¿Aún no hay una dirección HTTPS?"

    Con el nivel 1 o 2 de [Exposición segura](service_exposure.md), los usuarios acceden a LibreFolio por HTTP sin cifrar. Comprueba el nivel que obtiene cada dirección ([Qué muestra el indicador](#indicator)) y que HTTP sin cifrar no se cargue desde fuera (comprobación 6). Las comprobaciones de cookies no se aplican: por HTTP sin cifrar, la cookie de sesión no es `Secure`, y se espera `"cookie_secure":false`.

---

## 🚦 Qué muestra el indicador {: #indicator }

El navegador juzga la dirección que abrió; después, el servidor informa de dónde ve llegar la solicitud y puede confirmar ese veredicto o volverlo incierto, pero nunca volverlo seguro. Lo que ven tus usuarios, según cómo lleguen a LibreFolio:

| Cómo llegan los usuarios a LibreFolio | Ejemplo | Nivel |
| --- | --- | --- |
| Tailscale Serve o Funnel, o un proxy inverso con certificado | `https://librefolio.your-tailnet.ts.net` | 🟢 **segura**: HTTPS |
| En el propio servidor | `http://localhost:6040` | 🟢 **segura**: `localhost` |
| IP de Tailscale o nombre completo de MagicDNS, HTTP sin cifrar (nivel 1) | `http://100.a.b.c:6040` | 🟢 **segura**: VPN (Tailscale) |
| Nombre corto de MagicDNS, HTTP sin cifrar: un nombre sin punto cuenta como local | `http://your-server:6040` | 🏠 **red local** |
| Dirección local, también a través de un router de subred (nivel 2) | `http://192.168.1.100:6040` | 🏠 **red local** |
| Un puerto abierto en el router, HTTP sin cifrar | `http://myhome.duckdns.org:6040` | 🔴 **no segura** |

Cuando el servidor no puede ver las direcciones de tus visitantes, la última fila muestra 🏠 **red local** con
un motivo *Poco claro* en su lugar ([Límites](#limits)). La guía de usuario ofrece las reglas exactas de cada
nivel: rangos de direcciones, nombres y los casos en los que aparece *Poco claro*
([Seguridad de la conexión](../user/connection-security.md#connection-secure)).

---

## 🔎 La vista del servidor {: #server-view }

El indicador pregunta al servidor cómo ve la conexión, una vez por carga de página:
`GET /api/v1/system/connection`. Puedes leer la misma respuesta: con la sesión iniciada, abre esta dirección en una
pestaña nueva del mismo navegador, sustituyendo la dirección del ejemplo por tu propia dirección de LibreFolio:

```text
https://librefolio.your-tailnet.ts.net/api/v1/system/connection
```

El navegador muestra una respuesta de una línea, por ejemplo:

```json
{"client_class":"public","cookie_secure":true}
```

Cualquier cuenta sirve, no solo la de administrador. Una respuesta como `{"detail":"Not authenticated"}`
significa que no hay sesión en esa dirección: las sesiones pertenecen a una dirección, así que iniciar sesión en
`http://192.168.1.100:6040` no inicia tu sesión en la dirección HTTPS. Y como el indicador pregunta
solo una vez por carga de página, recarga LibreFolio después de un cambio para ver su nuevo veredicto.

**`cookie_secure`** indica si una cookie de sesión establecida en esta solicitud sería `Secure`, según
[`SESSION_COOKIE_SECURE`](#session-cookie). En la dirección HTTPS debe ser `true`: `false` es lo que
muestra la línea del administrador sobre la cookie ([Detrás de un proxy inverso](connection_proxy.md#reverse-proxy)). Por HTTP sin cifrar,
se espera `false`.

**`client_class`** indica de dónde ve el servidor que llega la solicitud. Lee el último valor de
`X-Forwarded-For`, el que añadió el proxy más cercano, cuando es una dirección IP, y, en caso contrario,
la dirección de la propia conexión. Solo la clase sale del servidor: la dirección nunca se devuelve ni se registra.

| `client_class` | La solicitud proviene de |
| --- | --- |
| `loopback` | El propio servidor: `127.0.0.0/8` o `::1` |
| `vpn` | Tailscale o Headscale: `100.64.0.0/10` o `fd7a:115c:a1e0::/48` |
| `lan` | Una red local: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` o `fc00::/7` |
| `public` | Cualquier otra dirección: internet |
| `unknown` | Ninguna dirección, o una que no se puede leer |

La clase solo se tiene en cuenta por HTTP sin cifrar, y no en el propio servidor (`localhost`):

- con una dirección pública en el navegador, `public` o `unknown` confirma **Conexión: no segura**,
  mientras que `loopback`, `vpn` o `lan` la convierten en **Conexión: red local**, como poco clara;
- con una dirección local o de Tailscale en el navegador, `public` vuelve poco claro el veredicto, y cualquier otra
  clase lo deja como está.

En la dirección HTTPS, la clase no cambia nada, pero te indica si el servidor puede ver las direcciones de tus
visitantes: desde el teléfono con datos móviles y Tailscale desactivado, `public` significa que sí puede, y
`lan` o `loopback` significan que no ([Límites](#limits)).

---

## 🍪 La cookie de sesión {: #session-cookie }

La cookie que mantiene iniciada la sesión de un usuario se llama `session`. LibreFolio la establece al iniciar sesión, siempre
`HttpOnly`, para que los scripts de la página no puedan leerla, y `SameSite=Lax`. Que además sea `Secure`,
enviada solo por HTTPS, depende de `SESSION_COOKIE_SECURE` en `.env`:

- **`auto`**, el valor predeterminado: `Secure` cuando la solicitud es HTTPS, ya sea porque se observa directamente o porque el primer
  valor de `X-Forwarded-Proto` que envía un proxy inverso es `https`;
- **`always`**: siempre `Secure`;
- **`never`**: nunca `Secure`.

El uso de mayúsculas o minúsculas y los espacios alrededor del valor no importan; cualquier otro valor detiene LibreFolio al arrancar. Cuándo
es adecuado elegir `always` o `never`: [Configuración](configuration.md#session-cookie-secure).

La marca se decide al iniciar sesión: la cookie que un navegador ya tiene conserva la marca que recibió entonces. Después
de corregir el proxy o la opción, cierra sesión y vuelve a iniciar sesión.

Para ver la marca en el navegador:

1. Inicia sesión en la dirección HTTPS.
2. Abre las herramientas de desarrollo: `F12`, o haz clic derecho en la página y elige **Inspeccionar**. Safari solo las muestra
   cuando sus funciones de desarrollador están activadas en la configuración de Safari.
3. Abre las cookies de tu dirección de LibreFolio: **Aplicación** → **Cookies** en Chrome y Edge,
   **Almacenamiento** → **Cookies** en Firefox y Safari.
4. En la fila `session`, **Secure** está marcada (`true` en Firefox), y **HttpOnly** también;
   **SameSite** indica `Lax`.

La consola no puede mostrarla: `document.cookie` omite las cookies `HttpOnly`.

---

## 🛠️ Cuando falla una comprobación {: #when-a-check-fails }

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| La dirección HTTPS no muestra **Conexión: segura** | La página no está en HTTPS: la barra de direcciones muestra `http://` | Abre la dirección `https://` y haz que el proxy redirija `http://` a ella |
| La línea sobre la cookie de sesión, o `"cookie_secure":false` en la dirección HTTPS | El proxy no envía `X-Forwarded-Proto: https`, o `SESSION_COOKIE_SECURE` es `never` | Corrige el proxy ([Detrás de un proxy inverso](connection_proxy.md#reverse-proxy)) o vuelve a poner la opción en `auto`, y luego recarga |
| `"cookie_secure":true`, pero la cookie `session` no es `Secure` | La cookie se estableció antes de la corrección | Cierra sesión y vuelve a iniciar sesión |
| `{"detail":"Not authenticated"}` | No hay sesión en esta dirección | Inicia sesión en esta dirección, en el mismo navegador |
| Cada inicio de sesión vuelve a terminar en la página de inicio de sesión | La cookie es `Secure`, pero el navegador usa HTTP sin cifrar: `SESSION_COOKIE_SECURE=always`, o un proxy que envía `X-Forwarded-Proto: https` a LibreFolio para un navegador que usa HTTP sin cifrar | Usa la dirección HTTPS o corrige el proxy: consulta [Configuración](configuration.md#session-cookie-secure) |
| Desde fuera, la dirección HTTPS no se carga | Una dirección de Tailscale Serve es privada; un Funnel nuevo necesita aprobación y unos minutos | Activa Tailscale en el teléfono o usa Funnel; aprueba el Funnel y espera ([Exposición segura: acceso público con Funnel](service_exposure_funnel.md#step-2-approve-and-wait-for-propagation)) |
| Desde fuera, se carga `http://…:6040` sin cifrar | El puerto de LibreFolio está abierto a internet: una redirección de puertos en el router, o un servidor con una dirección pública | Ciérralo: elimina la redirección de puertos o bloquea el puerto en el firewall del servidor. Tailscale no necesita ningún puerto abierto, y un proxy inverso solo el suyo |
| `client_class` muestra `lan` o `loopback` desde datos móviles, o el HTTP sin cifrar desde internet muestra **Conexión: red local**, *Poco claro* | El servidor no puede ver de dónde vienen los visitantes | Consulta [Límites](#limits); con Nginx, añade la línea `X-Forwarded-For` |
| Una dirección de Tailscale muestra **Conexión: red local** | Un nombre corto de MagicDNS no tiene punto, así que cuenta como local | Usa la IP de Tailscale, el nombre completo `.ts.net` o, mejor, la dirección HTTPS |

---

## ⚠️ Límites {: #limits }

El indicador es un aviso, no una comprobación: no bloquea nada. Hay dos límites que importan cuando compruebas un
despliegue.

**No siempre puede ver de dónde vienen los visitantes.** Con Docker Desktop expuesto directamente, o detrás de un
proxy que no pasa la dirección del visitante en `X-Forwarded-For`, el servidor considera locales a todos los visitantes:
`lan`, o `loopback` para un proxy en la misma máquina. Entonces, el HTTP sin cifrar desde internet
muestra **Conexión: red local**, como poco clara, en lugar de **Conexión: no segura**. Las direcciones
HTTPS no se ven afectadas: muestran **Conexión: segura** en cualquier caso. Docker Engine en Linux
conserva la dirección del visitante con IPv4; con IPv6, a menos que el contenedor tenga su propia dirección
IPv6, los visitantes IPv6 llegan a través del proxy de Docker, desde la puerta de enlace de la red del contenedor, así que
todos comparten esa única dirección local, tanto para el indicador como para los límites por dirección del visitante,
que entonces los agrupan. El proxy de Docker no añade ninguna cabecera de reenvío, así que LibreFolio
no puede detectarlo: su advertencia sobre un proxy en el que no confía necesita una cabecera de reenvío. Un proxy inverso por delante
que vea la propia dirección de cada visitante, configurado como se explica en [La dirección del visitante](connection_proxy.md#client-address),
lo evita.

**No comprueba los certificados.** Un certificado autofirmado que un usuario haya aceptado en el navegador
muestra **Conexión: segura**: el tráfico está cifrado, pero nadie garantiza que el servidor sea realmente
tuyo.

Ni el indicador ni la cookie de sesión necesitan una lista de proxies de confianza: un `X-Forwarded-For` falsificado
solo engaña al indicador de quien lo envió, y como `X-Forwarded-Proto` solo puede activar `Secure`, un `https`
falsificado solo rompe el propio inicio de sesión del emisor. Los límites por dirección del visitante son otra
cuestión: consulta [La dirección del visitante](connection_proxy.md#client-address).

---

## 🔗 Relacionado

- 📄 **[Comprobación de la seguridad de la conexión: detrás de un proxy inverso](connection_proxy.md)** — En qué proxy confía LibreFolio, la dirección del visitante, Tailscale con Docker
- 🔐 **[Seguridad de la conexión](../user/connection-security.md)** — La guía de usuario: los tres niveles
  y qué hacer en cada uno
- 🌐 **[Exposición segura](service_exposure.md)** — Tailscale, de una VPN privada a una dirección HTTPS
  pública
- 🐳 **[Docker avanzado](docker_advanced.md)** — Archivo Compose, variables de entorno, proxy inverso
- 📝 **[Configuración](configuration.md)** — `SESSION_COOKIE_SECURE` y todas las demás opciones de `.env`
