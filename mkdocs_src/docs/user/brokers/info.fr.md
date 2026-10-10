# ⚙️ Configuration et informations du courtier

L'onglet **Info** d'un courtier affiche les détails du compte à gauche et les personnes qui peuvent y accéder à droite.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vue des informations et du partage du courtier">
</div>

---

## 📋 Détails du compte

La carte **Détails** liste :

- **Compte actif** — **✓ Actif**, ou **✗ Clôturé** pour un compte que vous n'utilisez plus. Un courtier clôturé conserve son historique dans vos graphiques.
- **Compte ouvert** — la date à laquelle vous avez ouvert le compte, si vous l'avez renseignée.
- **Autoriser l'achat à effet de levier** et **Autoriser la vente à découvert** — les deux options de trading, expliquées ci-dessous.
- **Créé dans le système** — la date à laquelle le courtier a été ajouté à LibreFolio.

Pour les modifier, cliquez sur **Modifier** dans la barre d'outils du courtier (Propriétaires et Éditeurs).

---

## 🛡️ Options de trading {: #trading-options }

Les deux options sont désactivées pour un nouveau courtier, et LibreFolio vous protège alors contre les soldes impossibles :

- avec **Autoriser l'achat à effet de levier** désactivée, une sauvegarde est refusée si elle devait faire passer la trésorerie d'une devise sous zéro ;
- avec **Autoriser la vente à découvert** désactivée, une sauvegarde est refusée si elle devait faire passer la quantité d'un actif sous zéro.

Activez une option pour un compte sur marge, ou pour enregistrer des ventes à découvert.

??? note "📅 Comment les soldes sont vérifiés — quand une sauvegarde est refusée"

    Pour chaque devise $c$ et chaque actif $i$ du courtier, LibreFolio examine le solde à la **fin de chaque journée** $d$, après toutes les transactions de cette journée :

    $$
    C_c(d) = \sum_{\text{date}_t \le d} a_t \ge 0 \qquad\qquad Q_i(d) = \sum_{\text{date}_t \le d} q_t \ge 0
    $$

    Ici, $a_t$ est le montant en espèces de chaque transaction $t$ dans la devise $c$, et $q_t$ la quantité de chaque transaction de l'actif $i$. Les entrées et sorties d'argent du même jour se compensent, mais un dépôt effectué plus tard ne corrige pas une journée déjà clôturée sous zéro.

    Une sauvegarde refusée apparaît dans l'espace de travail sous *Cette configuration provoque des incohérences de données*, avec la devise ou l'actif, la date et des liens vers les lignes concernées de l'espace de travail.

---

## 🤝 Partager le courtier

La colonne de droite contient le panneau **Partager le courtier** ; **Partager le courtier** dans la barre d'outils vous amène également ici. Seul un Propriétaire peut le modifier : tous les autres le voient en lecture seule.

Pour donner accès à quelqu'un :

1. Cliquez sur **+** (**Ajouter un utilisateur**) sous le graphique de répartition de propriété et trouvez la personne **par son nom d'utilisateur**.
2. Choisissez le **Rôle** — **Lecteur** par défaut, **Éditeur** ou **Propriétaire** — et, pour un Propriétaire, le **% de propriété**. Cliquez ensuite sur **Ajouter un utilisateur**.
3. Cliquez sur **Enregistrer la configuration** : rien ne change avant cela.

Enregistrez avant de changer d'onglet : dans l'onglet Info, les modifications non enregistrées sont abandonnées sans confirmation.

Sous **Votre accès**, vous pouvez aussi **Quitter le courtier**, ou **Passer en lecteur** si vous êtes Éditeur. Les rôles et les parts de propriété sont expliqués dans [Partage du courtier](sharing.md).

---

## 🔗 Voir aussi

- 🧠 **[Export IA du courtier](../ai-export/broker.md)** — **export IA** se trouve dans la barre d'outils du courtier et fonctionne depuis chaque onglet.
- 🏦 **[Courtiers](index.md)** — créer un courtier et ses champs facultatifs.
