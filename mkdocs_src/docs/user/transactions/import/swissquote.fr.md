# <img src="https://www.swissquote.com/favicon.ico" alt=""> Swissquote

!!! warning "Bêta — les retours de la communauté sont les bienvenus"

    Ce plugin a été développé à partir de **fichiers d'export d'exemple** et se trouve actuellement en **bêta**. Nous serons ravis de recevoir tout signalement pour l'améliorer ou pour mettre à jour la documentation sur la façon d'obtenir l'export.

## 📥 Comment exporter

Exportez votre historique de transactions au format **CSV** depuis Swissquote, puis importez-le dans LibreFolio. Pour le déroulement pas à pas de l'import, consultez le **[Guide d'importation](how-to.md)**.

## 🔄 Ce qui est importé

| Dans l'export (**Transaction**) | Importé comme |
|:--------------------------------|:------------|
| Achat | **Achat** |
| Vente | **Vente** |
| Dividende | **Dividende** |
| Intérêt, Intérêts | **Intérêt** |
| Impôt, Retenue | **Impôt** |
| Frais de conservation, tout autre frais | **Frais** |
| Débit | **Retrait** |
| Crédit | **Dépôt** |
| Crédit Forex + débit Forex, même **N° d'ordre** | Une paire de **changes de devises** liés |

**Conversion de devise.** Les deux jambes d'une conversion, un **crédit Forex** et un **débit Forex**
portant le même **N° d'ordre**, deviennent deux transactions de **change de devises** liées : l'argent sortant dans une
devise et l'argent entrant dans l'autre. Chaque jambe conserve sa propre date et son propre **Montant net**.

## 📝 Notes

- Développé à partir d'exports d'exemple — certains cas limites peuvent ne pas encore être couverts.
- Les coûts et les intérêts courus d'une opération sont inscrits dans sa description et ne sont pas importés comme des transactions distinctes.
- Les lignes que LibreFolio ne reconnaît pas sont listées dans un avertissement orange, avec un lien pour ouvrir un ticket sur GitHub ; un second avertissement liste les lignes qu'il ne parvient pas à lire.
- Vous avez trouvé un problème ou vous souhaitez documenter les étapes de l'export ? [Ouvrez un signalement](../../../community/contribute.md) — les contributions sont les bienvenues !

## 🚧 Limitations connues

- **Seule une paire valide de jambes Forex est importée.** Une jambe Forex est écartée et listée dans l'avertissement orange avec le lien pour ouvrir un ticket (ajoutez cette conversion de devise manuellement) lorsque :
    - son partenaire est absent (aucune autre jambe avec le même **N° d'ordre**) ;
    - l'ordre comporte plus de deux jambes ;
    - une jambe comporte des **Coûts** (le fichier ne précise pas si le coût est compris dans son **Montant net** ou s'il en est exclu) ;
    - les deux jambes sont dans la même devise, ou sont toutes deux des crédits ou toutes deux des débits.
- **Quelque chose ne va pas ?** Veuillez [ouvrir un signalement](../../../community/contribute.md), avec un fichier d'exemple anonymisé.
