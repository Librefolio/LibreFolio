# 🤝 Partage de courtier

LibreFolio vous permet de partager l'accès à vos comptes de courtage avec d'autres utilisateurs. C'est utile pour les familles, les conseillers financiers ou les comptables qui ont besoin de visibilité sur votre portefeuille.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Broker Sharing Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Comment partager

Seul un **Propriétaire** du courtier peut gérer les accès. Vous pouvez ouvrir le panneau de partage de deux manières :

- **Depuis la liste des courtiers** : cliquez sur l'icône **Partager** (:material-share-variant:) sur la carte du courtier — la **Modale de partage** s'ouvre.
- **Depuis la page de détail du courtier** : cliquez sur le bouton **Partager** dans l'en-tête — vous arrivez sur l'onglet **Info**, qui héberge le panneau de partage.

Ensuite :

1. **Recherchez** l'utilisateur par son nom d'utilisateur
2. **Sélectionnez un rôle** (Lecteur, Éditeur ou Propriétaire)
3. **Définissez le pourcentage de propriété** — uniquement pour le rôle *Propriétaire* (faites glisser le curseur ou saisissez une valeur ; les Lecteurs et les Éditeurs ont toujours 0 %)
4. Cliquez sur **Enregistrer** pour appliquer les modifications

!!! warning "Seuls les propriétaires peuvent gérer les accès"

    Vous devez être **Propriétaire** du courtier pour ajouter, supprimer ou modifier les accès des autres utilisateurs. Les non-propriétaires voient le même panneau en mode lecture seule.

---

## 🛡️ Rôles d'accès

Lorsque vous partagez un courtier, vous attribuez un **rôle** qui détermine ce que l'autre utilisateur peut faire :

| Fonctionnalité | Lecteur | Éditeur | Propriétaire |
|:-------------------------------------|:------:|:------:|:-----:|
| **Voir les détails du courtier** | ✅ | ✅ | ✅ |
| **Voir les transactions** | ✅ | ✅ | ✅ |
| **Voir les rapports et graphiques** | ✅ | ✅ | ✅ |
| **Ajouter/Modifier les transactions** | ❌ | ✅ | ✅ |
| **Importer des fichiers (BRIM)** | ❌ | ✅ | ✅ |
| **Modifier les paramètres du courtier** | ❌ | ✅ | ✅ |
| **Gérer les accès (Ajouter/Supprimer des utilisateurs)** | ❌ | ❌ | ✅ |
| **Supprimer le courtier** | ❌ | ❌ | ✅ |

- 👁️ **Lecteur** : Accès en lecture seule. Idéal pour les comptables ou les membres de la famille qui ont simplement besoin de consulter les données.
- ✏️ **Éditeur** : Peut gérer les opérations courantes (transactions, importations) mais ne peut pas supprimer le courtier ni modifier les accès.
- 👑 **Propriétaire** : Contrôle total. Peut tout faire, y compris ajouter/supprimer d'autres utilisateurs. Un courtier peut avoir **plusieurs propriétaires** — voir le pourcentage de partage ci-dessous.

---

## 📊 Pourcentage de partage

Chaque **Propriétaire** d'un courtier a un **pourcentage de partage** (de 0 % à 100 %). Il représente la part de la valeur du portefeuille du courtier qui appartient à ce propriétaire. Les Lecteurs et les Éditeurs ont toujours 0 % — le schéma rejette toute part non nulle pour eux.

!!! example "Compte joint"

    Vous et votre conjoint êtes copropriétaires d'un compte de courtage à 50/50. Vous êtes tous les deux propriétaires :

    - Vous (Propriétaire) : **50 %**
    - Conjoint (Propriétaire) : **50 %**

    Chacun de vous voit 50 % de la valeur de ce courtier comptabilisée dans son propre tableau de bord.

!!! example "Conseiller financier"

    Votre conseiller financier doit voir votre portefeuille mais n'en détient aucune part :

    - Vous (Propriétaire) : **100 %**
    - Conseiller (Lecteur) : **0 %**

La somme de tous les pourcentages de partage d'un courtier **ne doit pas dépasser 100 %**, mais elle peut être inférieure (par exemple, un compte en copropriété dont le copropriétaire n'est pas dans le système). Le panneau affiche les totaux **Alloués** et **Disponibles** pendant vos modifications.

!!! note "Agrégation du portefeuille"

    Le pourcentage de partage est **déjà appliqué** à l'agrégation de votre portefeuille : le tableau de bord et les statistiques au niveau du portefeuille ajustent chaque montant d'un courtier partagé en fonction de votre part de propriété. Un propriétaire à 50 % voit la moitié de la valeur, des revenus et des P&L de ce courtier comptabilisée dans ses totaux. Les Lecteurs et les Éditeurs, dont la part est toujours de 0 % par définition, voient les montants **complets** du courtier à la place — la part n'ajuste que ce que vous *possédez*.

---

## 🚪 Quitter un courtier partagé (en libre-service)

Vous n'avez jamais besoin de l'intervention d'un propriétaire pour quitter un courtier auquel vous avez accès. Dans le panneau de partage, la section **Votre accès** vous permet de :

- **Quitter le courtier** — supprime immédiatement votre propre accès. Le courtier disparaît de vos listes.
- **Passer en lecteur** — un Éditeur peut se rétrograder en Lecteur ; un Propriétaire peut le promouvoir à nouveau plus tard.

!!! danger "Dernier propriétaire : quitter supprime le courtier"

    Si vous êtes le **seul propriétaire** restant, l'action Quitter devient **Quitter et supprimer le courtier** : quitter *supprime définitivement le courtier ainsi que toutes ses transactions et ses fichiers de rapports importés*. Cette action ne peut pas être annulée. Si ce n'est pas ce que vous souhaitez, attribuez d'abord le rôle de Propriétaire à un autre utilisateur, puis quittez.

---

## 💡 Scénarios courants

| Scénario | Configuration suggérée |
|----------|----------------|
| **Conjoint / Partenaire** | Deux propriétaires, 50 % de part chacun |
| **Conseiller financier** | Lecteur, 0 % de part |
| **Comptable** | Lecteur, 0 % de part |
| **Membre de la famille** | Lecteur ou Éditeur, 0 % de part |
