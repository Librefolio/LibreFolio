# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

!!! info "Alpha"

    Ces importateurs sont en **Alpha** : certains types de lignes n'ont pas encore été observés dans des exports réels (voir [Limites](#limits)). Si un fichier est refusé, ou si une ligne est importée d'une manière qui semble erronée, veuillez nous le signaler dans les [issues](https://github.com/Librefolio/LibreFolio/issues) du projet.

LibreFolio importe les deux comptes de **Scalable Capital** : le **compte-titres** et le **compte rémunéré** (*Tagesgeld*, *conto deposito*). LibreFolio n'est pas affilié à Scalable Capital.

---

## 🏦 Deux comptes, deux courtiers {: #two-brokers }

Chaque compte devient un courtier à part entière dans LibreFolio, lu par son propre importateur :

| Compte Scalable | Importateur | Fichiers lus |
|:--|:--|:--|
| Compte-titres | **Scalable Capital compte-titres** | le fichier courtier de l'exportateur LibreFolio, ou le CSV de Scalable |
| Compte rémunéré | **Scalable Capital compte rémunéré** | le fichier compte rémunéré de l'exportateur LibreFolio |

Pourquoi deux courtiers ? Chaque compte possède son propre solde de trésorerie et son propre IBAN, et l'argent que vous déplacez entre eux est un **Virement**, qui relie deux courtiers. Avec deux courtiers, chaque solde peut être vérifié par rapport à l'application Scalable, et chaque virement devient une paire liée. Chaque importateur refuse le fichier de l'autre compte et indique l'importateur qui le lit.

---

## 📤 Quoi exporter

### 🧩 Recommandé : l'exportateur LibreFolio {: #exporter }

L'[exportateur LibreFolio](https://github.com/Librefolio/librefolio-exporter) est une extension pour Chrome, Edge, Brave et les autres navigateurs Chromium, version 120 ou ultérieure. Il lit vos transactions sur les pages de Scalable, dans votre navigateur, et les enregistre sous forme de fichiers CSV :

- il fonctionne sur **toutes les formules**, FREE inclus ;
- c'est le **seul moyen** d'exporter le **compte rémunéré** ;
- il ajoute ce qui manque au CSV de Scalable : l'**identifiant de transaction** et le **type exact** de chaque mouvement.

Avant de l'installer, lisez le [README](https://github.com/Librefolio/librefolio-exporter#readme) de l'exportateur : il couvre en détail l'installation et la mise à jour, la confidentialité, et les risques d'une extension qui utilise l'interface interne de l'application web de Scalable.

**Installez-le une fois :**

1. Téléchargez les deux fichiers de la [dernière version publiée](https://github.com/Librefolio/librefolio-exporter/releases/latest), `librefolio-exporter-<version>.zip` et `librefolio-exporter-<version>.zip.sha256`, dans le même dossier — par exemple `Downloads/chromePlugin`.
2. Vérifiez le ZIP depuis un terminal. Le `cd` va dans ce dossier ; la seconde commande compare le ZIP avec l'empreinte de son fichier `.sha256` :

    === "macOS"

        ```bash
        cd ~/Downloads/chromePlugin
        shasum -a 256 -c librefolio-exporter-*.zip.sha256
        ```

    === "Linux"

        ```bash
        cd ~/Downloads/chromePlugin
        sha256sum -c librefolio-exporter-*.zip.sha256
        ```

    === "Windows"

        Windows n'a pas de commande qui lit les fichiers `.sha256` : utilisez les lignes PowerShell du [README](https://github.com/Librefolio/librefolio-exporter#readme) de l'exportateur.

    `OK` signifie que le ZIP est exactement celui publié. Pour toute autre réponse, ne l'installez pas : téléchargez à nouveau les deux fichiers.

3. Décompressez-le dans ce dossier : vous obtenez un dossier `librefolio-exporter`. Laissez-le là, car le navigateur charge l'extension depuis celui-ci.
4. Ouvrez `chrome://extensions` (`edge://extensions` dans Edge), activez le **mode développeur**, cliquez sur **Charger l'extension non empaquetée** et choisissez le dossier `librefolio-exporter`.

**Export :**

1. Connectez-vous à Scalable Capital : le bouton **LibreFolio** apparaît dans le coin inférieur droit de chaque page.
2. Cliquez dessus, choisissez les comptes et la période, puis cliquez sur **Exporter CSV**.
3. Vous obtenez `scalable-broker_<date>_<time>.csv` et `scalable-deposit_<date>_<time>.csv` — ensemble dans un seul ZIP lorsque vous exportez les deux comptes. Extrayez le ZIP : LibreFolio lit les fichiers CSV.

Le premier export lit tout l'historique ; les suivants démarrent à partir du dernier export (**Depuis le dernier**), donc seules les nouvelles transactions sont lues. Les lignes déjà présentes dans LibreFolio reviennent comme [doublons probables](index.md#duplicate-detection) et arrivent décochées. Vous pouvez renommer les fichiers : LibreFolio reconnaît chacun d'eux par ses colonnes.

!!! warning "Fichiers écrits par l'exportateur 1.0.0"

    L'exportateur 1.0.0 écrivait les frais à l'intérieur du montant de chaque transaction. LibreFolio importe ces transactions telles quelles, sans frais séparés, et vous en avertit. Mettez à jour l'exportateur vers la version 1.0.1 ou ultérieure et exportez-les à nouveau. Si vous avez déjà importé un tel fichier, supprimez d'abord les transactions listées dans l'avertissement : leurs montants changent, donc LibreFolio ne les reconnaîtrait pas comme doublons.

### 📄 Alternative : le CSV de Scalable {: #scalable-csv }

Sur les formules **PRIME** et **PRIME+**, Scalable vous permet de télécharger les transactions du **compte-titres** sous forme de fichier CSV : l'importateur **Scalable Capital compte-titres** le lit tel que téléchargé. Il ne couvre que le compte-titres — le compte rémunéré nécessite toujours l'exportateur.

Tenez-vous-en à une seule source par compte. Les descriptions que LibreFolio écrit diffèrent entre les deux sources — seules celles de l'exportateur portent l'identifiant de transaction — donc les lignes importées depuis l'une reviennent depuis l'autre comme des doublons *possibles*, toujours cochées : lorsque vous changez de source, exportez à partir du jour suivant votre dernier import.

---

## ⚙️ Configurer les deux courtiers {: #set-up }

Créez deux [courtiers](../../brokers/index.md), un par compte — par exemple *Scalable broker* et *Scalable overnight account* — et choisissez le **Plugin d'import par défaut** de chacun :

| Courtier pour | Plugin d'import par défaut | Icône |
|:--|:--|:--:|
| le compte-titres | **Scalable Capital compte-titres** | ![Logo de Scalable avec un badge de graphique bleu, l'icône de l'importateur Scalable Capital compte-titres](../../../static/icons/brokers/scalable-broker.png){: width="48" } |
| le compte rémunéré | **Scalable Capital compte rémunéré** | ![Logo de Scalable avec un badge tirelire orange, l'icône de l'importateur Scalable Capital compte rémunéré](../../../static/icons/brokers/scalable-deposit.png){: width="48" } |

Le courtier affiche alors l'icône de l'importateur de lui-même : un courtier sans icône propre affiche l'icône de son plugin d'import par défaut, avant l'icône du site web de son **URL du portail**, donc laissez **URL de l'Icône Personnalisée** vide.

---

## 📥 Import {: #import }

Importez chaque fichier dans son propre courtier, lors du même import ou à des moments différents : dans l'[Assistant d'importation](how-to.md), déposez les fichiers CSV et assignez chacun à son courtier.

Si un fichier atterrit dans le mauvais courtier, l'assistant d'importation le signale juste après le téléversement. Il montre pourquoi le plugin par défaut du courtier ne peut pas lire le fichier et quel courtier le peut, et propose de déplacer le fichier, de le conserver ou de le supprimer.

### 🔁 Virements entre vos deux comptes {: #transfers }

L'argent que vous déplacez entre le compte-titres et le compte rémunéré apparaît dans les deux fichiers : un **Retrait** dans l'un et un **Dépôt** dans l'autre, le même jour et pour le même montant. Fusionnez chaque paire en un seul **Virement** : l'espace de travail groupé de la page [Transactions](../index.md) suggère les paires, et demande confirmation avant **Enregistrer Tout** si vous ne les avez pas examinées.

- **Fichiers importés ensemble** : les deux moitiés se retrouvent dans l'espace de travail, où une bannière verte, *Transactions complémentaires détectées*, propose de **Fusionner** chaque paire — ou toutes en une fois, avec **Tout fusionner (N)**.
- **Fichiers importés à des moments différents** : lorsque vous importez le second fichier, l'espace de travail trouve les moitiés déjà enregistrées et affiche le bouton 💡 : cliquez dessus pour les ajouter, puis **Fusionner** chaque paire depuis la bannière. Pour les virements enregistrés depuis longtemps, vous pouvez également cocher les lignes de virement des deux courtiers sur la page **Transactions** et cliquer sur **Modifier** : la bannière apparaît dans l'espace de travail.

Vous pouvez aussi lier une paire manuellement : cochez ses deux lignes sur la page **Transactions** et cliquez sur **🔗 Promouvoir la paire**.

Les deux moitiés ont des descriptions différentes, puisque chacune porte son propre identifiant de transaction : conservez la description jointe que propose la fusion (dans **Fusionner tout**, le choix par défaut : **Combiner**). Un export qui chevauche un virement fusionné ramène alors ses moitiés comme doublons probables, décochées.

### 🤔 Un seul courtier ? {: #one-broker-only }

Vous pouvez importer les deux fichiers dans un seul courtier. L'import fonctionne, mais :

- chaque virement entre les comptes reste un **Dépôt** plus un **Retrait**, puisqu'un Virement nécessite deux courtiers : l'argent entrant et sortant paraît plus important qu'il ne l'est ;
- les deux comptes partagent un seul solde de trésorerie, donc aucun ne peut être vérifié seul par rapport à l'application Scalable.

Dans tous les cas, n'importez jamais le même fichier dans deux courtiers : ses transactions compteraient deux fois.

---

## 📝 Ce qui est importé {: #what-is-imported }

| Dans le fichier (`type`) | Importé comme |
|:--|:--|
| `Buy`, `Savings plan` | **Achat**, sur le montant du fichier — la valeur des parts — avec les frais d'ordre comme **Frais** et l'impôt comme **Impôt** du même titre. Un impôt restitué devient un **Dépôt** |
| `Sell` | **Vente**, de la même manière |
| `Distribution` | **Dividende**, brut — le montant crédité plus l'impôt retenu — avec cet impôt comme **Impôt** ; net lorsque le fichier ne donne pas d'impôt |
| `Interest` | **Intérêt**, brut, avec l'impôt retenu comme **Impôt** ; net lorsque le fichier ne donne pas d'impôt |
| `Deposit`, `Withdrawal` — virements bancaires, et virements entre vos deux comptes | **Dépôt**, **Retrait** |
| `Fee` | **Frais** |
| `Taxes` | **Impôt** ; un remboursement d'impôt devient un **Dépôt** |
| Toute autre ligne de trésorerie, comme un bonus | **Dépôt** ou **Retrait**, selon le signe de son montant |
| `Security transfer`, `Corporate action` et autres types | Non importés : une [notice](#notices) les liste |

- **Seules les lignes exécutées** sont importées : une notice compte les autres.
- **Les titres** arrivent avec leur ISIN et leur nom : associez chacun à vos actifs à l'étape **Révision** de l'assistant d'importation (voir [Association d'actifs](index.md#asset-mapping)).
- **Chaque description se termine par l'identifiant de transaction** : `· id …` depuis l'exportateur, suivi de `· ref …` lorsque la ligne a une référence ; `· ref …` depuis le CSV de Scalable. Les frais et l'impôt d'une transaction commencent par `Order fee ·` et `Tax ·`. L'identifiant distingue deux mouvements identiques et permet à un nouvel export de reconnaître les lignes déjà importées.
- **Tags** : `import` et `scalable`.
- **Les montants sont copiés** depuis le fichier, jamais recalculés ni convertis — un dividende ou un intérêt brut est la somme de deux de ses colonnes — et la devise provient de chaque ligne.

---

## 🔔 Ce que LibreFolio vous signale {: #notices }

À l'étape **Analyser**, les notices de l'importateur (⚠️) vous indiquent ce qu'il a omis ou lu d'une manière méritant vérification, chacune avec ses lignes :

- **Non exécutées** — les lignes en attente, annulées, expirées ou rejetées ne sont pas importées ; un ordre exécuté plus tard arrivera avec le prochain export.
- **Exécutées en partie** — les ordres exécutés en partie et encore ouverts ne sont pas encore importés : ils arriveront, exécutés, avec un export ultérieur.
- **Annulations** — les lignes qui annulent une transaction déjà enregistrée ne sont pas importées : vérifiez cette transaction et corrigez-la manuellement.
- **Non importées** — transferts de titres, opérations sur titres et types que LibreFolio ne lit pas encore : ajoutez-les manuellement s'ils déplacent des parts ou de la trésorerie.
- **Enregistrées selon le signe** — les lignes de trésorerie d'un type inconnu, ou avec un signe inattendu, deviennent un dépôt ou un retrait selon le signe de leur montant.
- **Remboursements d'impôt** — importés comme dépôts : dans LibreFolio, un impôt retire toujours de l'argent.
- **Pas de détails de frais ou d'impôt** — lignes importées avec le montant que Scalable affiche, sans frais ni impôt séparés : exportez à nouveau avec l'option d'inclure les frais et impôts.
- **Dividendes nets** — le fichier ne donne pas l'impôt retenu, donc le dividende est importé tel que crédité.
- **Virements entre vos comptes** — un rappel d'importer le fichier de l'autre compte dans son propre courtier et de [fusionner chaque paire](#transfers).
- **Plusieurs comptes rémunérés** — le fichier en contient plus d'un : toutes leurs lignes vont dans ce courtier, dont le solde est leur somme.
- **Frais à l'intérieur du montant** — les transactions d'un [fichier de l'exportateur 1.0.0](#exporter), importées telles quelles.
- **Lignes illisibles** — une date, un montant, une devise, les parts ou le titre manquent : ces lignes ne sont pas importées.

---

## ⚠️ Limites {: #limits }

- **Alpha** : aucun export réel n'a encore été observé pour les ventes, dividendes, annulations, crypto ou ordres exécutés en partie. Vérifiez ces lignes avec soin après l'import.
- **Signalez-nous** : si un fichier est refusé ou si une ligne semble erronée, veuillez ouvrir une [issue](https://github.com/Librefolio/LibreFolio/issues), avec les lignes concernées anonymisées.

## 🔗 Référence développeur

→ [Liste des fournisseurs BRIM](../../../developer/backend/brim/providers_list.md) · [Indiquer la raison avec un code](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail), les refus des deux importateurs
