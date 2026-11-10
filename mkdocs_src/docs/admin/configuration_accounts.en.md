# 👥 Configuration: Accounts and Asset Search

Who can **sign up** to your LibreFolio, how many accounts it may hold, the limit on failed sign-ins and
the **initial administrator**; then two options of the asset search: the order of the price providers in
the results and the optional web search.

- **Where to write it**: in LibreFolio's `.env` file ([Configuration](configuration.md), the guide's first page,
  explains the file and its other options). Then restart LibreFolio. With Docker Compose, run `docker compose up -d`.
- **From inside the app**: the matching choices are in the [Global Settings](settings.md)
  (**Settings › Administration**). A set variable wins: each line below says how.

---

## 👥 Accounts and Sign-ups {: #accounts }

**Where**: in LibreFolio's `.env`, **Accounts** section of `.env.example`: uncomment a line to set it. All
optional; an empty value counts as not set. Without them, the [Global Settings](settings.md) decide; three
more variables, for installs made with a script and Docker Compose, create the
[initial administrator](#initial-admin) of a new instance.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` | _not set_ | Who may create an account: `open` (anyone), `invite` (only with an invitation link) or `disabled` (nobody). Not set: the **Registration** setting decides. |
| `LIBREFOLIO_MAX_USERS` | _not set_ (no limit) | The most accounts the instance may hold: a whole number, at least `1`; any other value (`0`, `abc`, `-3`, `1.5`) stops the server at startup. See [When the Instance Is Full](#user-limit). |
| `LIBREFOLIO_DEFAULT_LANGUAGE` | _not set_ | The language of the accounts that have not chosen one, and of the emails to people who have no account yet: `en`, `it`, `fr` or `es`. Not set: the **Default Language** setting decides; on a new instance, English. |
| `LIBREFOLIO_DEFAULT_CURRENCY` | _not set_ | The currency new accounts start with: an ISO 4217 code that LibreFolio knows, such as `EUR`, `USD` or `CHF`. Not set: the **Default Currency** setting decides; on a new instance, `EUR`. |
| `LIBREFOLIO_DEFAULT_TIMEZONE` | _not set_ | The timezone of the app, the one the times of the [market data scheduler](settings.md#market-data-scheduler) are read in: an IANA name such as `Europe/Rome` or `America/New_York`. Not set: the **Timezone** setting decides; on a new instance, `UTC`. |
| `LIBREFOLIO_PUBLIC_URL` | _not set_ | The address your users open LibreFolio at, with `http://` or `https://`, such as `https://librefolio.example.com`: the start of the invitation and password-reset links, and of the links in the emails. |
| `LIBREFOLIO_LOGIN_LIMIT` | `on` | The limit on failed sign-ins: `on` or `off`, in any case, spaces around the value included. `off` for a test instance only. Any other value, `true`, `1` and `yes` included, stops the server at startup. See [Failed Sign-ins](#login-limit). |

- **`LIBREFOLIO_REGISTRATION`** — in the app: **Registration**, in the Global Settings. Not set: on a new
  instance it is **By invitation**, unless an administrator changed it; an instance upgraded from an earlier
  version keeps the mode it had. Set: this value wins, and the global setting cannot be changed from the app.
  Case and spaces around the value do not matter. Whatever the value, the first account of a new instance can be
  created from the login page, with **Register here**, and becomes the administrator
  ([Who Can Sign Up](settings.md)); with `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio creates that administrator
  directly instead ([The Initial Administrator](#initial-admin)). `open` also shows the administrators who open
  the app from an address outside the local network a warning that names this variable
  ([The Open-Registration Warning](settings.md)).
- **`LIBREFOLIO_MAX_USERS`** — active accounts count, and so does each invitation until it is used, revoked or
  expires, each account waiting for its email verification while its link is live, and the
  [initial administrator](#initial-admin) while it waits for its setup; deactivated accounts do not.
- **`LIBREFOLIO_DEFAULT_LANGUAGE`, `LIBREFOLIO_DEFAULT_CURRENCY`, `LIBREFOLIO_DEFAULT_TIMEZONE`** — in the app:
  **Default Language** and **Default Currency** of the [Global Settings](settings.md), **Timezone** of the
  scheduler's configuration. The variable holds until an administrator saves that setting for the first time;
  from that first save the administrator's value wins, even when it goes back to the default (English, `EUR`,
  `UTC`). Language and currency in any case. The server itself always works in UTC.
- **`LIBREFOLIO_PUBLIC_URL`** — who uses it:
    - the [Users](users.md) tab of Settings › Administration: the invitation and password-reset dialogs fill in
      their **Server address** field with it; without it, with the address the administrator's browser is
      using. The administrator can change it, and the browser then checks that this LibreFolio answers there;
    - the [command line](cli_tools.md): it puts it in front of the invitation and password-reset links it
      prints; without it, it prints the path only (`/invite#token=…`) and you add the address yourself;
    - the emails with a link, with no fallback to the browser's address: without it, no invitation email,
      no email with the password-reset link and no forgotten-password email
      ([Email](email.md)).

    An address that holds a user name or a password is refused: LibreFolio works as if it were not set.

**Wrong value**, two behaviours:

- **`LIBREFOLIO_REGISTRATION` and `LIBREFOLIO_PUBLIC_URL` do not stop the server**, unlike the
  [main options](configuration.md): LibreFolio stays on the safe side and writes an error to the log the first
  time each server process needs the value: `Invalid account configuration`, with the variable and its value
  in `problem` (an address that holds an `@` is not shown: it may carry a user name or a password) and in
  `consequence` what it costs until you fix it:

    | Wrong value | What LibreFolio does | `consequence` in the log |
    | --- | --- | --- |
    | `LIBREFOLIO_REGISTRATION` other than the three modes | Registration is closed and the global setting stays locked | `registration stays closed until it is fixed` |
    | `LIBREFOLIO_PUBLIC_URL` without `http://` or `https://`, or with a user name or a password | Ignored, as if it were not set: the [command line](cli_tools.md) prints the path only and says why under each link; the dialogs of the [Users](users.md) tab start from the browser's address; no email with a link and, while email works, the start log has a [warning](configuration_security.md#startup-checks) too ([Email](email.md)) | `links show the bare path until it is fixed` |

- **The other five stop the server at startup** with a value other than those allowed in the table above
  (as an unusable value of the [initial administrator](#initial-admin) does). The error is in the server's
  console output (`docker compose logs librefolio` with Docker) and names the variable and the value:
  `LIBREFOLIO_LOGIN_LIMIT='yes': expected on or off`,
  `LIBREFOLIO_MAX_USERS='abc': expected a whole number of at least 1`.

Fix the value, then restart LibreFolio. With Docker Compose, run `docker compose up -d`.

### 📏 When the Instance Is Full {: #user-limit }

When the active accounts, the pending invitations, the accounts waiting for their email verification and an
[initial administrator](#initial-admin) waiting for its setup reach `LIBREFOLIO_MAX_USERS`:

- nobody can sign up without an invitation, whatever the [Registration](settings.md) mode;
- an invitation link already sent still works: its place was counted when it was created;
- administrators cannot create invitations or reactivate accounts, except from the
  [command line](cli_tools.md): `user create`, `user invite` and `user activate` print a warning,
  then go ahead. `user activate` prints none for an account that already holds its place: one
  waiting for its email verification while its link is live, or the initial administrator waiting
  for its setup.

A place frees up when an account is deactivated or deleted, when an invitation is revoked or
expires, or when the link of an account waiting for its email verification expires (see
*Email Verification* in [Email](email.md)). The first account of a new instance can always be
created.

### 📉 When the Plan Gets Smaller {: #user-limit-over }

If the **active** accounts outnumber `LIBREFOLIO_MAX_USERS` — you lowered the limit and restarted, or you
restored a backup with more users than the limit allows — the instance is *over the limit*. LibreFolio
does not delete anybody: it asks an administrator to choose.

- **Who is concerned**: only `active > limit`. With exactly as many active accounts as the limit, nothing
  happens. Invitations and accounts waiting for their verification take places but never start this state.
- **What everybody else sees** until the choice is made: a message that an administrator has to choose who
  keeps the access. Nobody but an administrator enters, and the administrators see nothing but this
  choice.
- **A limit LibreFolio cannot read** (`LIBREFOLIO_MAX_USERS=abc`, `0`) never starts this state: the server
  does not start until you fix the value, so a typo cannot lock everybody out.

**Where**: in the app, as an administrator.

1. Sign in. Before any other page, the list of the active accounts appears: you are checked and cannot be
   unchecked; each row says how many brokers the account owns **alone** (those brokers stay, but nobody else
   can reach them until the account is reactivated); a counter shows how many accounts are chosen against
   how many the limit allows.
2. First of all, make the full backup: the same page offers it, so the data can be taken away before anybody
   is deactivated.
3. Choose who keeps the access, then **Deactivate the others and continue**. The page says how many
   invitations it will cancel before you confirm.

   Result: the accounts not chosen are **deactivated**, not deleted: they are signed out, cannot sign in and
   keep all their data; you can reactivate one when a place frees up
   ([When the Instance Is Full](#user-limit)). Pending invitations are cancelled, newest first, only as far
   as the chosen accounts need their places.

No special step is needed after a restore: the restored accounts are counted the same way.

### 🚦 Failed Sign-ins {: #login-limit }

When sign-ins keep failing, LibreFolio stops checking passwords for a while: nobody can try password after
password until one works. The limit is on unless you turn it off.

| Limit | Past it |
| --- | --- |
| 10 failed sign-ins every 15 minutes with the same username or email address, whether an account has it or not | Every sign-in with that username or email address is refused, the right password included, until the oldest failure is 15 minutes old. |
| 50 failed sign-ins every 15 minutes from the same address, whatever username or email address they use; an IPv6 address counts by its /64, the block one subscriber usually holds. Not counted are the sign-ins that come through a proxy LibreFolio does not trust, on a local address: see *Behind a reverse proxy* below | Every sign-in from that address is refused, for any account, until the oldest failure is 15 minutes old. |

**What the user sees**: the login page says *Too many login attempts: wait a few minutes and try again.*
The wait is 15 minutes at most. The answer is the same whether an account exists or not: the limit does not
reveal which accounts exist.

**What counts as a failure**:

- a wrong password, or a username or email address that no account has;
- **a wrong current password** in **Change Password**, or when a user changes their own email address in the
  Profile tab ([Profile](../user/settings/profile.md)): it counts as a failed sign-in with the account's
  username, from the same address. So 10 wrong current passwords also block signing in with that username,
  and failed sign-ins with the username block those two checks: **Change Password** and the Profile tab then
  say *Too many wrong passwords: wait a few minutes and try again.* Deleting one's own account asks for no
  password: nothing to limit there;
- **a wrong password in Send the link again**: on the login page, an account waiting for its email
  verification gets **Send the link again**, which checks the username or email address and the password as a
  sign-in does ([Email Verification](email_flows.md#verification)). It counts as a failed sign-in with what
  was typed, from the same address; past the limit, it is refused before the password is checked, and the
  page says in how many minutes to try again. The right password clears the failures of what was typed, as a
  successful sign-in does. Its own limits still apply
  ([Limits of the Verification Emails](email_flows.md#verification-limits)).

**What does not count**:

- the right password of a deactivated account, or of one still waiting for its email verification: neither a
  failure nor a success;
- a sign-in the limit refuses: it is not counted and its password is not even checked, so trying again does
  not make the wait longer;
- the invitation and password-reset links: their tokens are long random values nobody can guess, and a limit
  per address could refuse them to every user behind the same router.
  **Forgot Password?** asks for no password and has limits of its own: see
  [Forgotten Passwords](email_flows.md#forgot-password).

**How they are counted**:

- **a successful sign-in** clears the failures of the username or email address it used, not those of the
  address it came from;
- **the username and the email address count apart**, even for one account: someone guessing its password
  gets 10 tries with the username and 10 with the email address every 15 minutes, still within the 50 of
  their own address. Capitals A to Z do not matter: `Alice` and `alice` share one count;
- **kept in memory**, by each server process: a restart forgets every count, which also lets a user who
  cannot wait back in at once. With several server processes (`./dev.py server --workers N`), each keeps its
  own counts, so the limits are N times these; the Docker image runs one.

**Behind a reverse proxy**, the address that counts is the visitor's, as LibreFolio reads it. Tell LibreFolio
about your proxy, by listing it in `FORWARDED_ALLOW_IPS` or by naming the header it sets in
`LIBREFOLIO_CLIENT_IP_HEADER`: where and how, in [The Visitor's Address](connection_proxy.md#client-address).
Until then, LibreFolio sees every visitor with the proxy's address, and what happens depends on where the
proxy is:

| Proxy LibreFolio does not trust | What happens |
| --- | --- |
| On a **local address** (a Docker network, your own network or your VPN), such as a proxy container in front of the Docker image, the usual setup | LibreFolio leaves the sign-ins through it out of the limit per address, so that 50 failed sign-ins from anyone cannot refuse every sign-in. The limit per username or email address still counts them. The log has one warning per server process, the first time a request through such a proxy meets a limit per address: `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER` |
| On a **public address**, such as a CDN | Every visitor shares the proxy's address and its count: 50 failed sign-ins from anyone refuse every sign-in through the proxy, the right passwords included, for up to 15 minutes |

**Turning it off**, for a test instance only, whose automated tests sign in wrongly on purpose:
anyone can then try passwords without pause.

**Where**: in LibreFolio's `.env`.

1. Add the line (case does not matter):

    ```env
    LIBREFOLIO_LOGIN_LIMIT=off
    ```

2. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

    Nothing is counted any more and nothing is refused. Every start logs a
    [warning](configuration_security.md#startup-checks), with `accounts.login_limit` in `check`:
    `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance`.
    The same check, on demand, is in the **Security** tab of **Settings › Administration**: a warning,
    counted in the number on the tab, until the limit is back on («Security» in
    [Global Settings](settings.md)).

3. To turn the limit back on, remove the variable or set it to `on`, then restart: it holds from the next start.
   Any other value stops the server at startup ([Accounts and Sign-ups](#accounts)).

### 👑 The Initial Administrator {: #initial-admin }

LibreFolio can create the administrator of a new instance by itself, at its first start, for the address you
give it: nobody can register first and take its place. It is meant for installs made with a script or Docker
Compose. Without these variables nothing changes, and the first account registered becomes the administrator
([Who Can Sign Up](settings.md)).

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | _not set_ | The email address of the administrator. Setting it turns the initial administrator on. |
| `LIBREFOLIO_ADMIN_USERNAME` | `admin` | The administrator's username: 3 to 50 characters, without `@`, as at registration. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | _not set_ | Optional: the token of the setup link, for a script that delivers the link itself. 32 to 200 characters, only letters, digits and `-` `.` `_` `~`, since it travels in a link: the output of `openssl rand -hex 32`, for example. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` reads it from a file instead: see [Secrets](configuration_secrets.md#secrets). Not set: LibreFolio generates the token. |

An empty value counts as not set. Spaces around the email and the username do not matter; the token is used
exactly as written, so a space in it, even at the end, makes it unusable.

**Where**: in LibreFolio's `.env`, before the instance's first start.

1. Set the administrator's address; the username and the token only if you do not want the generated ones:

    ```env
    LIBREFOLIO_ADMIN_EMAIL=admin@example.com
    # LIBREFOLIO_ADMIN_USERNAME=admin
    # LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN=
    ```

2. Start LibreFolio. At the first start of an instance **without any account**, LibreFolio:

    1. creates the administrator, not yet active, with a random password nobody knows: nobody can sign in
       with it yet;
    2. sets the **Registration** [global setting](settings.md) to **By invitation**; `LIBREFOLIO_REGISTRATION`,
       when set, still decides;
    3. issues a **setup link**, `/setup#token=…`, that works once, for 72 hours.

3. Hand the link over to the administrator. Who hands it over depends on the token:

    - **With `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`**, whoever chose it: the link is the instance's address followed
      by `/setup#token=` and the token. LibreFolio neither logs it nor emails it.
    - **Without it**, LibreFolio generates the token and hands the link over itself:
        - it writes the link **once** in its log, as a warning:
          `Setup link of the initial administrator, single use: open it to choose the password`, with the link in
          `link` (with Docker: `docker compose logs librefolio`). The link is the full address when
          `LIBREFOLIO_PUBLIC_URL` is set; otherwise it is the path, and `note` asks you to put the address of
          your server in front of it;
        - it emails the link to `LIBREFOLIO_ADMIN_EMAIL` when email works, that is with an SMTP server set up
          ([Email](email.md)) and `LIBREFOLIO_PUBLIC_URL` set. The email is in the instance's default language
          and goes out once the server is up, so a slow mail server never delays the start. If it cannot be
          sent, the log has
          `Setup link of the initial administrator not emailed`, with the reason, and the link in the log still works.

4. The administrator opens the link: the instance's setup page, where they choose the password and sign in.
   From then on the variables create nothing more: each start logs
   `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`, as on an instance that already has accounts
   and no administrator waiting.

**While the administrator waits**: nobody can register as the first account, and the administrator takes a
place of `LIBREFOLIO_MAX_USERS`. A restart issues nothing new and does not write the link in the log again.

**When no link works any more**, each start logs a warning:

| Warning in the log | When |
| --- | --- |
| `The initial administrator's setup link has expired: run ./dev.py user setup-link…` | The link has expired |
| `The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link…` | The link was [cancelled](users.md#cancel-setup) or the administrator's address changed |

That command prints a new link ([A New Setup Link](cli_tools.md)). A new value of
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` also gives a new link, at the next start.

**Unusable value**: **stops the server at startup**, on any instance, one that already has accounts included:

- `LIBREFOLIO_ADMIN_USERNAME` or `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` set without `LIBREFOLIO_ADMIN_EMAIL`;
- an email that is not an address;
- a username shorter than 3 or longer than 50 characters, or with an `@` in it: the sign-in reads a name with
  `@` as an email address, and the administrator signs in with the address of `LIBREFOLIO_ADMIN_EMAIL` anyway;
- a token shorter than 32 or longer than 200 characters, or with a character other than letters, digits and `-` `.` `_`
  `~`, a space included;
- a `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` that cannot give the token
  ([Secrets in Files](configuration_secrets.md#secret-files)).

The error is in the server's console output (`docker compose logs librefolio` with Docker): it names the
variable, never the token. Fix the value, then start again.

---

## 🥇 The Order of the Price Providers in the Search {: #provider-order }

When you create an asset, the search asks every price provider at once and lists the results provider by
provider. Each provider declares its tier, **premium** (a source an instance vouches for, such as licensed
data) or **community** (the default), and its priority inside the tier. The results of the premium providers
come first. None of the providers shipped with LibreFolio is premium, so without one the search keeps its order.

**Where**: in LibreFolio's `.env`. No restart: LibreFolio reads them at every search, and they apply to the next
search.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` | _not set_ | The providers to count as premium, by code, separated by commas, such as `yfinance,justetf`: exactly these, whatever they declare. Not set: what each provider declares. |
| `LIBREFOLIO_ASSET_PROVIDERS_ORDER` | _not set_ | The providers to list first, in this order, by code, separated by commas; the others follow in their declared order. Premium providers still come before the others. Not set: what each provider declares. |

- The codes of the providers shipped with LibreFolio are `yfinance`, `justetf`, `borsa_italiana`, `css_scraper` and
  `scheduled_investment`; a provider you add has its own. Case and spaces around the codes do not
  matter.
- A code that no provider has is ignored, and the server logs it once.

---

## 🔎 Optional: Web Search for New Assets {: #optional-web-search-for-new-assets }

When you create an asset, also from the broker import wizard, and a provider's own search finds nothing,
LibreFolio can find the asset's page with a web search through the
[`ddgs`](https://pypi.org/project/ddgs/) library. It is on by default and never used for price
updates.

**Where**: in LibreFolio's `.env`: uncomment a line of `.env.example` to change one. All optional. Then restart
LibreFolio. With Docker Compose, run `docker compose up -d`.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` turns the web search off; the providers' own search keeps working. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` needs no setup. `apikey` is reserved for a paid search service and returns no results yet. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Search region. `wt-wt` (worldwide) keeps national sites such as Borsa Italiana from being pushed down. Examples: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Engines that `ddgs` queries: `auto` rotates them for the widest coverage; a list such as `google,bing,duckduckgo` gives steadier results. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Time limit of one search, in seconds: at least `1`. Any other value means the default. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Most links returned by one search: a whole number, at least `1`. Any other value means the default. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _empty_ | Key for the `apikey` engine. `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` reads it from a file instead: see [Secrets](configuration_secrets.md#secrets). |

??? tip "🔁 Results change between attempts — when a known asset is sometimes not found"

    With `auto`, each search may reach different engines, so the same query can do better or worse
    from one try to the next. Retry once, or set
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔗 Related

- 📄 **[Configuration](configuration.md)** — Create the `.env` File, Main Options, Parameters Set by the Tools, …
- 📄 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)** — Secrets, Plugin Settings
- 📄 **[Configuration: Checks and Protections](configuration_security.md)** — Startup Checks, Browser Protections, Stopping the Server
