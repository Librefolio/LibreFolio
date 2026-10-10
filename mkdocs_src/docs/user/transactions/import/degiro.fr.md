# 📥 <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

LibreFolio importe le **Relevé de compte** de DEGIRO : le CSV qui enregistre chaque mouvement de votre compte — transactions, frais, dividendes, intérêts, dépôts, retraits et conversions de devise — dans n'importe quelle langue proposée par DEGIRO.

## 📥 Comment exporter

1. Connectez-vous au [Portail client DEGIRO](https://www.degiro.eu).
2. Ouvrez **Boîte de réception** dans la barre latérale gauche, puis **Relevé de compte**.
3. Choisissez la **Date de début** et la **Date de fin** : de votre premier dépôt à aujourd'hui pour l'historique complet.
4. Cliquez sur **Exporter**, choisissez **CSV** et enregistrez le fichier (généralement `Account.csv`).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Pièges courants

!!! warning "Relevé de compte, pas Transactions"

    L'export **Transactions** de DEGIRO ne liste que vos ordres : pas de dividendes, de dépôts, de retraits ou de conversions de devise. Si vous le téléversez, LibreFolio le reconnaît, n'importe rien et vous demande le Relevé de compte.

- **Conservez le fichier tel qu'exporté.** Toute langue fonctionne, tant que vous n'ajoutez, ne supprimez ni ne réorganisez les colonnes, et que vous ne modifiez pas les dates jour-mois-année de DEGIRO.
- **Avertissements dans la langue du fichier.** Les avertissements d'import sont dans la langue du relevé, quelle que soit la langue utilisée par LibreFolio : anglais, néerlandais, allemand, français ou espagnol, et anglais pour toute autre langue.

## 🔄 Ce qui est importé

| Dans le relevé | Importé en tant que |
|:-----------------|:------------|
| Achats et ventes, comme `Buy 5 APPLE INC@180,25 USD`, dans n'importe quelle langue | **Achat** ou **Vente** : le signe du montant donne le sens, la description donne la quantité |
| Frais d'ordre (`DEGIRO Transaction and/or third party fees`) et frais de connexion à la bourse | **Frais** |
| Droit de timbre et impôts sur les transactions financières sur un ordre | **Impôt** |
| Dividendes et leur retenue à la source (`Dividend`, `Dividend Tax`) | **Dividende** et **Impôt**, chacun dans sa propre devise |
| Dépôts et retraits | **Dépôt** et **Retrait** |
| Intérêts (`Flatex Interest Income`) | **Intérêt** ; les intérêts qui vous sont facturés deviennent des **Frais** |
| Crédits promotionnels et de courtoisie (`DEGIRO courtesy`) | **Intérêt**, en conservant la description de DEGIRO |
| Conversions de devise (`FX Debit` et `FX Credit`) | Une paire liée de **conversions FX** (voir ci-dessous) |

Les montants sont importés tels que DEGIRO les rapporte, chacun dans la devise de sa propre ligne.

### 💱 Conversions de devise

DEGIRO enregistre une conversion en deux lignes : l'argent quittant une devise et l'argent arrivant dans l'autre. LibreFolio les importe comme une paire liée : dans l'assistant d'importation, à l'étape [Récapitulatif](how-to.md#review), il s'agit d'une seule ligne affichant **De**, **Vers** et le taux que les deux montants impliquent, sélectionnée et importée en entier. Elle compte comme deux transactions dans **Importer N transactions**. Le coût AutoFX de DEGIRO est déjà inclus dans le montant débité, donc aucun frais séparé n'est ajouté.

## 🚫 Ce qui n'est pas importé

Chaque type ci-dessous est listé dans un avertissement lors de l'import, avec ses lignes d'origine, afin que vous puissiez les vérifier :

- **Opérations sur titres** (changements de produit ou d'ISIN, divisions, fusions, dividendes en actions et leurs règlements en espèces), lignes de **fonds monétaires** et **remboursements de capital** : LibreFolio ne les importe pas automatiquement — vérifiez les positions concernées.
- **Lignes de retrait flatex** (`flatex Withdrawal`) : LibreFolio ne peut pas déterminer si l'argent a réellement quitté votre compte. Si c'est le cas, ajoutez le retrait manuellement.
- **Lignes de conversion de devise sans contrepartie** : l'autre jambe est absente du fichier ou ne peut pas être identifiée.
- **Lignes avec un signe inattendu** pour leur type, comme un dividende négatif.
- **Transactions dont la quantité ne peut pas être lue** à partir de la description.
- **Lignes non reconnues** : tout autre élément que LibreFolio n'a pas pu classer.

Ignorées sans avertissement : les lignes d'information sans montant, les écritures internes de DEGIRO (balayages de trésorerie, transferts vers ou depuis flatexDEGIRO Bank, réservations) et les lignes à montant nul qui ne nomment aucun produit, comme un intérêt nul.

## 🔗 Référence développeur

→ [Architecture BRIM — notes DEGIRO](../../../developer/backend/brim/architecture.md#plugin-degiro)
