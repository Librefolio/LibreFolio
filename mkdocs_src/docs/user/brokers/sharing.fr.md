# 🤝 Partage de courtier

Partagez un courtier avec les personnes qui en ont besoin — un partenaire, un membre de la famille, un conseiller ou un comptable. Chaque personne reçoit un **rôle**, qui détermine ce qu'elle peut faire, et chaque Propriétaire reçoit une **part de propriété**, qui détermine quelle part du compte lui revient.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Modale de partage de courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Partager un courtier

Ouvrez le panneau de partage à l'aide du bouton de partage sur la carte du courtier, ou via **Partager le courtier** dans la barre d'outils du courtier (cela ouvre l'onglet **Info**). Seul un Propriétaire peut le modifier ; tous les autres le voient en lecture seule.

1. Cliquez sur **+** (**Ajouter un utilisateur**) et trouvez la personne **par nom d'utilisateur**.
2. Choisissez le **Rôle** et, pour un Propriétaire, le **% de propriété**. Cliquez ensuite sur **Ajouter un utilisateur**.
3. Cliquez sur **Enregistrer la configuration**. Rien ne change avant cela : jusque-là, **↺ Réinitialiser** remet la liste dans son état d'origine.

??? note "✏️ Modifier ou retirer quelqu'un — et quand un enregistrement est refusé"

    Cliquez sur la pastille d'une personne pour modifier son **Rôle** ou son **% de propriété**, ou pour **Retirer l'accès** ; cliquez sur **Confirmer**, puis sur **Enregistrer la configuration**.

    Un enregistrement est refusé s'il devait laisser le courtier **sans Propriétaire** — le dernier Propriétaire ne peut donc être ni retiré ni rétrogradé — ou si les parts totalisent **plus de 100 %** (le panneau affiche l'avertissement *Le total de la propriété dépasse 100 %*).

    Modifications non enregistrées : la boîte de dialogue ouverte depuis la liste des courtiers demande confirmation avant de se fermer, mais dans l'onglet **Info**, passer à un autre onglet les abandonne.

---

## 🛡️ Ce que chaque rôle peut faire

| Ce que vous pouvez faire | Lecteur | Éditeur | Propriétaire |
|:--|:--:|:--:|:--:|
| Voir le courtier, ses transactions, ses rapports et ses graphiques | ✅ | ✅ | ✅ |
| Ajouter, modifier et importer des transactions ; téléverser et supprimer des fichiers de rapport | ❌ | ✅ | ✅ |
| Modifier les paramètres du courtier | ❌ | ✅ | ✅ |
| Gérer les personnes ayant accès | ❌ | ❌ | ✅ |
| Supprimer le courtier | ❌ | ❌ | ✅ |

- 👁️ **Lecteur** — en lecture seule, pour un comptable ou des proches qui ont seulement besoin de consulter.
- ✏️ **Éditeur** — assure le travail quotidien, mais ne peut ni partager ni supprimer le courtier.
- 👑 **Propriétaire** — contrôle total ; un courtier peut avoir plusieurs Propriétaires.

---

## 📊 Part de propriété

Chaque Propriétaire a une **part** de 0 % à 100 % : la partie du compte qui lui revient. Les Lecteurs et les Éditeurs ont toujours 0 %. Les parts peuvent totaliser moins de 100 % — par exemple lorsqu'un copropriétaire n'utilise pas LibreFolio — mais jamais plus ; le panneau affiche les totaux **Alloué** et **Disponible** au fur et à mesure de vos modifications.

La part détermine ce qui compte dans vos chiffres :

- Le **Tableau de bord** ne compte que les courtiers que vous **possédez** avec une part supérieure à 0 %, et ajuste leurs montants selon votre part : avec 50 %, vous voyez la moitié de la valeur, des revenus et du P&L du courtier.
- L'onglet **Risque** du Tableau de bord couvre les mêmes courtiers : ceux que vous possédez avec une part supérieure à 0 % (voir [Onglet Risque](../dashboard/index.md#risk-tab)).
- Les courtiers pour lesquels vous êtes Lecteur ou Éditeur, ou que vous possédez à 0 %, ne figurent pas sur votre Tableau de bord. Leur propre page les affiche : les Lecteurs et les Éditeurs voient les montants **complets**, les Propriétaires leur part.

---

## 💡 Configurations courantes

| Qui | Configuration | Ce qu'ils voient |
|:--|:--|:--|
| Conjoint ou partenaire | Deux Propriétaires, 50 % chacun | Chacun de vous voit la moitié du compte sur son propre Tableau de bord |
| Copropriétaire sans compte LibreFolio | Vous comme Propriétaire, 50 % | Votre moitié ; l'autre 50 % reste non allouée |
| Conseiller financier ou comptable | Lecteur | L'ensemble du courtier sur sa page, rien sur son Tableau de bord |
| Membre de la famille qui saisit les opérations | Éditeur | Ajoute et importe des transactions, mais ne peut ni partager ni supprimer le courtier |

---

## 🚪 Quitter un courtier ou se retirer

Vous n'avez jamais besoin de l'intervention d'un Propriétaire pour partir. Sous **Votre accès** dans le panneau de partage, après une confirmation :

- **Quitter le courtier** retire votre accès immédiatement, et le courtier disparaît de vos listes ;
- **Passer en lecteur** (Éditeurs uniquement) renonce à l'édition ; un Propriétaire peut vous redonner le rôle d'Éditeur.

!!! danger "Dernier Propriétaire : quitter supprime le courtier"

    Si vous êtes le **seul Propriétaire** restant, le bouton devient **Quitter et supprimer le courtier** : quitter *supprime définitivement le courtier ainsi que toutes ses transactions et les fichiers de rapport importés*. Cette action est irréversible. Pour conserver le courtier, faites d'abord d'un autre utilisateur un Propriétaire, puis quittez.

La suppression de votre compte suit la même règle — voir [Profil](../settings/profile.md).

Pour obtenir l'accès au courtier de quelqu'un d'autre, demandez à l'un de ses Propriétaires. Les courtiers que vous ne pouvez pas ouvrir sont listés sous **Autres courtiers existants** sur la page [Courtiers](index.md), et leur bouton de partage indique qui a accès. Tout utilisateur connecté à ce LibreFolio peut voir qui a accès à n'importe quel courtier, afin que les personnes qui partagent une instance puissent se retrouver.
