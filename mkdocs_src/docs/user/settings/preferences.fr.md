# 🎛️ Préférences utilisateur

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="Préférences utilisateur">
</div>

L'onglet **Préférences** contrôle **l'apparence et le comportement de l'application pour vous** — les modifications ne s'appliquent qu'à votre compte. Votre identité (nom d'utilisateur, e-mail, avatar, mot de passe) se trouve, elle, dans l'onglet **[Profil](profile.md)**.

| Paramètre | Catégorie | Description |
|---------|----------|-------------|
| **Langue** | 🌍 Affichage | Langue de l'interface — 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español. S'applique dès que vous l'enregistrez |
| **Devise par défaut** | 💰 Devise | Votre propre devise de référence. Le Tableau de bord, la page Courtiers et la page de chaque courtier, ainsi que l'onglet **Corrélation** de la page Actifs s'ouvrent dans cette devise, et l'export IA d'une paire de devises l'utilise aussi ; une devise que vous choisissez sur le Tableau de bord reste valable pour la session. Elle est également proposée lorsque vous créez quelque chose de nouveau — un actif, le premier solde de trésorerie d'un nouveau courtier, un plan PAC. Ce menu liste toutes les devises |
| **Thème** | 🎨 Apparence | ☀️ Clair / 🌙 Sombre / 🖥️ Auto (suit votre système d'exploitation) |

<style>
/* Keep the first two columns on one line (long setting names would wrap otherwise) */
article table:first-of-type th:nth-child(-n + 2),
article table:first-of-type td:nth-child(-n + 2) {
    white-space: nowrap;
    min-width: 11rem;
}
</style>

Choisissez une catégorie dans la barre latérale — sur un téléphone, dans le menu **Catégorie** — pour n'afficher que ses paramètres ;
**Tous les paramètres** affiche tout.

!!! tip "Menus de devises sur le Tableau de bord et les pages d'actifs"

    Les menus de devises du **Tableau de bord** et d'une page d'actif sont plus courts que **Devise par défaut** : ils ne proposent que les devises de vos paires FX, et **Créer un forex…** en bas de la liste ajoute une paire manquante. Voir **[Tableau de bord](../dashboard/index.md)**.

## 💾 Enregistrement, annulation, réinitialisation

Chaque champ conserve son propre état :

- Modifiez un champ et il affiche **Enregistrer** et **Annuler** ; l'en-tête propose **Tout enregistrer** et **Tout annuler**
  pour chaque champ modifié.
- Lorsqu'une valeur enregistrée diffère de la **valeur par défaut de l'instance** (définie par votre administrateur dans
  [Paramètres globaux](../../admin/settings.md)), un bouton orange **Réinitialiser par défaut** apparaît : il
  remet la valeur par défaut dans le champ, prête à être enregistrée. **Tout réinitialiser par défaut** le fait pour chaque
  champ.

---

## 🧭 Prise en main et guides {: #onboarding-and-guides }

La catégorie **Prise en main** liste tous les guides, regroupés par lieu d'apparition. Chacun affiche son
statut — **En attente**, **Terminé** ou **Ignoré** — et la version que vous avez vue.
**Nouvelle version à consulter** signifie qu'un contenu mis à jour vous attend : le guide redémarre la prochaine fois que vous
y accédez.

| Groupe | Guides |
|---|---|
| **Configuration** | Configuration d'accueil |
| **Parcours principal** | Visite rapide |
| **Transactions** | Vue d'ensemble des transactions, Guide d'ajout de transaction, Vue d'ensemble de l'espace de travail groupé, Guide d'importation |
| **Courtiers** | Vue d'ensemble des courtiers, Guide du courtier, Guide des détails d'un courtier |
| **FX** | Vue d'ensemble FX, Guide FX, Guide des détails d'une paire FX |
| **Actifs** | Vue d'ensemble des actifs, Guide de l'actif, Guide des détails d'un actif |

### 🔁 Relancer un guide

- **Configuration d'accueil** et **Visite rapide** — **Relancer** les démarre immédiatement.
- Tout autre guide — **Relancer au prochain déclenchement** le prépare : il démarre la prochaine fois que vous ouvrez sa
  page, son formulaire, son assistant ou son espace de travail. **Annuler l'activation** le retire.
- **Tout relancer** prépare tous les guides et ouvre d'abord la page d'accueil.

Un rejeu ne modifie jamais le statut enregistré, et les guides ne cliquent ni n'enregistrent à votre place. Une exception :
lors d'un rejeu de la page d'accueil, **Continuer** enregistre la langue, la devise et l'image que vous avez choisies
(**Quitter le parcours** part sans enregistrer).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="onboarding-replay" alt="La catégorie Prise en main des Préférences : Prise en main et guides avec Tout relancer ; Configuration d'accueil et Parcours principal dépliées, chaque guide avec son badge Terminé, Vu v1 · actuel v1 et Relancer ; les autres zones repliées avec leur nombre">
</div>

??? info "🧩 Guide d'importation et vue d'ensemble de l'espace de travail groupé — guides avec étapes"

    Dépliez la ligne de l'un ou l'autre guide pour voir chaque étape avec son propre statut. Une étape d'importation
    facultative (**Unifier les actifs**, **Corrections**, **Doublons**, **Aligner avec la banque**) reste **En attente**
    jusqu'à ce qu'une importation en ait besoin pour la première fois.

    Dans ces deux guides, **✕** n'ignore que l'étape en cours : la suivante démarre lorsque l'assistant ou
    l'espace de travail l'atteint. Lors d'un rejeu, **✕** retire l'étape du rejeu sans modifier
    son statut enregistré.

??? note "💾 Où un rejeu est conservé — ce navigateur uniquement"

    Un rejeu est conservé dans ce navigateur, pour votre compte : un rejeu à moitié terminé survit à un rechargement,
    à la fermeture du navigateur ou à une déconnexion suivie d'une reconnexion. Il n'est pas partagé avec d'autres comptes,
    navigateurs ou appareils. Il se termine lorsque vous le finissez ou le quittez, lorsque vous l'annulez ici, ou lorsqu'une mise à jour apporte une
    version plus récente du guide — et il se ferme alors aussi dans vos autres onglets ouverts.

Si la liste des guides ne peut pas être chargée, cette section affiche son propre bouton **Réessayer**.

---

## 🙈 Mode confidentialité {: #privacy-mode }

Le mode confidentialité masque ce que vous possédez lorsque quelqu'un d'autre peut voir votre écran — un collègue qui passe,
un écran partagé, un projecteur. Ce n'est pas un champ de cet onglet : c'est le **bouton en forme d'œil** dans
l'en-tête de la page, en haut à droite, à côté des boutons de thème et de langue.

- :material-eye-outline: **Masquer les montants** — les montants sont visibles ; cliquez pour les masquer.
- :material-eye-off-outline: **Afficher les montants** — le mode confidentialité est activé ; cliquez pour afficher à nouveau les montants.

La modification s'applique immédiatement à la page où vous vous trouvez, sans rechargement, et le mode confidentialité reste activé
lorsque vous naviguez entre les pages et après un rechargement, jusqu'à ce que vous le désactiviez. À ne pas confondre avec l'icône
en forme d'œil d'une **barre d'outils de tableau**, qui affiche ou masque les colonnes d'un tableau.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="Le Tableau de bord avec le mode confidentialité activé : le bouton en forme d'œil barré dans l'en-tête, les montants des cartes KPI et des Soldes de trésorerie affichés sous forme de ••• avec leur signe et leur devise, les pourcentages toujours lisibles, et l'axe Croissance du portefeuille masqué">
</div>

### 🔒 Ce qui est masqué

Le mode confidentialité remplace le **nombre** d'un montant par `•••`. La devise reste toujours présente, tout comme
le signe, de sorte qu'un gain se lit toujours comme un gain et une perte comme une perte :

| Normalement | Avec le mode confidentialité |
|---|---|
| `1,234.56 € 🇪🇺 EUR` | `••• € 🇪🇺 EUR` |
| `-1,234.56 € 🇪🇺 EUR` | `-••• € 🇪🇺 EUR` |
| `€1,234.56` ou `1.234,56 €` | `€•••` ou `••• €` |
| `—` (aucune valeur) | `—` |

`•••` correspond toujours aux trois mêmes points — même le **K** ou le **M** d'un chiffre abrégé disparaît — afin de ne jamais
révéler l'ordre de grandeur. Cela couvre :

- **Tableau de bord**, **Courtiers** et les **panneaux de risque** — leurs montants : les cartes KPI, les Soldes de trésorerie,
  les infobulles d'Allocation, les cartes de courtier et la page de détail d'un courtier.
- **[Positions](../dashboard/positions.md)** et
  **[Analyse des lots FIFO](../dashboard/positions.md#fifo-lots-analysis)** — chaque montant sauf les
  prix unitaires, dans les tableaux, la modale de détail du lot et les graphiques, ainsi que les quantités que vous détenez
  (la colonne **Qté** des Positions, les quantités des lots). Un lot partiellement clôturé affiche sa part ouverte, par
  exemple `••• (60%)`.
- **Transactions** — le montant en trésorerie de chaque transaction.
- **[Allocateur PAC](../tools/pac-allocator/index.md#reading-the-result)** — chaque montant et
  quantité du résultat, ainsi que les limites d'achat d'une route.

### 👀 Ce qui reste visible

Les nombres qui n'indiquent pas **combien vous possédez** restent lisibles, afin que vous puissiez continuer à travailler :

- la **devise** de chaque montant masqué, les **pourcentages** (rendements, pondérations, parts d'allocation,
  rendement sur coût) et les **taux de change** ;
- les **prix unitaires** — les prix de marché, les colonnes **Prix** et **Coût moyen** de Positions, les
  prix des lots et les lignes de prix du graphique PRU / Prix de marché ;
- les **comptages, dates et noms**, et les **événements d'actif** tels qu'un dividende ou une division, qui décrivent
  l'actif plutôt que votre portefeuille ;
- les **quantités dans la liste des Transactions** — un choix délibéré, même si une quantité multipliée
  par le prix public laisse deviner la taille d'une opération ;
- les nombres à l'intérieur des **champs de saisie**, par exemple lorsque vous ajoutez ou modifiez une transaction : un champ que
  vous ne pouvez pas lire est un champ que vous ne pouvez pas modifier.

### 🌐 Où le réglage est conservé

Le mode confidentialité appartient à **ce navigateur**, et non à votre compte : il concerne l'écran que quelqu'un pourrait
être en train de regarder.

- Il est désactivé jusqu'à ce que vous l'activiez. Se déconnecter ou changer de compte le laisse tel quel, et il ne vous suit pas
  sur un autre navigateur ou appareil.
- Les autres onglets LibreFolio déjà ouverts dans ce navigateur prennent en compte la modification lorsque vous les rechargez.
- Si le navigateur bloque le stockage de site, le mode confidentialité fonctionne toujours dans cet onglet, mais peut être de nouveau désactivé
  après un rechargement.

!!! warning "Ce que le mode confidentialité ne couvre pas"

    - **[export IA](../ai-export/index.md)** copie les chiffres réels dans le presse-papiers même lorsque
      le mode confidentialité est activé. Relisez le texte avant de le partager.
    - Les **téléchargements et les fichiers exportés** contiennent les chiffres réels.
    - Il masque ce qui est **dessiné à l'écran**. Les chiffres parviennent toujours à votre navigateur ; il ne s'agit donc pas
      d'une protection contre quelqu'un qui peut utiliser votre appareil ou ses outils de développement.
    - Certains chiffres peuvent encore être **déduits** : le signe distingue un gain d'une perte, et lorsque vous détenez
      une seule unité d'un actif, son prix visible correspond à sa valeur.

---

## 🔗 Voir aussi

- 👤 **[Profil](profile.md)** — Nom d'utilisateur, e-mail, avatar, mot de passe, suppression du compte
- ⚙️ **[Vue d'ensemble des paramètres](index.md)** — Résumé des paramètres généraux
- ℹ️ **[À propos](about.md)** — Informations de version, plugins et journal des modifications
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options d'administrateur et planificateur
- 🛠️ **[Composants des paramètres](../../developer/frontend/components/features/settings.md)** — Comment cet onglet et sa liste de Prise en main sont construits (pour les développeurs)
