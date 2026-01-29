Note migliorative da fare ma alla fine:

1. ✅ COMPLETATO (14-01-2026): Quando si cambia pw o si crea un utente, aggiungere un componente che indica il livello di sicurezza della pw, e quando non si rispettano i parametri,
   far comparire una nuvoletta che evidenza le regole rispettate e quelle mancanti.
    - Creato `PasswordStrength.svelte` con zxcvbn-ts
    - Aggiunto a RegisterModal e ProfileTab (cambio password)
    - Traduzioni in EN/IT/FR/ES

2. ✅ COMPLETATO (16-01-2026): Attuare a backend la lettura dei vari global settings per renderli efficaci, con dei metodi utility così che le varie aree di codice non debbano
   accedere direttamente al DB
    - Creato `backend/app/services/global_settings_service.py`
    - Funzioni: `get_session_ttl_hours()`, `get_max_upload_mb()`, `is_registration_enabled()`, `get_setting_value()`
    - Lettura diretta da DB (no cache per consistenza multi-worker)
    - Integrato in auth.py per TTL sessioni dinamico

3. ✅ COMPLETATO (19-01-2026): Creare il tema chiaro e il tema scuro, copiando lo stile della documentazione, e magari mettendo un sole e una nuvola in un bottone tra il selettore
   lingua e l'help
    - Creato `ThemeToggle.svelte` con Sun/Moon icons
    - CSS variables per light/dark in `app.css`
    - Salva preferenza in localStorage
    - Rispetta `prefers-color-scheme` come default
    - Aggiunto all'header e alla pagina login

4. ✅ COMPLETATO (19-01-2026): Modificare la pagina delle preferenze dell'utente normale per renderla come quella delle impostazioni globali, con un selettore verticale del "
   capitolo" e una parte destra con le varie voci, che alla loro modifica mostrano salva, annulla e ripristina, e sopra ci siano salva tutto, modifica tutto e ripristina tutto (
   come nel global)
    - Riscritto `PreferencesTab.svelte` con layout a due colonne
    - Categorie: Display, Currency, Appearance (+ All)
    - Pulsanti bulk: Save All, Undo All, Reset All
    - Pulsanti singoli: Save, Undo, Reset per ogni campo
    - Integrato FuzzySelect per valuta predefinita
    - Tema ora salvabile e sincronizzato con ThemeToggle

5. ✅ COMPLETATO (19-01-2026): nell'icona della valuta nel cerca, rendere il background più grande e gradevole
    - Aumentata dimensione icona a 9x9 con bg-libre-green/20
    - Font-medium per miglior leggibilità
    - Applicato sia nel trigger che nella dropdown list

6. ✅ COMPLETATO (18-01-2026): gli strumenti di rendering grafici come mermaid o flow della documentazioni, vengono caricati molto lentamente dal browser. Sarebbe preferibile
   cashare la versione in locale, e solo come fallback andare a prendere quella remota, così da vincolare anche la versione di pacchetto.
    - Creato `scripts/update_js_cache.py` per gestione cache
    - Directory `vendor/` per librerie cachate (in .gitignore)
    - Cache aggiornata automaticamente all'avvio server
    - Mantiene ultime 4 versioni, elimina vecchie
    - Rimosso polyfill.io (deprecato, non necessario per browser moderni)

7. 🔲 aggiornare la documentazione nelle parti "per tutti/base" e scriverle in tutte le lingue del frontend

8. ✅ COMPLETATO (14-01-2026): Primo utente registrato diventa automaticamente admin (is_superuser=True)

9. ✅ COMPLETATO (14-01-2026): Messaggi di errore migliorati per registrazione (es. dominio email non valido)

10. ✅ COMPLETATO (17-01-2026): Sistema upload risorse statiche
    - Creato `backend/app/services/static_uploads.py`
    - Storage in `backend/data/custom-uploads/` con metadata JSON
    - Endpoints: POST/GET/DELETE `/api/v1/uploads`, GET `/api/v1/uploads/file/{id}`
    - Creata pagina `frontend/src/routes/(app)/files/+page.svelte` con due tab:
        - "Risorse Statiche": custom-uploads
        - "Report Broker": broker_reports
    - Componenti UI: `LazyImage.svelte`, `ImageUploader.svelte` (con resize client-side), `Tooltip.svelte`
    - Static assets per plugin con `generate_static_url()` in tutte le classi base provider

11. 🔲 Creare nei settings, un altro tab "plugins", anche lui con un selettore verticale a sinistra tra i vari sotto sistemi (brim, fx, asset per ora) e che una volta selezionato
    mostri varie card per i vari plugin con le info del caso, icone, ed eventuali url per maggiori info o crediti. I vari plugin devono esporre da API le stringhe da mostrare nei
    vari campi, e lo devono fare nativamente multilingua, in caso una lingua manchi si fa fallback sull'inglese, e se anche lui manca, una a caso tra quelle implementate, la prima
    direi)

12. ✅ COMPLETATO (18-01-2026): Migrazione dev.sh → dev.py
    - Creato `dev.py` come entry point principale
    - Subparser automatico per ogni tool in `scripts/`
    - Autocompletamento bash/zsh con `scripts/dev_completion.bash`
    - TreeParser personalizzato per help gerarchico
    - Test runner, user_cli spostati in `scripts/`
    - Singola fonte di verità con utilities condivise in `cli_base.py`

13. ✅ COMPLETATO (17-01-2026): Sistema multi-utente broker/transazioni
    - Enum `UserRole` con OWNER > EDITOR > VIEWER
    - `BrokerUserAccess` con CHECK constraint su role
    - Auto-create OWNER al create broker
    - Parametro `as_user_id` per superuser
    - API gestione accessi: GET/POST/PATCH/DELETE `/brokers/{id}/access`
    - ~160 test API backend passano

14. ✅ COMPLETATO (19-01-2026): Licenza AGPLv3
    - Aggiunto file LICENSE
    - Aggiornato README con sezione licenza e link al repo GitHub
    - Aggiornato AboutTab con info licenza (link cliccabile)
    - **Nota**: Header nei file sorgente non obbligatorio per AGPL, ma consigliato.
      Può essere aggiunto incrementalmente in futuro con uno script automatico.

---

## 🐛 Bug/Fix Segnalati (19-01-2026) - Aggiornato 20-01-2026

### Alta Priorità

1. ✅ RISOLTO: **Dark mode incompleto**: Lo sfondo non cambia, sidebar e icone illeggibili/fosforescenti
    - Fix: Aggiunto CSS variables con override più specifici in app.css
    - Fix: Layout principale con classi esplicite dark:bg-slate-900
    - Fix: Supporto dark mode in BrokerForm, BrokerModal, BrokerCard
    - Fix: LanguageSelector dark mode (rimosso bg-white/80, ora uniforme)
    - Fix: Files page completo supporto dark mode

2. ✅ RISOLTO: **BrokerModal footer non sticky**: Annulla/Crea ancora in fondo e non in sovra impressione
    - Fix: Ristrutturato modale con flex column
    - Fix: Bottoni ora fuori dal form con sticky bottom
    - Fix: Aggiunto padding e margin negativo per eliminare gap sotto footer

3. 🔲 **PreferencesTab vs GlobalSettingsTab**: Strutture troppo diverse
    - Fix parziale: Card ora usano bg-gray-50 come GlobalSettingsTab
    - TODO: Creare componenti condivisi (vedi `plan-settings-unification.md`)

4. ✅ RISOLTO: **Files page API calls e UI migliorata**:
    - Fix: Corrette chiamate API (api.get ritorna dati, non Response)
    - Fix: Conflitto nome `File` (icona) vs `File` (tipo nativo) risolto
    - Fix: Aggiunto toggle vista griglia/lista per static files
    - Fix: Tabella BRIM con colonne uniformi e wrapper per scroll
    - Fix: Icone specifiche per tipo file (CSV=FileSpreadsheet, etc.)
    - Fix: Endpoint download file BRIM aggiunto al backend

5. ✅ RISOLTO: **Broker detail/form icon**: Icona broker con fallback Briefcase
    - Fix: Aggiunto icon_url all'interfaccia BrokerSummary
    - Fix: Mostrata icona con LazyImage o fallback Briefcase
    - Fix: BrokerForm preview icona sempre visibile, con gestione errore URL

6. ✅ RISOLTO: **Plugin BRIM ordinamento**: "GenericCSV" ora in cima alla lista con "(default)"
    - Fix: Sorting in BrokerForm.svelte con GenericCSV sempre primo

### Media Priorità

7. ✅ RISOLTO: **Tooltip leva/short**: Troppo stretto, dovrebbe essere più largo
    - Fix: Aumentato maxWidth a 320px

8. 🔲 **BrokerCard favicon**: Non si vede il loading placeholder
    - TODO: Verificare LazyImage funzioni correttamente

### Bassa Priorità

9. ✅ RISOLTO: **i18n audit tool**:
    - Fix: Default ora è --format none che mostra solo warning
    - Fix: Tabulate usato per formattare le tabelle degli errori
    - Fix: Refactoring con add_arguments() e run_from_args() per riutilizzo

10. ✅ RISOLTO: **user_cli reset password**: Deve validare password con stesse regole frontend
    - Fix: Aggiunta funzione validate_password() con stesse regole del frontend

11. ✅ RISOLTO: **Traduzioni mancanti FR/ES**: 12 chiavi mancanti per common.* e settings.*
    - Fix: Aggiunte tutte le chiavi mancanti

12. ✅ RISOLTO: **BrokerForm initial balance proportions**: Cambiato da 70%/30% a 60%/40%
    - Fix: flex-[7]/flex-[3] → flex-[6]/flex-[4]

13. ✅ RISOLTO: **broker_service.py update_bulk**: Mancava supporto per icon_url, default_import_plugin, is_active, opened_at
    - Fix: Aggiunti campi in update_bulk() righe ~477-490

---

## 🔲 DA FARE

### Alta Priorità

1. 🔲 **Multi-utenza BRIM files**: Backend non filtra per utente
    - TODO: Aggiungere user_id a metadata file BRIM
    - TODO: Aggiungere filtro per superuser (as_user_id=all)
    - TODO: Selettore utente in UI Files page per superuser

2. 🔲 **Tabella avanzata con sorting/filtering/selezione**:
    - TODO: Valutare librerie (tanstack-table, svelte-simple-datatables)
    - TODO: Aggiungere ordinamento colonne cliccabili
    - TODO: Aggiungere filtri per colonna
    - TODO: Checkbox selezione multipla + azioni bulk (delete, download)
    - TODO: Applicare sia a Static files che a BRIM files

3. 🔲 **Vista griglia per BRIM files**: Come già fatto per Static files
    - TODO: Replicare toggle griglia/lista
    - TODO: Card view per BRIM files

4. 🔲 **Unificazione PreferencesTab/GlobalSettingsTab**:
    - Piano scritto in: `plan-settings-unification.md`
    - TODO: Review piano, poi implementare componenti condivisi

### Media Priorità

5. 🔲 **Preview file testuali**: Poter cliccare su file e vedere anteprima contenuto
    - TODO: Modal preview con contenuto file (primi N caratteri)

6. 🔲 **Plugin Settings Tab**: Mostrare info sui plugin (brim, fx, asset)
    - TODO: API backend per esporre info plugin multilingua
    - TODO: UI con card per ogni plugin con icone e link

7. 🔲 **Documentazione multilingua**: Scrivere docs in tutte le lingue frontend

