# 🧩 Plugin Settings

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="plugins" alt="Plugin Settings">
</div>

The **Plugins** tab holds what the price and exchange-rate sources ask for: the API key of a paid
data source, a region, or a preference of your own. Open **Settings** (gear icon in the sidebar),
then the **Plugins** tab, after **Preferences** (on a phone, the tab with the puzzle-piece icon).
Every user has it; what you can change there depends on
[whose setting it is](#personal-and-instance). The book icon at its top opens this page.

The plugins that ask for something are listed, and so is every plugin that calls an outside service,
for its [Calls](#calls) block: under **Prices** for the
[price providers](../assets/providers/index.md) and **Exchange rates** for the
[exchange-rate providers](../fx/providers/index.md), each heading after its family's icon (a column
chart for prices, coins for exchange rates); a heading with no such plugin is left out. Of
the plugins shipped with LibreFolio, **JustETF** and **Borsa Italiana** have a personal search preference each
(see [Search Preferences](#search-preferences)); the others that call an outside service, such as **Yahoo Finance**
and the central banks of the exchange rates, show their **Calls** block alone. A plugin added
to your installation may ask for more. The tab also has a **Tools** group, for the [Tools](../tools/index.md) that have settings of their own; none of them does yet, so you will not see it today. When no plugin asks for anything, the tab says *No installed
plugin asks for settings.*

## 🧭 The Menu {: #menu }

On the left of the tab, as in **Global Settings**, a menu chooses what the page shows:

- **All**, every plugin once, under its family (the shared settings cards are not repeated here: they are under **Shared**, and a plugin that reads one links to it);
- **To configure**, only the plugins that still miss something (it appears when one does);
- one family: **Prices**, **FX rates**, **Imports** (the broker import plugins, with the Transactions icon), **Tools**,
  **Asset profile** and **Shared** (a settings card several plugins share, such as the
  [CoinGecko account](coingecko-key.md)).

Each entry shows how many plugins it holds; an amber dot marks a family with a plugin to configure. On a phone the
menu is the **Category** list above the page. **Open** on a plugin's shared settings row shows them even when the menu
hides them.

### 🔎 Search {: #search }

The **Search plugins or settings** field above the cards keeps the cards that hold **every word** you type, in any of
their texts: the plugin's name and code, its description, and the names and descriptions of its settings, in the
language of the page. Capitals and accents do not matter; the words must be written as they are (*gecko*, not *geko*).
Numbers are never searched: a count or a limit is not a word.

- *swiss* finds the **Swiss National Bank**, whose description says so (*svizzera* in Italian);
- *gecko daily limit* finds only the **CoinGecko** account card: the CoinGecko price plugin has no limit of its own.

The menu's numbers follow the search, and its entries stay (with 0). When nothing matches, the page says so; within a
choice of the menu, a link searches every family.

The page's address keeps the choice and the search, as in `…/settings/plugins?family=fx&q=swiss`: you can bookmark it or
send it, and **Back** returns to the previous choice. The link of the *to configure* window opens the page on its
plugin.

## 🧾 One Plugin, One Form {: #form }

Each plugin has a form of its own: its icon and name (a puzzle piece when the plugin has no icon), a
[badge](#configured) that says whether it can work, then its settings. Each setting shows its name,
a red **\*** when it is required, whose it is — **Personal** or **Whole instance** — and what it
does.

- Change what you need, then click **Save** at the bottom of that plugin's form: each plugin is
  saved on its own. **Discard** drops the changes you have not saved.
- **Save** keeps all the changes of the plugin, or none of them: when one is refused, nothing is
  saved, and the setting at fault says why.
- Before you save, LibreFolio checks what you typed against the plugin's rules — a number, a whole
  number, a minimum or a maximum, a length, one of the options — and says under the setting what is
  wrong, such as *At least 8 characters*. **Save** stays disabled until it is fixed.
- A saved change shows in the setting itself, with no message. A plugin whose settings you cannot
  change has no buttons.

??? note "💬 When a save does not go through"

    | Message | What happened |
    |---|---|
    | *Nothing was saved: check the settings below.* | A setting was refused. Under it: *The value is not valid for this setting.*, *Only an administrator can change this setting.*, *A server variable sets it: it cannot be changed here.* or *This setting no longer exists: reload the page.* |
    | *These settings changed meanwhile: they have been reloaded, save again.* | Someone saved the same settings at the same moment: nothing of yours was saved. Check the values shown, then save again. |
    | *Secrets cannot be saved: this instance's key cannot be used (see the configuration checks).* | Nothing was saved: a secret cannot be encrypted. An administrator finds the cause in the [startup checks](../../admin/configuration_security.md#startup-checks). |
    | *The settings could not be saved.* | No answer from the server: try again. |

---

## 👥 Personal and Whole-Instance Settings {: #personal-and-instance }

Next to its name, each setting says whose it is:

| | **Personal** | **Whole instance** |
|---|---|---|
| **Its value** | Your own: every user has theirs | One for everybody on this LibreFolio |
| **Who changes it** | You | An administrator |
| **Who sees it** | You alone: not even an administrator | Everybody; the users who are not administrators see it read-only, with *Only an administrator can change it.* Of a secret, they see only whether it is set |
| **What it changes** | What LibreFolio does for you alone: your searches, and the provider checks of the asset dialog, such as **Test Configuration** | Everything the plugin does, prices and exchange rates included |

Prices, price histories and exchange rates are shared by everybody, so they never depend on one
user's choice: for them, a personal setting always takes the plugin's default.

!!! info "🛡️ For administrators"

    You change the whole-instance settings here, like everybody else changes their personal ones. A
    whole-instance setting can also be given by the server's configuration instead: see
    [Set by the Server](#set-by-the-server), and [Plugin Settings](../../admin/configuration_secrets.md#plugin-settings)
    in the administrators' manual for the variables.

---

## 🔐 Secrets {: #secrets }

Some settings are secrets, such as an API key. A secret is write-only:

- **Type it, then Save.** What you typed is sent once, then dropped from the page: from then on the
  setting shows only *Set on* with the date and time it was saved, never the secret itself — not
  even to you. The field is marked as a new password, so the browser does not fill it in with one of
  your saved passwords.
- **Replace** opens the field for a new value; **Cancel** keeps the saved one.
- **Clear** deletes the secret when you click **Save** (*It will be deleted when you save.*);
  **Undo** keeps it.

Users who are not administrators see a whole-instance secret as *Set on …* (*Set* when the
[server sets it](#set-by-the-server)) or *Not set*, and nothing else. LibreFolio keeps a saved
secret encrypted: see [Saved Secrets and the Instance Key](../../admin/configuration_secrets.md#plugin-secrets).

---

## 🔒 Set by the Server {: #set-by-the-server }

An administrator can also give a whole-instance setting through the server's configuration, with an
environment variable. The setting then shows its value read-only, a secret only as *Set*, with
:material-lock-outline: *Set by the server*: nobody can change it here, not even an administrator.
Administrators also see the name of the variable, *Set by the server variable* followed by it.

To change such a setting, an administrator changes the variable and restarts LibreFolio: see
[A Variable Locks the Setting](../../admin/configuration_secrets.md#plugin-variable-lock).

---

## ↩️ Back to the Default {: #use-the-default }

Once you have saved a value of your own in a setting you can change, **Use the default** appears
under it. It deletes the saved value when you click **Save**, and the setting goes back to the
plugin's default: *The saved value will be deleted when you save: the default applies.*, with
**Undo**. Emptying a text field that shows a saved value does the same. A secret has no default:
**Clear** deletes it ([Secrets](#secrets)).

---

## ⚠️ When a Setting Has a Problem {: #problems }

| The setting says | What happened | What to do |
|---|---|---|
| *The server variable … is invalid: the plugin stays unconfigured until it is fixed.* | The variable that sets it holds a value the setting refuses, or names a file that cannot be read. LibreFolio never falls back to a saved value or to the default. Administrators see the variable's name | An administrator fixes the variable and restarts LibreFolio |
| *The saved value is no longer valid: the default applies.* | The plugin no longer accepts the value saved earlier, after an update for example | Choose a value again and save it, or leave it: the default applies meanwhile |
| *Saved, but this instance's key cannot read it. If an administrator can put the old key back, that comes first; otherwise enter it again.* | A saved secret can no longer be read, because the instance's encryption key has changed. LibreFolio keeps it, but never uses it | If an administrator can still put the old instance key back, that comes first: a secret saved under the new key would become unreadable once the old key is back (see [Saved Secrets and the Instance Key](../../admin/configuration_secrets.md#plugin-secrets)). Otherwise, type the secret again and save it; for a whole-instance secret, an administrator does |

---

## 🚦 Configured or To Configure {: #configured }

The badge next to each plugin's name says whether it can work:

- **Configured**: every required setting has a value LibreFolio can use.
- **To configure**: a required setting has no usable value — never set, or a secret that can no
  longer be read — or a server variable that sets one of its settings is invalid.

LibreFolio does not call a plugin that is **To configure**: its prices or exchange rates are not
updated, a search says that it must be configured, and **Test Configuration** fails with ❌ *This
provider must be configured before use*. The plugins shipped with LibreFolio need no setting to
work: **JustETF** and **Borsa Italiana** are always **Configured**.

---

## 📊 Calls and Their Limits {: #calls }

Every plugin that calls an outside service has a **Calls** block in its form, after its own settings: how many calls
this LibreFolio has made to that service, and how many it may make. It has five boxes, **Minute**, **Hour**, **Day**,
**Week** and **Month**: five side by side on a wide screen, three and two where the card is narrower, one per line on
a phone. Each shows the calls of the current window and
its limit, *412 / 2,000*, or the calls alone and *No limit*.

- **Calendar windows, in UTC**: the day starts again at 00:00 UTC, the week on Monday, the month on the 1st. The
  counts are read when the page opens and after a save: reload the page to see newer ones.
- **The limits are whole-instance settings.** An administrator types a whole number in a box and clicks the form's
  **Save**; an empty box means no limit. **0** stops the plugin: no call goes out until an administrator changes it.
  The other users see the limits read-only, with *Only an administrator can change the limits.*
- **A full window** turns its box amber, and a line says when it resumes, such as *Daily limit reached: 2,000 of
  2,000. Resumes on 18 November at 00:00 UTC.* (the minute and the hour name only the time). Until then LibreFolio
  makes no call to that service, and the calls start again by themselves.
- **A limit set by the server** shows its value with a lock, and under the boxes, *Month — Set by the server*
  ([Set by the Server](#set-by-the-server)).
- **A limit variable with an invalid value** stops the plugin: the form says so at its top, in red, and the box says
  *invalid value*. The variable needs a whole number of 0 or more, or nothing: an administrator fixes it on the server.
- **An account shared by several plugins** (CoinGecko): the calls of every plugin that uses it count on the account,
  so the **Calls** block is on the account's card, under **Shared settings**. Each plugin's form says *Its calls count
  on CoinGecko: the counter and the limits are there.*, and **Open** brings that card into view.
- **A hosted service** may set the limits itself: the block then shows the counts alone, without the limits, and
  *Instance limit reached: resumes …* when a window is full.

---

## 🛠️ Configure, From an Asset {: #configure }

You do not have to leave an asset to change its provider's settings: **Configure** opens the same
form as this tab, for that one price provider, over the dialog you are in.

- **In the asset dialog** (**+ Add Asset**, or **Edit** on an asset), under **Provider Assignment**:
  when the chosen provider has settings, **Configure** sits next to its
  :material-help-circle-outline: help link — on a phone, its :material-tune: icon alone. When the
  provider cannot work yet, **To configure** shows there too. After a save the badge follows, and
  the asset you are editing is left as it was.
- **In Search Online**: when a provider must be configured before it can search, the list of
  results starts with a line *… must be configured before it can search*, naming the provider, and
  its own **Configure** button. Once you save, the search runs again. So a provider that could not
  search is never mistaken for one that found nothing.

---

## 🔎 Search Preferences: JustETF and Borsa Italiana {: #search-preferences }

Both are **Personal** settings, and both show everything until you choose otherwise. They only
choose which rows your own searches list: no price changes, and neither does an asset you already
have. No instrument disappears either: each one exists in every currency or language, so a
preference only keeps one of its rows.

| Plugin | Setting | Choices | What it changes in **Search Online** |
|---|---|---|---|
| **JustETF** | **Preferred currency** | **All currencies** (the default), 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF, 🇬🇧 GBP | With a currency, each fund appears once, in that currency. With **All currencies**, each fund appears four times, once per currency |
| **Borsa Italiana** | **Preferred language** | **Both languages** (the default), 🇮🇹 Italian, 🇬🇧 English | With a language, each instrument appears once, in that language: the one its name and details come in. With **Both languages**, Italian first, then English. Borsa Italiana's website is searched the same way whatever you choose |

Set them here, under **JustETF** and **Borsa Italiana**, or with **Configure** in the asset dialog
while that provider is chosen.

**CoinGecko** has a **Preferred currency** too, also **Personal**, but it works another way: its search always shows
each coin once, in that currency (EUR by default), and that currency becomes the price currency of an asset you create
from a result. See [CoinGecko](../assets/providers/coingecko.md#preferred-currency).

### 👑 The Crown in JustETF Results {: #crown }

👑 marks a fund's own currency, the one its NAV is computed in — not necessarily the one you trade
in. Whenever a result shows it, a line at the bottom of the list says so: *👑 the fund's own
currency*. With a preferred currency, 👑 appears only on the funds computed in that currency: with
🇪🇺 EUR, a fund computed in US dollars shows 🇪🇺 alone.

How the currency of a justETF asset works: [Pick the Currency in Search](../assets/providers/justetf.md).

---

## 🔗 Related

- 🎛️ **[User Preferences](preferences.md)** — Language, base currency, theme and guides
- ⚙️ **[Settings Overview](index.md)** — Every tab of Settings
- 📡 **[justETF](../assets/providers/justetf.md)** and 🇮🇹 **[Borsa Italiana](../assets/providers/borsa-italiana.md)** — The two providers with a search preference
- 🔑 **[Get and Set the CoinGecko Key](coingecko-key.md)** — A shared account: the key every CoinGecko plugin uses
- 🛠️ **[Plugin Settings for administrators](../../admin/configuration_secrets.md#plugin-settings)** — The server variables, the instance key and the encryption of the secrets
- 🧩 **[Plugin Settings for developers](../../developer/architecture/patterns/plugin_settings.md)** — How a plugin declares its settings
