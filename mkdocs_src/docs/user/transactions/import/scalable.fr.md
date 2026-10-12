# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

LibreFolio importe les deux comptes de **Scalable Capital** : le **compte-titres** et le **compte rémunéré** (*conto deposito*). LibreFolio n'est pas affilié à Scalable Capital.

---

## 🏦 Deux comptes, deux courtiers {: #two-brokers }

Chaque compte devient un courtier à part entière dans LibreFolio, lu par son propre importateur. Créez deux [courtiers](../../brokers/index.md), un par compte, et choisissez le **Plugin d'Import par Défaut** de chacun :

<div class="lf-accounts-table" markdown>

| Compte Scalable | Plugin d'Import par Défaut | Fichiers lus |
|:--|:--|:--|
| ![](../../../static/icons/brokers/scalable-broker.png){: style="width:36px;vertical-align:middle;margin-right:6px" } Compte-titres | **Scalable Capital compte-titres** | le fichier courtier de l'exportateur LibreFolio, ou le CSV de Scalable |
| ![](../../../static/icons/brokers/scalable-deposit.png){: style="width:36px;vertical-align:middle;margin-right:6px" } Compte rémunéré | **Scalable Capital compte rémunéré** | le fichier compte rémunéré de l'exportateur LibreFolio |

</div>

#### ❓ Pourquoi deux courtiers ? {: #why-two-brokers }

- Chaque compte possède son propre solde de trésorerie et son propre IBAN.
- L'argent que vous déplacez entre eux est un **Virement**, qui relie deux courtiers.
- Avec deux courtiers, chaque solde peut être vérifié par rapport à l'application Scalable, et chaque virement devient une paire liée.
- Chaque importateur refuse le fichier de l'autre compte et indique l'importateur qui le lit.

---

## 📤 Comment exporter {: #exporter }

En octobre 2026, Scalable ne permet de télécharger vos transactions que sur les formules **PRIME** et **PRIME+**, et jamais celles du compte rémunéré.

C'est pourquoi une extension de navigateur a été créée, qui exporte vos données en fichiers CSV : l'[exportateur LibreFolio](https://github.com/Librefolio/librefolio-exporter). Il fonctionne dans Chrome, Edge, Brave et les autres navigateurs Chromium, version 120 ou ultérieure, et lit vos transactions sur les pages de Scalable, dans votre navigateur.

Nous recommandons **notre exportateur** pour les raisons suivantes :

- il fonctionne sur **toutes les formules**, FREE inclus ;
- c'est le **seul moyen** d'exporter le **compte rémunéré** ;
- il ajoute ce qui manque au CSV de Scalable : l'**identifiant de transaction** et le **type exact** de chaque mouvement.

Le plugin d'import de LibreFolio pour le compte-titres lit aussi le CSV de Scalable (PRIME) ; celui du compte rémunéré ne lit que le fichier de l'exportateur.

??? note "🧩 Installer l'exportateur — une fois, avant le premier export"

    Les détails à jour se trouvent dans le [README](https://github.com/Librefolio/librefolio-exporter#readme) de l'exportateur, qui couvre aussi la mise à jour, la confidentialité et les risques d'une extension qui utilise l'interface interne de l'application web de Scalable : lisez-le avant de l'installer. Voici une synthèse des étapes.

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

---

## 📥 Import {: #import }

Importez chaque fichier dans son propre courtier, lors du même import ou à des moments différents : dans l'[Assistant d'importation](how-to.md), déposez les fichiers CSV et assignez chacun à son courtier. N'importez jamais le même fichier dans deux courtiers : ses transactions compteraient deux fois.

!!! note "💡 Un fichier dans le mauvais courtier"

    Si un courtier a un **Plugin d'Import par Défaut**, l'assistant d'importation vérifie chaque fichier qui lui est assigné juste après le téléversement. Lorsque ce plugin ne peut pas lire un fichier, l'assistant indique pourquoi, montre quel courtier peut le lire et propose de déplacer le fichier, de le conserver ou de le supprimer.

### 🔁 Virements entre vos deux comptes {: #transfers }

L'argent que vous déplacez entre le compte-titres et le compte rémunéré apparaît dans les deux fichiers :

1. le compte d'où part l'argent enregistre un **Retrait** ;
2. le compte où il arrive enregistre un **Dépôt**, le même jour et pour le même montant ;
3. vous fusionnez les deux en un seul **Virement** : après l'import, tant que les [nouvelles lignes](../index.md#bulk-workspace) attendent **Enregistrer Tout**, LibreFolio suggère les paires, et demande confirmation avant d'enregistrer si vous ne les avez pas examinées.

??? info "🔍 Comment les paires sont trouvées, et comment les corriger"

    - **Fichiers importés ensemble** : les deux moitiés arrivent avec les autres nouvelles lignes, et une bannière verte, *Transactions complémentaires détectées*, propose de **Fusionner** chaque paire — ou toutes en une fois, avec **Tout fusionner (N)**.
    - **Fichiers importés à des moments différents** : lorsque vous importez le second fichier, LibreFolio trouve les moitiés déjà enregistrées et affiche le bouton 💡 : cliquez dessus pour les ajouter, puis **Fusionner** chaque paire depuis la bannière. Pour les virements enregistrés depuis longtemps, vous pouvez également cocher les lignes de virement des deux courtiers sur la page **Transactions** et cliquer sur **Modifier** : la même bannière apparaît.
    - **À la main** : cochez les deux lignes d'une paire sur la page **Transactions** et cliquez sur **🔗 Promouvoir la paire**.
    - **Descriptions** : les deux moitiés ont des descriptions différentes, puisque chacune porte son propre identifiant de transaction. Conservez la description jointe que propose la fusion (dans **Tout fusionner**, le choix par défaut : **Combiner**) : un export qui chevauche un virement fusionné ramène alors ses moitiés comme doublons probables, décochées.

## 🔗 Référence développeur

- [Importateurs Scalable Capital](../../../developer/backend/brim/scalable.md)
- [Liste des fournisseurs BRIM](../../../developer/backend/brim/providers_list.md)
- [Indiquer la raison avec un code](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail) : les refus des deux importateurs
