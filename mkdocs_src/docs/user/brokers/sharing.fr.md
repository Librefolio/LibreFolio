# 🤝 Partage de Courtier

LibreFolio vous permet de partager l'accès à vos comptes de courtage avec d'autres utilisateurs. Ceci est utile pour les familles, les conseillers financiers ou les comptables qui ont besoin d'une visibilité sur votre portefeuille.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Modale de partage de courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Comment partager

1. Naviguez vers la page de détails d'un courtier
2. Cliquez sur le bouton **Partager** (:material-share-variant:) dans l'en-tête
3. La **fenêtre modale de partage** s'ouvre
4. **Recherchez** l'utilisateur par son nom d'utilisateur
5. **Sélectionnez un rôle** (Lecteur, Éditeur ou Propriétaire)
6. **Définissez le pourcentage de partage** (faites glisser le curseur ou saisissez la valeur)
7. Cliquez sur **Enregistrer** pour appliquer les modifications

!!! warning "Seuls les Propriétaires peuvent gérer l'accès"

    Vous devez être **Propriétaire** du courtier pour ajouter, supprimer ou modifier l'accès d'autres utilisateurs.

---

## 🛡️ Rôles d'accès

Lorsque vous partagez un courtier, vous attribuez un **rôle** qui détermine ce que l'autre utilisateur peut faire :

| Fonctionnalité | Lecteur | Éditeur | Propriétaire |
|:-------------------------------------|:------:|:------:|:-----:|
| **Voir les détails du courtier** | ✅ | ✅ | ✅ |
| **Voir les transactions** | ✅ | ✅ | ✅ |
| **Voir les rapports et graphiques** | ✅ | ✅ | ✅ |
| **Ajouter/Modifier des transactions**| ❌ | ✅ | ✅ |
| **Importer des fichiers (BRIM)** | ❌ | ✅ | ✅ |
| **Modifier les paramètres du courtier**| ❌ | ✅ | ✅ |
| **Gérer l'accès (Ajouter/Supprimer des utilisateurs)**| ❌ | ❌ | ✅ |
| **Supprimer le courtier** | ❌ | ❌ | ✅ |

- 👁️ **Lecteur** : Accès en lecture seule. Idéal pour les comptables ou les membres de la famille qui ont seulement besoin de consulter les données.
- ✏️ **Éditeur** : Peut gérer les opérations quotidiennes (transactions, imports) mais ne peut pas supprimer le courtier ni modifier les accès.
- 👑 **Propriétaire** : Contrôle total. Peut tout faire, y compris ajouter ou supprimer d'autres utilisateurs.

---

## 📊 Pourcentage de partage

Chaque utilisateur ayant accès à un courtier possède un **pourcentage de partage** (0 % à 100 %). Cela représente la part de la valeur du portefeuille associée à ce courtier qui appartient à cet utilisateur.

!!! example "Compte joint"

    Vous et votre conjoint(e) partagez un compte de courtage à 50/50 :

    - Vous (Propriétaire) : **50 %**
    - Conjoint(e) (Éditeur) : **50 %**

    Lors du calcul de la valeur totale du portefeuille, le système comptabilise 50 % de la valeur de ce courtier pour chacun de vous.

!!! example "Conseiller financier"

    Votre conseiller financier doit voir votre portefeuille mais n'en possède aucune part :

    - Vous (Propriétaire) : **100 %**
    - Conseiller (Lecteur) : **0 %**

La somme de tous les pourcentages de partage pour un courtier **ne doit pas dépasser 100 %**, mais elle peut être inférieure (par exemple, un compte co-détenu où le co-propriétaire n'est pas enregistré dans le système).

---

## 💡 Scénarios courants

| Scénario | Configuration suggérée |
|----------|----------------|
| **Conjoint / Partenaire** | Éditeur ou co-Propriétaire, part de 50 % chacun |
| **Conseiller financier** | Lecteur, 0 % de partage |
| **Comptable** | Lecteur, 0 % de partage |
| **Membre de la famille** | Lecteur ou Éditeur, % de partage personnalisé |

!!! note "Agrégation de portefeuille"

    Le pourcentage de partage est conçu pour les futures fonctionnalités d'agrégation de portefeuille. Une fois implémentées, le tableau de bord de chaque utilisateur affichera sa part proportionnelle de tous les courtiers auxquels il a accès.
