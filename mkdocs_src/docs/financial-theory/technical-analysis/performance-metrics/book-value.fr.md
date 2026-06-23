# 📖 Book Value

*[⬅️ Retour à l'aperçu des mesures de performance](index.md)*

## 💡 Qu'est-ce que le Book Value?

Dans LibreFolio, le **Book Value** représente le coût comptable historique (prix de revient) de votre portefeuille. Il reflète le montant net de capital que vous avez réellement investi dans vos positions actuellement ouvertes, plus la trésorerie.

Il répond à la question : _"Combien mon portefeuille actuel a-t-il coûté à construire ?"_

Contrairement à la Net Asset Value (NAV), qui fluctue selon les cours quotidiens du marché, le Book Value ne change que lorsque vous achetez ou vendez des actifs, ou lorsque des liquidités sont déposées/retirées. Il ne représente pas la valeur de marché actuelle en cas de liquidation.

---

## 🧮 Formule

Le Book Value est calculé selon la formule suivante :

$$
\text{Book Value} = \text{Coût des Positions Ouvertes} + \text{Liquidité} + \text{Coût en Transit}
$$

Dans laquelle :

- **$\text{Coût des Positions Ouvertes}$** : Le coût total d'acquisition de vos positions encore ouvertes, calculé en multipliant la quantité de chaque actif par son [Coût Moyen Pondéré (CMP)](weighted-average-cost.md).
- **$\text{Liquidité}$** : Le solde de trésorerie réel détenu sur les comptes des courtiers inclus dans le périmètre.
- **$\text{Coût en Transit}$** : Le coût comptable des liquidités ou des actifs actuellement en transit entre des comptes inclus dans le périmètre. Ce concept est introduit pour gérer les transferts (ex. virements bancaires ou transferts de titres) qui partent comptablement le jour 1 du compte source et arrivent le jour 5 sur le compte de destination en raison des délais d'exécution.

---

## 📝 Exemple Pratique

Considérons un portefeuille présentant les chiffres suivants :

- **Coût d'Achat des Positions Ouvertes** : 27 000 €
- **Liquidité** : 600 €
- **Actifs en Transit (Coût Comptable)** : 0 €

Le Book Value est calculé comme suit :

$$
\text{Book Value} = 27 000 + 600 + 0 = 27 600\text{ €}
$$

### 📊 Comparaison avec la NAV (Performance Latente)

Si la valeur de marché actuelle ([NAV](nav.md)) de ce portefeuille est de **33 000 €**, nous pouvons calculer la **Plus-value/Moins-value Latente** (unrealized gain/loss) en la comparant à la Valeur Comptable :

$$
\text{Performance Latente} = \text{NAV} - \text{Book Value}
$$

$$
\text{Performance Latente} = 33 000 - 27 600 = +5 400\text{ €}
$$

Cela indique que la valeur de marché de votre portefeuille a augmenté de 5 400 € par rapport au coût total payé pour l'acquérir.

---

## ⚙️ Note sur les Méthodes de Prix de Revient

Pour déterminer le coût d'achat des positions ouvertes, LibreFolio utilise la méthode du [Coût Moyen Pondéré (CMP)](weighted-average-cost.md) comme algorithme par défaut pour le suivi des stocks :

- Chaque fois que vous achetez un actif, le coût unitaire moyen d'acquisition est mis à jour.
- Chaque fois que vous vendez un actif, la base de coût est réduite proportionnellement sur la base du CMP au moment de la vente, laissant inchangé le coût unitaire des parts restantes.
