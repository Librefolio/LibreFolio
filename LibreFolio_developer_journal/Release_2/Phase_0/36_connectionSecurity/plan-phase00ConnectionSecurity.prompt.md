# Piano — fase 00, 36: l'indicatore di sicurezza della connessione e il login senza enumerazione

> **Stato**: ✅ pronto per il checkpoint (2026-10-09), FROZEN dopo l'handoff. L'analisi è approvata dal developer e la revisione dal coordinatore; la cura del login è approvata dal developer; D1, D3 e D5 sono decise (§0.1).
>
> - Workstream L, ramo `e-alfy-l-danske-bank`.
> - Base `da8d7a10b` (treno 22), worktree pulito al via.
> - I commit del 34s2 sono già nel treno 22: da `2fb8b8502` a `696105587`, merge `47c56581b`.
> - Corsia 6156 / 6166, `--data-dir /tmp/librefolio-r2-l`, un comando alla volta.
> - Coordinatore: sessione `c8328a01-…`.

## 0. Il mandato

**Il developer** ha approvato l'analisi del 2026-10-09 («Sì, procedi così (Consigliato)»):
- i livelli e la regola;
- l'endpoint dietro login;
- la riga nella Sidebar;
- il pallino sul burger quando il livello è rosso;
- il link alla doc, senza ancora.

L'avviso nella pagina di login (la fase 2) è facoltativo, ed è **fuori** da questo lotto.

**Il coordinatore** ha approvato la revisione, il 2026-10-09:
- l'endpoint restituisce `{client_class, cookie_secure}`;
- la classe viene dall'**ultimo** `X-Forwarded-For`, altrimenti dal peer TCP. È solo un consiglio e solo una classe: mai l'IP, neppure nei log;
- un avviso **solo per gli admin** quando il browser è in HTTPS ma `cookie_secure` è falso. Dà il rimedio per Nginx, o l'uscita da `never`;
- niente `FORWARDED_ALLOW_IPS`.

**La pagina di Q** (S20, FROZEN) entra con questo lotto nel treno 23. Se cambio un testo, lo dico al coordinatore, che lo gira a Q.
- Le etichette sono «Connection: secure / local network / not secure».
- L'avviso per gli admin è una riga in più nei **dettagli** dell'indicatore; il livello resta verde.
- Il link va alla radice, `user/connection-security/`.
- La regola, nella frase di Q: il server può confermare il verdetto del browser o renderlo incerto, ma **mai renderlo sicuro**.

**La cura del login.** Il developer: «Sì, nella 1.2, a L nel lotto dell'indicatore». Il difetto l'ha trovato O:
- `auth.py:102-104` controlla `is_active` prima della password, e risponde «Account is disabled» a chiunque;
- così si scopre che un account esiste ed è disattivato, senza conoscerne la password.

La cura:
- la password si controlla prima;
- con una password sbagliata, la risposta è identica (codice e testo) per un account inesistente, attivo o disattivato;
- «disattivato» si dice solo a chi ha la password giusta.

Bisogna anche verificare che S21 di O (`stores/app/auth.ts`, `LoginCard`) mostri ancora il messaggio giusto in tutti e tre i casi. Al checkpoint, una riga di CHANGELOG sotto 🔒 Security.

**Proprietà dei file**:
- `Sidebar.svelte` e `Header.svelte` sono miei per questo lotto (verificato dal coordinatore);
- i cataloghi i18n sono miei; le chiavi si aggiungono solo con `dev.py i18n`.

### 0.1 Le decisioni (2026-10-09)

- **D1 — il runner**: concesso a me dal coordinatore. Il file `_frontend_utility.py` non è di N: N ha `_backend_utils.py`. Condizioni:
  - solo righe aggiunte, nei tre punti indicati: dopo `headerScroll.test.ts`, dopo `Header.test.ts` in `front_component_unit`, e la voce `connection-security` accanto ad `app-start-auth`;
  - niente riformattazioni;
  - M ha una riga aperta a `:101` (`pdfViewerAssets.test.ts`), e il coordinatore simula la fusione.
- **D3 — la Sidebar chiusa**. Il developer: «Apre la Sidebar e poi i dettagli». Il clic sullo scudo apre la Sidebar, salvandone lo stato come fa il logo, poi apre i dettagli. Da aperta, la riga apre e chiude i dettagli in linea.
- **D5 — il canale di tempo**: approvato dal coordinatore. Si verifica la password contro un hash fittizio, calcolato una volta; il test controlla che il confronto bcrypt avvenga, senza misurare tempi.
- **S21, l'account disattivato con la password giusta.** Il developer ha approvato che «disattivato» si dica solo a chi ha la password giusta, quindi anche la UI deve dirlo.
  - `stores/app/auth.ts` e i cataloghi sono miei.
  - **Non toccare `LoginCard.*`**: K ha una fusione aperta su `LoginCard.test.ts`. LoginCard traduce già `{key}` da sé, quindi il test va in `auth.test.ts`.
  - **Il contratto lo scelgo io**: un 403 con `detail = {"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}`, sulla convenzione `error_code` di `assets.py:198`.
  - L'interceptor axios reagisce solo al 401 (`zodios-client.ts:130`), quindi un 403 arriva intatto al catch del login.
- **Doc**: `community/faq.en.md:83` diceva che un account disattivato riceve lo stesso messaggio generico; dopo la cura vale solo con la password sbagliata.
  - Coordinatore: «La FAQ la correggi tu, col docs-writer», solo EN e col testo proposto. IT, FR ed ES li aggiorna il giro delle traduzioni.
  - Gate: `mkdocs build` strict e `check-links`, dove resta solo il noto `#rolling-return`.
- **D2 — il namespace**: `connectionSecurity.*`, un namespace di funzione come `updateCheck`, al posto di `nav.*`. Il motivo è la skill `devpy-i18n`, che vuole `feature.*`.
  - Le chiavi stanno in **mappe di letterali interi**, perché l'audit le veda come usate.
- **Due testi rivisti**, mandati al coordinatore per Q:
  - `reason.uncertain` diventa generico, perché copre entrambi i casi discordi;
  - `cookieWarning` diventa vero anche con `never`, e dà il rimedio per Nginx.

## 1. Stato verificato (codice a `da8d7a10b`)

**Backend**
- In `api/v1/system.py`, `plugin-diagnostics` e `container-image-status` usano già `Depends(get_current_user)`. Gli schemi sono in `schemas/system.py`, tutti `StrictModel`.
- `session_cookie_secure(request)` sta in `api/v1/auth.py`; la regola di `auto` è quella del 34s2.
- Nessun codice legge l'IP del client.
- Non c'è `TrustedHostMiddleware`: ogni `Host` è accettato, e l'E2E coi nomi mappati può funzionare.
- **Il login** (`auth.py:117-127`): utente inesistente → 401 «Invalid credentials»; **inattivo → 401 «Account is disabled», senza aver controllato la password**; password sbagliata → 401 «Invalid credentials».
  - C'è anche un canale di tempo: per un utente inesistente bcrypt non gira (costo 12, circa 0,25 s), e la risposta è subito pronta.
  - `get_current_user` (`:97-98`) dice «User account is disabled» solo a chi ha già un token valido: non è enumerazione.
- **S21** (`stores/app/auth.ts:122-131`) mappa **ogni** 401 sulla chiave `auth.invalidCredentials`: è un solo messaggio, che non distingue i casi. Con la cura i tre casi con password sbagliata restano un 401, quindi la UI non cambia.

**Frontend**
- `Sidebar.svelte` è **legacy** (`export let`, `$:`, `on:click`); la riga della versione è nascosta quando la Sidebar è chiusa.
- `Header.svelte` è **runes** (`$props`, `$state`); il burger è `data-testid="mobile-menu-toggle"`.
- Un admin si riconosce con `$auth.user?.is_superuser === true` (`ChangelogModal.svelte:190`).
- I link alla doc hanno la forma `/mkdocs/${lang !== 'en' ? lang + '/' : ''}${path}` (`DocsLink.svelte`). `DocsLink` ha colori pensati per gli sfondi chiari: sul verde della Sidebar serve un link suo.
- Il client Zodios chiama le operazioni `get_<fn>_api_v1_system_<path>_get`.

**Runner**
- I file Vitest sono elencati a mano in `_frontend_utility.py`, nelle liste `front_utility_unit` (accanto a `headerScroll.test.ts`) e `front_component_unit` (accanto a `Header.test.ts`). Gli E2E si registrano con `add_test`, e `check-orphans` li controlla tutti.
- **`_frontend_utility.py` è di N**, quindi le righe le chiedo (§4 D1).
- `api system` → `test_system_api.py` e `api auth` → `test_auth_api.py` sono già registrati.

**Playwright**: `desktop` e `mobile` sono entrambi Chromium, quindi `--host-resolver-rules` vale per tutti e due.

## 2. Il disegno

### 2.1 Backend dell'indicatore

**`backend/app/utils/network_utils.py`** (nuovo, puro)
- `ClientClass = Literal["loopback", "vpn", "lan", "public", "unknown"]`.
- **`classify_ip(address)`**:
  - normalizza l'indirizzo: toglie parentesi e zone id, e porta un IPv6 mappato su IPv4;
  - `loopback`: `127/8`, `::1`;
  - `vpn`: `100.64.0.0/10`, `fd7a:115c:a1e0::/48`;
  - `lan`: `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `fe80::/10` e il resto di `fc00::/7`;
  - `public`: tutto il resto, compresi i range di documentazione;
  - `unknown`: `None`, un indirizzo illeggibile, `0.0.0.0` e `::`, il multicast.
- **`client_address(forwarded_for, peer)`**: l'**ultimo** valore non vuoto di `X-Forwarded-For`, senza spazi, parentesi e porta, se è un IP valido; altrimenti il peer.

**`GET /api/v1/system/connection`**, dietro `get_current_user`
- Restituisce `ConnectionSecurityResponse(client_class, cookie_secure)`.
- `cookie_secure = session_cookie_secure(request)`.
- Nessun log dell'indirizzo.

**`ConnectionSecurityResponse`** (`schemas/system.py`): un `StrictModel` con `client_class: Literal[...]` e `cookie_secure: bool`, descritti.

Poi `dev.py api sync`; i file generati sono ignorati da git.

### 2.2 Frontend dell'indicatore

**`frontend/src/lib/utils/security/connectionSecurity.ts`** (nuovo, puro)
- **`classifyHost(hostname)`** → `loopback | vpn | lan | public`. Maiuscole, punto finale e parentesi IPv6 non contano.
  - `loopback`: `localhost`, `*.localhost`, `127/8`, `::1`;
  - `vpn`: `100.64/10`, `fd7a:115c:a1e0::/48`, `*.ts.net`;
  - `lan`: gli IP privati, link-local e ULA, e i nomi `.local`, `.lan`, `.home.arpa`, `.internal`, oppure senza punti.
- **`assessConnection({protocol, hostname, server})`** → `{level, reason, cookieWarning}`, secondo la tabella di §2.3.
  - `server` è `{clientClass, cookieSecure}`, oppure `null` finché non risponde.
  - `cookieWarning` = `protocol === 'https:' && server?.cookieSecure === false`. Il filtro sugli admin lo fa la UI.
- **`connectionSecurityDocsUrl(lang)`** → `/mkdocs/<lang>/user/connection-security/`, senza prefisso per l'inglese.

**`frontend/src/lib/stores/app/connectionSecurityStore.ts`** (nuovo, writable: lo leggono la Sidebar legacy e l'Header runes)
- Il verdetto del client è disponibile subito.
- `refreshConnectionSecurity()` chiama l'endpoint **una volta** per ogni caricamento di pagina, e ricalcola.
- Se la chiamata fallisce, resta il verdetto del client, senza mostrare errori.

**`frontend/src/lib/components/layout/ConnectionSecurityIndicator.svelte`** (nuovo, runes). Props: `collapsed`, `onExpand`.
- **Sidebar aperta**: un pulsante con icona, etichetta e `aria-expanded`. Apre i **dettagli** in linea:
  - il motivo;
  - la riga per l'admin, se è `is_superuser` e c'è `cookieWarning`;
  - il link «How to connect securely», in una nuova scheda.
- **Sidebar chiusa**: solo l'icona, con l'etichetta al passaggio del mouse come le altre voci. Il click chiama `onExpand` e apre i dettagli (D3).
- Le icone lucide sono `ShieldCheck`, `ShieldHalf` e `ShieldAlert`, nei colori leggibili sul verde: smeraldo, lime e rosso chiari.
- Gli attributi:
  - `data-testid="connection-security"`, con `data-level`, `data-reason` e `data-server-checked`;
  - `connection-security-toggle`, `connection-security-details`, `connection-security-admin-warning` e `connection-security-docs-link`.

**`Sidebar.svelte`**: l'indicatore va nella sezione in basso, sopra la versione, ed è visibile anche da chiusa. `onExpand` apre la Sidebar e salva lo stato, come fa il logo.

**`Header.svelte`**: col livello `insecure`, un pallino rosso sul burger (`data-testid="mobile-menu-security-dot"`), più l'etichetta in `sr-only`.

### 2.3 La regola (concordata con Q)

| Browser | Il server vede | Livello | Motivo |
|---|---|---|---|
| `https:` | qualunque | secure | https |
| `http:`, host loopback | qualunque | secure | localhost |
| `http:`, host vpn | non `public` | secure | vpn |
| `http:`, host lan | non `public` | local | lan |
| `http:`, host public | `public`, `unknown` o nessuna risposta | insecure | internet |
| `http:`, host public | `lan`, `loopback` o `vpn` | local | uncertain |
| `http:`, host vpn o lan | `public` | local | uncertain |

**Limite noto**, documentato da Q: Docker Desktop esposto direttamente, e i proxy che non mandano `X-Forwarded-For`, nascondono il client. In quei casi l'indicatore dice «uncertain» invece del rosso.

### 2.4 i18n: 11 chiavi `connectionSecurity.*` più `auth.accountDisabled`, × 4 lingue, con `dev.py i18n add` (§0.1 D2)

Il namespace provvisorio è `nav.connectionSecurity.*`. Lo confermo con la skill `devpy-i18n`; le chiavi non sono visibili all'utente.
- Le etichette (`level.*`): secure «Connection: secure», local «Connection: local network», insecure «Connection: not secure».
- I motivi (`reason.*`): https, localhost, vpn, lan, uncertain, internet. I testi EN sono quelli mandati a Q.
- `cookieWarning`: «Your browser uses HTTPS, but LibreFolio was not told so: the session cookie is not marked Secure. Make the reverse proxy send X-Forwarded-Proto, or set SESSION_COOKIE_SECURE=always.»
- `learnMore`: «How to connect securely».
- IT, FR ed ES li scrivo io.

### 2.5 Il login senza enumerazione

**`auth.py`, `login`**
- La password si controlla **prima** dello stato dell'account.
- Utente inesistente, oppure password sbagliata → 401 «Invalid credentials», identico per un account inesistente, attivo o disattivato.
- Solo con la password giusta, se l'account è disattivato → 401 «Account is disabled».
- I log restano distinti («user not found», «wrong password», «user inactive»): li vede l'admin, non il client.

**Il canale di tempo**, nella stessa cura: per un utente inesistente, bcrypt gira lo stesso, contro un hash fittizio.
- È `verify_password_or_dummy(plain, hashed_or_none)` in `auth_service.py`.
- L'hash fittizio è calcolato una sola volta, la prima volta che serve (`functools.cache`), con lo stesso costo.
- Così il tempo di risposta non rivela se l'account esiste.

**Il contratto per l'account disattivato** (§0.1):
- **Backend**: solo con la password giusta, se l'account è disattivato → **403** con `detail = {"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}`. Un 403 dice «credenziali giuste, accesso negato».
- **Frontend**, `stores/app/auth.ts`:
  - un 401 → `auth.invalidCredentials`, come prima;
  - un 403 con `error_code === "ACCOUNT_DISABLED"` → `auth.accountDisabled`, una chiave nuova;
  - un 403 senza quel codice resta «un altro stato» → `{message}`, come prima.
  - `AuthErrorKey` si allarga di una chiave.
- `LoginCard` non si tocca: traduce già la chiave.

## 3. Superfici

| File | Proprietà | Cosa |
|---|---|---|
| `backend/app/utils/network_utils.py` (nuovo) | L | la classe dell'IP e la scelta dell'indirizzo |
| `backend/app/api/v1/system.py` | L | l'endpoint |
| `backend/app/schemas/system.py` | L | `ConnectionSecurityResponse` |
| `backend/app/api/v1/auth.py` | L | l'ordine dei controlli nel login |
| `backend/app/services/auth_service.py` | L | `verify_password_or_dummy` |
| `backend/test_scripts/test_api/test_system_api.py` | test-author | i test unitari e dal vivo dell'indicatore |
| `backend/test_scripts/test_api/test_auth_api.py` | test-author | i test sull'enumerazione al login |
| `frontend/src/lib/utils/security/connectionSecurity.ts` (+ `.test.ts`, nuovi) | L / test-author | la regola pura |
| `frontend/src/lib/stores/app/connectionSecurityStore.ts` (nuovo) | L | lo stato condiviso |
| `frontend/src/lib/components/layout/ConnectionSecurityIndicator.svelte` (+ `.test.ts`, nuovi) | L / test-author | la UI |
| `frontend/src/lib/components/layout/Sidebar.svelte` | L | l'inserimento |
| `frontend/src/lib/components/layout/Header.svelte` (+ `Header.test.ts`) | L / test-author | il pallino |
| `frontend/e2e/layout/connection-security.spec.ts` (nuovo) | test-author | l'E2E, desktop e mobile |
| `frontend/src/lib/stores/app/auth.ts` (+ `auth.test.ts`) | L / test-author | il 403 «account disattivato» → `auth.accountDisabled` |
| `frontend/src/lib/types/user.ts` | L | `AuthErrorKey` più `'auth.accountDisabled'` |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | L, con `dev.py i18n` | le 11 chiavi dell'indicatore, più `auth.accountDisabled` |
| `scripts/test_runner/_frontend_utility.py` | **N**, vedi §4 D1 | 2 percorsi Vitest e una voce E2E |

Nessuna migrazione e nessuna dipendenza nuova. `api sync` va fatto in ogni worktree. La doc la scrive Q.

## 4. Decisioni aperte

- **D1 — le righe del runner, nel file di N.** Servono:
  - `src/lib/utils/security/connectionSecurity.test.ts` in `front_utility_unit`;
  - `src/lib/components/layout/ConnectionSecurityIndicator.test.ts` in `front_component_unit`;
  - una voce E2E `connection-security`, per `layout/connection-security.spec.ts`, con la sua funzione.
  - Le aggiungo io solo se il coordinatore me le concede; altrimenti le aggiunge N.
- **D2 — il namespace** `nav.connectionSecurity.*`: è interno, lo decido io dopo aver letto la skill.
- **D3 — la Sidebar chiusa**: il click sullo scudo apre la Sidebar, salvando lo stato, e i dettagli. È coerente con i «dettagli» della pagina di Q. L'alternativa è che il click apra la doc.
- **D4 — l'endpoint non risponde**: resta il verdetto del client, senza errori visibili.
- **D5 — il canale di tempo del login**: bcrypt contro un hash fittizio per gli utenti inesistenti. È nella cura (§2.5); lo segnalo al coordinatore.

## 5. Rischi

1. **Falsi verdetti**, con lo split DNS, i proxy, IPv6 o la CGNAT dei provider. È un consiglio, non un controllo; e la regola non rende mai sicuro ciò che il browser non dice sicuro.
2. **Certificato self-signed**: accettato con un'eccezione risulta verde, perché il browser lo considera sicuro.
3. **Privacy**: l'endpoint restituisce solo la classe; l'IP non esce e non finisce nei log.
4. **Sidebar legacy**: l'indicatore è un componente runes figlio, e lo stato passa da uno store writable.
5. **L'E2E coi nomi mappati** gira in un contesto non sicuro: niente `crypto.randomUUID` (c'è già un ripiego) e niente service worker.
6. **Login**:
   - l'hash fittizio costa un bcrypt alla prima richiesta con un utente inesistente;
   - i messaggi lato server (`detail`) cambiano solo per il caso disattivato con password sbagliata.

## 6. Passi

1. Questo piano; poi il via del coordinatore su D1, D3 e D5.
2. **Gli stub**, con le firme finali, perché i rossi falliscano sulle asserzioni:
   - backend: utils, endpoint e schema; `verify_password_or_dummy`, che per ora non gira contro l'hash fittizio;
   - frontend: il modulo puro, lo store, il componente, la Sidebar e l'Header.
   - Poi `api sync`.
3. **I rossi**, col test-author:
   - backend: `test_system_api.py` e `test_auth_api.py`;
   - frontend: il modulo puro, il componente, `Header.test.ts` e l'E2E. Li registro dopo D1.
4. **La cura**, e le chiavi i18n.
5. **I gate** (§7), poi il checkpoint coi testi definitivi per Q e la riga di CHANGELOG 🔒.

## 7. Gate e definizione di fatto

**I gate**
- `api system`, `api auth`, `check-orphans`, ruff e black;
- `front check` (svelte-check) e Prettier sui file toccati;
- `front-utility utility-unit`, `component-unit`, e lo unit di `auth.ts` e `LoginCard`;
- `front build --debug`, poi `front-utility connection-security` (desktop e mobile) e `app-start-auth`;
- `i18n audit`, `git diff --check` e le porte libere.

**Fatto quando**:
- su localhost l'indicatore è verde;
- su un nome `.lan` è «rete locale»;
- su un nome pubblico, col server che vede una sorgente pubblica, è rosso, e c'è il pallino sul burger;
- l'avviso compare solo agli admin;
- il link porta alla radice della pagina di Q, nella lingua dell'utente;
- con una password sbagliata il login risponde allo stesso modo in tutti e tre i casi, e bcrypt gira sempre;
- la UI mostra il messaggio generico.

## 8. Avanzamento

### 8.0 ✅ Analisi e piano (2026-10-09)

> **Note implementazione**:
> - HEAD verificato: `da8d7a10b`, worktree pulito.
> - Letti `system.py`, `schemas/system.py`, il login di `auth.py`, `auth_service.py`, Sidebar, Header, gli store `auth`, `DocsLink`, il runner (`_frontend_utility.py`, `_backend_api.py`), `playwright.config.ts` e `main.py`.
> - DevWiki: niente di specifico sull'indicatore; graphify assente, come previsto.
>
> **⚠️ Fuori pista**:
> - la cartella del piano non esisteva, ed è stata creata (`36_connectionSecurity/`);
> - la cura del login è entrata nel lotto dopo la prima stesura (developer, tramite il coordinatore).

### 8.1 ✅ Gli stub, `api sync` e il runner (2026-10-09)

> **Note implementazione — gli stub**, con le firme finali e il comportamento invariato:
> - **Backend**:
>   - `utils/network_utils.py`: `classify_ip` → sempre "unknown", `client_address` → sempre None;
>   - `schemas/system.py`: `ConnectionSecurityResponse`, con `client_class: ClientClass` e `cookie_secure`;
>   - `system.py`: `GET /connection`, già vero. Unisce le righe di `X-Forwarded-For` con ", ", usa il peer e `session_cookie_secure`;
>   - `auth_service.verify_password_or_dummy`: per ora con None restituisce False senza bcrypt. Il login non è toccato.
> - **Frontend**:
>   - `utils/security/connectionSecurity.ts`: tipi e costanti finali; le funzioni restituiscono valori fissi;
>   - `stores/app/connectionSecurityStore.ts`: `connectionSecurity`, `refreshConnectionSecurity({location, fetchServerView, force})`, `resetConnectionSecurity`, `fetchServerViewFromApi`. `refresh` e `reset` non fanno niente;
>   - `ConnectionSecurityIndicator.svelte`: la radice con i `data-*` e il pulsante vuoto;
>   - `Sidebar.svelte`: monta l'indicatore sopra la versione, ed `expandSidebar()` riusa `toggleCollapsed()`;
>   - `types/user.ts`: `AuthErrorKey` accetta `'auth.accountDisabled'`.
> - **`dev.py api sync`**: exit 0. Il client generato ha `get_connection_security_api_v1_system_connection_get`, e i file generati sono ignorati.
> - **`dev.py front check`**: 0 errori. C'è 1 avviso a11y, atteso: il pulsante vuoto dello stub.
> - **Il runner** (D1): 23 righe aggiunte, 0 tolte, in `_frontend_utility.py`:
>   - `connectionSecurity.test.ts` dopo `headerScroll.test.ts`, nell'azione `core-unit`;
>   - `ConnectionSecurityIndicator.test.ts` dopo `Header.test.ts`, in `component-unit`;
>   - `front_connection_security` con la sua voce `connection-security`, accanto ad `app-start-auth`. Si vede in `dev.py test front-utility -h`.
> - **⚠️ Fuori pista**:
>   - la cartella `frontend/src/lib/utils/security/` non esisteva, ed è stata creata;
>   - `community/faq.en.md:83` va corretta (§0.1), chiesto al coordinatore a chi tocca;
>   - il test puro gira sotto `front-utility core-unit`, non sotto `utility-unit`.

### 8.2 ✅ La FAQ (2026-10-09)

> **Note implementazione** (docs-writer, solo EN, niente stamp):
> - `community/faq.en.md:83` ora ha il testo approvato, parola per parola: con una password sbagliata il messaggio è sempre «Invalid username or password», ed è il valore EN di `auth.invalidCredentials`, verificato; con la password giusta, l'account disattivato viene avvisato.
> - `mkdocs build` strict pulito; `check-links` dà exit 1 solo sul noto `#rolling-return`; `git diff --check` pulito.
> - `translate-validate` sulla FAQ: il debito di IT, FR ed ES c'era già, e quella riga nelle traduzioni è perfino più vecchia («check whether your account is activated»). La tradurrà il giro delle traduzioni.
> - **Vincolo**: la riga è vera solo insieme alla cura del login (403, `auth.ts`, `auth.accountDisabled`). Entra nello stesso checkpoint.

### 8.3 ✅ Backend: rossi e cura (2026-10-09)

> **Rossi** (test-author; ha eseguito solo i controlli statici):
> - **`test_system_api.py`** (`api system`):
>   - CONN-001, la tabella delle classi: 28 casi;
>   - CONN-002, i casi `unknown` (guardia);
>   - CONN-003, `client_address`: 11 casi, compreso l'IPv6 nudo `2001:db8::7`, quello che manda Nginx;
>   - CONN-004, `client_address(None, None)` (guardia);
>   - CONN-010…013, dal vivo:
>     - senza sessione → 401 (guardia);
>     - con sessione → esattamente due chiavi;
>     - `X-Forwarded-For` → `lan`, `public`, `vpn`;
>     - `X-Forwarded-Proto` → `cookie_secure` (guardia);
>   - CONN-020…023, in-process: un peer non fidato con l'intestazione, nessun peer, due righe d'intestazione, un'intestazione illeggibile che ripiega sul peer.
> - **`test_auth_api.py`** (`api auth`):
>   - LOGIN-010…014, dal vivo, con utenti propri, uno attivo e uno disattivato, cancellati a teardown. Le risposte devono essere identiche nei tre casi con password sbagliata; con la password giusta e l'account disattivato → 403 `ACCOUNT_DISABLED`; mai un cookie se il login fallisce;
>   - LOGIN-020…026, in-process su un DB privato, con una spia su `bcrypt.checkpw`: un controllo bcrypt per ogni login; l'hash fittizio ha costo `BCRYPT_ROUNDS` e si calcola una volta sola.
> - Nessun test dipendeva dal comportamento vecchio.
>
> | comando | esito |
> |---|---|
> | `dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-l api system` | **46 failed, 40 passed**: tutti su asserzioni (`'unknown' == …`), nessun ERROR |
> | `… api auth` | **7 failed, 49 passed**: LOGIN-012, 013, 020, 022, 023, 024, 025, su asserzioni (`401 != 403`, `0 == 1`) |
>
> **La cura**:
> - `network_utils.py`:
>   - `_parse_ip` toglie parentesi, porta (solo quando c'è un unico «:») e zone id, e riporta l'IPv4 mappato a IPv4;
>   - `classify_ip`: unspecified e multicast → `unknown`, poi loopback, vpn, lan, e altrimenti public;
>   - `client_address`: l'ultimo valore non vuoto, se è leggibile come IP; altrimenti il peer.
> - `auth_service.py`: `_dummy_password_hash()`, con `functools.cache`, è `hash_password(token)`; `verify_password_or_dummy` lo controlla e poi restituisce False.
> - `auth.py`, il login:
>   - `verify_password_or_dummy(...)` va per primo, poi `user is None` → 401 «Invalid credentials». I log restano distinti, e sono eventi costanti;
>   - un utente inattivo → 403, con `detail = {"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}`.
>
> | comando | esito |
> |---|---|
> | ruff e black sui 5 file del backend | puliti |
> | `… api system` | **86 passed** |
> | `… api auth` | **56 passed** |

### 8.4 ✅ Frontend: rossi, cura e i18n (2026-10-09)

> **Rossi** (test-author: Vitest, Prettier e `front check` eseguiti da lui; l'E2E no):
> - `connectionSecurity.test.ts`, nuovo:
>   - `classifyHost`, 33 casi;
>   - la tabella della regola, 88 righe, ognuna con entrambi i cookie, più un controllo che la tabella sia completa;
>   - `cookieWarning`;
>   - l'invariante «mai renderlo sicuro», con un controllo positivo;
>   - l'URL della doc in 4 lingue;
>   - lo store: l'arrivo della risposta, il browser che decide prima, il fallimento, una volta per caricamento, `force` e `reset`.
> - `ConnectionSecurityIndicator.test.ts`, nuovo:
>   - la radice segue lo store (7 casi);
>   - un caricamento nuovo chiede al server una volta;
>   - i dettagli in linea, con il motivo e il link (`href`, `target`, `rel`); il link nella lingua corrente;
>   - l'avviso per gli admin (3 casi, con il vero `auth.checkAuth()`);
>   - la Sidebar chiusa (D3).
> - `Header.test.ts`, solo aggiunte: il pallino quando il livello è insecure, nessun pallino per secure e local (4 casi), il pallino che segue lo store.
> - `auth.test.ts`, solo aggiunte:
>   - un 403 con `ACCOUNT_DISABLED` → `auth.accountDisabled` (2 casi);
>   - un 403 senza il codice → `{message}` (5 guardie);
>   - un 401 che porta `ACCOUNT_DISABLED` → resta generico;
>   - le righe del catalogo; la riga 401 «disabled» rinominata con un'etichetta veritiera.
> - `e2e/layout/connection-security.spec.ts`, nuovo, desktop e mobile:
>   - localhost → secure/localhost, con il link della doc;
>   - `lf-e2e.lan` → local/lan;
>   - `lf-e2e.example` → local/uncertain;
>   - `lf-e2e.example` con `X-Forwarded-For: 203.0.113.9` → insecure/internet, più il pallino su mobile.
>   - `test.use({launchOptions})` sta in cima al file, perché Playwright 1.61 lo rifiuta dentro un `describe`. Il login sui nomi mappati passa dal form.
>
> | comando | esito |
> |---|---|
> | `node_modules/.bin/vitest run` sui 4 file | **142 failed, 89 passed**: errori solo `AssertionError`, nessun import fallito né errore non gestito |
> | `dev.py front build --debug`, poi `… front-utility connection-security` | **8 failed** (4 desktop, 4 mobile), tutti su `data-server-checked` «false» ≠ «true»: un'asserzione. Il login sui nomi mappati funziona |
>
> **⚠️ Fuori pista**:
> - **Runner**: `front_connection_security` non aveva `project=""`, quindi sarebbe girato solo desktop. Corretto: era la mia riga, segnalata dal test-author.
> - **`auth.test.ts`**: la riga `ENGLISH` di `auth.accountDisabled` fissava «Account is disabled». L'ho allineata alla frase approvata, «This account is disabled: ask an administrator to enable it again.», come aveva chiesto il test-author. Il commento ora rimanda alla FAQ.
>
> **La cura**:
> - **`connectionSecurity.ts`**:
>   - `classifyHost`: normalizza (minuscole, niente parentesi, niente punto finale); parser IPv4 e IPv6, con `::`, coda IPv4 e zone id; poi i nomi (`localhost`, `.ts.net`, i suffissi LAN, i nomi senza punti);
>   - `assessConnection` segue la tabella di §2.3;
>   - `connectionSecurityDocsUrl` costruisce il percorso.
> - **Lo store**: `verdict()` e `browserVerdict()`, con il ripiego più prudente quando non c'è `window`. `refresh` imposta subito il verdetto del browser e chiede una sola volta, con `asked` e `force`. `generation` scarta le risposte superate; se la richiesta fallisce resta il verdetto del browser. `reset` azzera tutto.
> - **`ConnectionSecurityIndicator.svelte`**, runes:
>   - le chiavi stanno in mappe di letterali interi;
>   - le icone `ShieldCheck`, `ShieldHalf`, `ShieldAlert`, con toni chiari sul verde;
>   - aperta: il pulsante con l'etichetta e `aria-expanded`/`aria-controls`, e i dettagli resi solo quando sono aperti;
>   - chiusa: `aria-label` e `title` col livello; il click chiama `onExpand()` e apre i dettagli;
>   - l'avviso per gli admin con `$auth.user?.is_superuser === true && cookieWarning`;
>   - il link della doc con `target="_blank"` e `rel="noopener noreferrer"`.
> - **`Header.svelte`**: il pallino rosso dentro il burger con il livello insecure; l'`aria-label` del burger aggiunge l'etichetta «not secure».
> - **`auth.ts`**: `isAccountDisabled(body)`; un 403 con `ACCOUNT_DISABLED` → `auth.accountDisabled`.
> - **i18n**: 12 chiavi × 4 lingue con `dev.py i18n add`, passando gli argomenti da Python per via di `$scheme;` e degli apostrofi. Il diff è di 76 righe in più e 4 in meno, cioè una virgola per lingua; parità 4/4; `$scheme;` intatto.
>
> | comando | esito |
> |---|---|
> | `vitest run` sui 4 file | **231 passed** |
> | `dev.py front check` | 0 errori, 0 avvisi |
> | Prettier `--check` sui 16 file frontend toccati | puliti |
> | `front build --debug`, poi `front-utility connection-security` | **8 passed**, desktop e mobile |
> | `front-utility app-start-auth` | **3 passed** |

### 8.5 ✅ I gate del lotto (2026-10-09)

I comandi sono tutti `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-l <cat> <azione>`, uno alla volta (`/tmp/libreFolio_gates_36.sh`). I log sono in `files/plan36/` della sessione.

| gate | esito |
|---|---|
| `api all` | **922 passed, 2 skipped** (8 min 25 s) |
| `front-utility core-unit` | **3607 passed**, compreso `connectionSecurity.test.ts` |
| `front-utility component-unit` | **2936 passed**, compresi l'indicatore e `Header.test.ts` |
| `front-utility onboarding-component-unit` | **429 passed** (anche questo contiene `Header.test.ts`) |
| `front-user user-unit` | **57 passed**, compreso `auth.test.ts` |
| `front-utility auth` | **28 passed** (E2E del login e del logout) |
| `front-user multi-user` | **2 passed** |
| `front-utility connection-security` | **8 passed**, desktop e mobile (§8.4) |
| `front-utility app-start-auth` | **3 passed** (§8.4) |
| `utils gate-i18n-usage` | **195 passed** |
| `check-orphans` | pulito: 57 test API, 103 spec E2E e 338 Vitest registrati e raggiungibili da `all` |

- **i18n audit**: 0 chiavi non usate, nessuna traduzione mancante. Nessuna delle 12 chiavi nuove compare fra le morte o le non verificate.
- **Statici**:
  - ruff e black puliti sui 5 file del backend;
  - Prettier pulito sui 16 file frontend toccati;
  - `front check` con 0 errori e 0 avvisi.
- **Doc** (docs-writer, §8.2): `mkdocs build` strict pulito; `check-links` rosso solo sul noto `#rolling-return`.
- `git diff --check` pulito; le porte 6156 e 6166 sono libere.
- **Non eseguiti**: la build Docker; la gallery (lo screenshot di M, `security/connection-indicator`, è suo); le traduzioni della FAQ.
- **v1.1.0**: l'API rispondeva già 401 «Account is disabled» prima di controllare la password, e bcrypt non girava per un utente inesistente. La UI di allora mostrava il messaggio generico per ogni 401, ma l'API rivelava l'account.

### 8.6 ✅ Il checkpoint (2026-10-09)

I messaggi e i percorsi sono in `/tmp/libreFolio_commits/l-36-c{1,2,3}.{msg,paths}`, in quest'ordine:

| commit | percorsi |
|---|---|
| C1 `fix(auth): login does not reveal accounts` | `auth.py`, `auth_service.py`, `test_auth_api.py`, `stores/app/auth.ts`, `auth.test.ts`, `types/user.ts`, i 4 cataloghi, `community/faq.en.md` |
| C2 `feat(ui): connection security indicator` | `network_utils.py`, `schemas/system.py`, `system.py`, `test_system_api.py`, `connectionSecurity.ts` e il suo test, `connectionSecurityStore.ts`, `ConnectionSecurityIndicator.svelte` e il suo test, `Sidebar.svelte`, `Header.svelte`, `Header.test.ts`, `e2e/layout/connection-security.spec.ts`, `_frontend_utility.py` |
| C3 `docs(journal): plan 36, connection security` | questo piano |

- **I cataloghi vanno in C1** perché `auth.test.ts` controlla `auth.accountDisabled` in tutte e quattro le lingue. Contengono anche le 11 chiavi dell'indicatore, che C2 legge; per un commit restano senza lettore, e non fa danni.
- Ogni commit è coerente da solo:
  - C1 non tocca l'indicatore;
  - C2 usa `session_cookie_secure`, che è del 34s2, e i login degli utenti attivi, che non cambiano.
