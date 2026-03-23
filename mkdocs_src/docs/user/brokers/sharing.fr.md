# 🤝 Partage de courtier

LibreFolio vous permet de partager l'accès à vos comptes de courtage avec d'autres utilisateurs. Cela est utile pour les familles, les conseillers financiers ou les comptables qui ont besoin d'avoir une visibilité sur votre portefeuille.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Fenêtre de partage de courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Comment partager

1. Accédez à la page de détail d'un courtier
2. Cliquez sur le bouton **Partager** (:material-share-variant:) dans l'en-tête
3. La **fenêtre de partage** s'ouvre
4. **Recherchez** par nom d'utilisateur
5. **Sélectionnez un rôle** (Consulteur, Éditeur ou Propriétaire)
6. **Définissez le pourcentage de part** (glissez le curseur ou saisissez une valeur)
7. Cliquez sur **Enregistrer** pour appliquer les modifications

!!! warning "Seuls les Propriétaires peuvent gérer les accès"

    Vous devez être **Propriétaire** du courtier pour ajouter, supprimer ou modifier l'accès d'autres utilisateurs.

---

## 🛡️ Rôles d'accès

Lorsque vous partagez un courtier, vous assignez un **rôle** qui détermine ce que l'autre utilisateur peut faire :

| Fonctionnalité | Consulteur | Éditeur | Propriétaire |
|:--------------------------------------------|:----------:|:-------:|:------------:|
| **Voir les détails du courtier** | ✅ | ✅ | ✅ |
| **Voir les transactions** | ✅ | ✅ | ✅ |
| **Voir les rapports et graphiques** | ✅ | ✅ | ✅ |
| **Ajouter/Modifier des transactions** | ❌ | ✅ | ✅ |
| **Importer des fichiers (BRIM)** | ❌ | ✅ | ✅ |
| **Modifier les paramètres du courtier** | ❌ | ✅ | ✅ |
| **Gérer les accès (Ajouter/Supprimer)** | ❌ | ❌ | ✅ |
| **Supprimer le courtier** | ❌ | ❌ | ✅ |

- 👁️ **Consulteur** : Accès en lecture seule. Idéal pour les comptables ou les membres de la famille qui ont seulement besoin de voir les données.
- ✏️ **Éditeur** : Peut gérer les opérations quotidiennes (transactions, imports) mais ne peut pas supprimer le courtier ni modifier les accès.
- 👑 **Propriétaire** : Contrôle total. Peut tout faire, y compris ajouter/supprimer d'autres utilisateurs.

---

## 📊 Pourcentage de part

Chaque utilisateur ayant accès à un courtier dispose d'un **pourcentage de part** (0% à 100%). Cela représente la part de la valeur du portefeuille du courtier qui appartient à cet utilisateur.

!!! example "Compte joint"

    Vous et votre conjoint(e) partagez un compte de courtage à 50/50 :

    - Vous (Propriétaire) : **50%**
    - Conjoint(e) (Éditeur) : **50%**

    Lors du calcul de la valeur totale du portefeuille, le système compte 50% de la valeur de ce courtier pour chacun d'entre vous.

!!! example "Conseiller financier"

    Votre conseiller financier a besoin de voir votre portefeuille mais n'en possède aucune part :

    - Vous (Propriétaire) : **100%**
    - Conseiller (Consulteur) : **0%**

La somme de tous les pourcentages de part pour un courtier **ne doit pas dépasser 100%**, mais elle peut être inférieure (par exemple, un compte co-détenu où le co-titulaire n'est pas dans le système).

---

## 💡 Scénarios courants

| Scénario | Configuration suggérée |
|----------|------------------------|
| **Conjoint(e) / Partenaire** | Éditeur ou Propriétaire, 50% de part chacun |
| **Conseiller financier** | Consulteur, 0% de part |
| **Comptable** | Consulteur, 0% de part |
| **Membre de la famille** | Consulteur ou Éditeur, pourcentage de part personnalisé |

!!! note "Agrégation de portefeuille"

    Le pourcentage de part est conçu pour les futures fonctionnalités d'agrégation de portefeuille. Lorsqu'elles seront implémentées, le tableau de bord de chaque utilisateur affichera sa part proportionnelle de tous les courtiers auxquels il a accès.
