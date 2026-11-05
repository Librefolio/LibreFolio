# 💼 Valeur nette (NAV) / Valeur nette

## 💡 Qu'est-ce que la NAV ?

La **valeur nette (NAV)** est la valorisation totale au prix du marché de votre portefeuille à un instant $t$. Elle répond à la question : *« Combien vaut le portefeuille en ce moment ? »*

---

## 🧮 Formule

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Où :

$$
\mathrm{MV}(t)=
\sum_{(a,b)\in S}
\frac{q(a,b,t)}{qbq(a)}
\cdot \operatorname{mark}(a,t)
\cdot \mathrm{fx}(\mathrm{ccy}_{mark}, C^*, t)
$$

et la trésorerie de chaque courtier, conservée dans les devises dans lesquelles elle a été enregistrée et valorisée au taux de $t$ :

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

avec $N_{b,c}(t)$ le solde que le courtier $b$ détient dans la devise $c$ à la date $t$, ajusté selon la [part de propriété](../../../../user/brokers/sharing.md) du courtier, et $\mathrm{fx}(c, C^*, t)$ le dernier taux à la date $t$ ou avant ($1$ pour $c = C^*$). La trésorerie détenue dans une autre devise fait donc varier la NAV lorsque son taux de change varie.

Une position dont l'actif n'a pas encore de prix de valorisation — aucune cotation, aucun achat ni vente et aucune [estimation du coût de transfert](price-resolution.md#transfer-cost-estimate) à la date $t$ ou avant — est prise en compte dans $\mathrm{MV}(t)$ à son coût de base $\mathrm{CB}(a,b,t)$ lorsque ce coût est complet, et est exclue de la NAV sinon.

🔗 Voir **[Moteur de portefeuille — §3 État de position](index.md#3-position-state)** et **[§5 Agrégation](index.md#5-portfolio-aggregation)** pour la dérivation complète.

---

## 🔗 Résolveur de prix unifié {: #valuation-price-chain }

Le prix de valorisation $\operatorname{mark}(a,t)$ provient du résolveur unifié :

1. **MARKET** — cotation du système d'actifs pour le jour même.
2. **TRADE_AVG** — moyenne des observations d'achat/vente du jour même, ou le coût d'un transfert entrant pour un actif sans autre élément pour l'instant ([estimation](price-resolution.md#transfer-cost-estimate)).
3. **CARRIED** — dernière observation avant $t$, reportée (LOCF).
4. **MISSING** — aucune observation à la date $t$ ou avant.

Un ajustement n'est jamais une observation, avec ou sans coût de base : il enregistre un coût, pas un prix. Le coût d'un transfert entrant n'est pris en compte qu'à titre d'estimation, et uniquement tant que l'actif n'a aucune cotation et aucune autre opération à cette date ou avant.

Les prix de valorisation restent dans leur devise d'origine jusqu'à la valorisation, et les soldes de trésorerie de même, chacun dans la devise dans laquelle il a été enregistré ; la conversion FX a lieu à $t$. Le PRU n'est **jamais** un prix : seule une position sans aucun prix de valorisation est comptée à son coût de base, une estimation déclarée (`ESTIMATED_AT_COST`) qui conserve les taux de change de ses dates d'acquisition. Voir [Résolution des prix](price-resolution.md).

---

## 📝 Exemple

| Composant | Montant |
|-----------|--------|
| Valeur de marché des actifs | €32,759 |
| Solde de trésorerie | €631 |
| En transit | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinctions clés

- **NAV vs [Valeur comptable](book-value.md)** : NAV = valeur de marché ; Valeur comptable = coût d'acquisition. Différence = plus-values latentes.
- **NAV vs [P&L période](period-pnl.md)** : NAV = instantané ; P&L période = variation ajustée des flux dans le temps.

---

## ⚠️ Qualité des données

| Source de valorisation | Confiance |
|-----------------|------------|
| `MARKET_PRICE` | Complète — cotation réelle, exacte ou reportée |
| `LAST_TRADE_PRICE` | Partielle — prix de valorisation du résolveur issu d'une transaction |
| `ESTIMATED_AT_COST` | Estimation — aucun prix du tout : le coût de base, sans plus-value latente ni moins-value latente |
| `MISSING` | Aucune — pas de prix et un coût incomplet : exclue de la NAV |

`estimated=True` ne s'applique qu'aux prix de valorisation d'origine TRADE. Une cotation MARKET reportée et obsolète est obsolète mais non estimée.

Pour un actif disposant d'un fournisseur de prix, le tableau de bord avertit à la date de valorisation : une valorisation d'origine transactionnelle, dès lors que l'actif n'a plus eu de cotation de marché pendant plus de la période de grâce de 14 jours — décomptée depuis l'arrivée du transfert pour un actif jamais coté, acheté ou vendu, valorisé au coût d'un transfert —, déclenche l'avertissement « valorisés à leur dernier prix de transaction », et une valorisation au coût, plus de 14 jours après la première acquisition de l'actif, déclenche l'avertissement « valorisé au coût ». Un actif sans fournisseur ne déclenche ni l'un ni l'autre : ses transactions, ou son coût, constituent sa valeur prévue.
