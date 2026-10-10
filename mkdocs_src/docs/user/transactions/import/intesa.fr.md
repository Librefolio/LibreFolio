# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Bêta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas limites peuvent subsister.

LibreFolio lit deux exports Intesa Sanpaolo, au format **CSV** ou **Excel (XLSX)**, tels que vous les téléchargez :

- la **liste des mouvements** — les coupons, dividendes, frais et impôts d'une période ;
- l'**instantané de portefeuille** (*patrimonio*) — vos positions à leur coût fiscal, et votre solde de trésorerie.

## 🧭 Quels fichiers dois-je importer ?

=== "Compte nouvellement ouvert"

    Importez la **liste des mouvements** : elle apporte les coupons, dividendes, frais et impôts.
    LibreFolio n'en tire aucun achat ni vente, ajoutez donc vos achats à la main avec le
    [formulaire de transaction](../form.md), ou avec un fichier [Generic CSV](generic-csv.md).

=== "Compte avec historique (recommandé)"

    Intesa exporte environ **un an** de mouvements, et LibreFolio n'en tire aucun achat ni vente.
    Partez plutôt de l'instantané de portefeuille :

    1. Importez l'**instantané de portefeuille**. Il ajoute un **Dépôt** pour votre solde de
       trésorerie et un **Ajustement** par position, à son coût fiscal, tous à la date de
       l'instantané : la date de cotation la plus récente du rapport.
    2. Réglez la date d'**Ouverture du compte** du courtier à la date de l'instantané. Les mouvements plus anciens
       sont déjà comptés dans l'instantané : l'assistant d'importation les marque **Avant l'ouverture** et les
       laisse de côté ([comment ça marche](how-to.md#opening-date)).
    3. À partir de là, importez la **liste des mouvements** pour les nouveaux coupons, dividendes,
       frais et impôts.

## 📥 Comment exporter

### 🔍 Étape 1 — Ouvrir la recherche avancée

Sur la page d'accueil de votre banque en ligne, cliquez sur **RICERCA AVANZATA**, à côté d'**Ultime Operazioni**.

![Intesa Sanpaolo — page d'accueil, RICERCA AVANZATA à côté d'Ultime Operazioni](../../../static/broker-guides/IntesaSanPaolo/01_ISP_RicercaAvanzata.jpg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Étape 2 — Filtrer et télécharger les mouvements

Réglez **Tipologia Operazione** sur **Operazioni titoli**, choisissez la période dans **Da** et **A**, cliquez sur **APPLICA**, puis sur **SCARICA EXCEL**.

![Intesa Sanpaolo — Tipologia Operazione réglée sur Operazioni titoli, période, APPLICA et SCARICA EXCEL](../../../static/broker-guides/IntesaSanPaolo/02_ISP_FiltraExport.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 📊 Étape 3 — Télécharger l'instantané de portefeuille

Pour un compte avec historique, ouvrez **Patrimonio** depuis la page d'accueil et téléchargez les positions de votre *Deposito Amministrato*.

## 🔄 Ce qui est importé

| Dans la liste des mouvements (**Operazione**) | Importé en tant que |
|:---------------------------------------|:------------|
| *Cedole* (coupons) | **Intérêt**, lié au titre nommé dans **Dettagli** |
| *Dividend…* | **Dividende**, lié de la même façon |
| *Commission…* | **Frais** |
| *Ritenut…*, *Imposta…*, *Bollo…* | **Impôt** |

Toute autre opération — y compris les achats, les ventes et les lignes bancaires du quotidien telles que les paiements par carte ou les virements — est ignorée avec un avertissement : l'import n'échoue jamais à cause de cela.

Depuis l'**instantané de portefeuille** : un **Ajustement** par position (sa quantité, à son coût fiscal) et un **Dépôt** pour le solde de trésorerie lorsqu'il n'est pas nul, le tout à la date de l'instantané.

## ⚠️ Bon à savoir

- **Filtrez sur Operazioni titoli.** Sans ce filtre, chaque paiement par carte ou virement de la
  période apparaît dans les avertissements comme une ligne ignorée.
- **Le même titre, deux noms.** La liste des mouvements ne nomme un titre qu'en texte libre, tandis
  que l'instantané donne son ISIN. Associez les deux au même actif dans le panneau **Resolve Assets**
  de [Review](how-to.md#review).
- **Montants tels quels.** Les mouvements conservent la devise de leur colonne **Valuta**, et
  l'instantané est en euros : rien n'est converti.
- **Messages en italien.** Les avertissements d'import sont en italien, comme le rapport.

## 🔗 Référence développeur

→ [BRIM Architecture — notes Intesa Sanpaolo](../../../developer/backend/brim/architecture.md#plugin-intesa)
