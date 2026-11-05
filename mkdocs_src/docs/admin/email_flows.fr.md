# 📬 E-mail : liens et messages

Cette page décrit les messages que LibreFolio envoie une fois que l'e-mail fonctionne : les **liens** d'invitation et de réinitialisation du mot de passe, les **mots de passe oubliés**, les **limites** applicables à ces e-mails, la **vérification** des nouvelles adresses et l'avis de **changement d'adresse**.

L'e-mail doit d'abord fonctionner : les variables SMTP, l'onglet **E-mail** et l'e-mail de test se trouvent dans [E-mail](email.md), et ce qu'il faut vérifier lorsqu'un message ne part pas figure dans [E-mail : quand cela ne fonctionne pas](email_troubleshooting.md).

---

## 🌐 E-mails contenant un lien {: #public-url }

Un lien d'invitation ou de réinitialisation du mot de passe envoyé par e-mail est construit à partir de `LIBREFOLIO_PUBLIC_URL` uniquement : cette adresse, puis la page qui reçoit le lien, par exemple `https://librefolio.example.com/reset-password#token=…`. Jamais à partir de l'adresse utilisée par votre navigateur, ni de quoi que ce soit d'autre dans une requête.

- **Pourquoi.** N'importe qui peut envoyer à LibreFolio une requête qui indique une autre adresse. Si un lien était construit à partir de la requête, un inconnu pourrait faire envoyer par LibreFolio à l'un de vos utilisateurs un vrai lien vers un site lui appartenant, et récupérer sa partie secrète lorsque l'utilisateur l'ouvre.
- **Ce qu'il faut définir.** L'adresse à laquelle vos utilisateurs ouvrent LibreFolio, avec `http://` ou `https://` et un nom d'hôte, par exemple `https://librefolio.example.com` : pas de nom d'utilisateur ni de mot de passe, pas de `?` ni de `#`, pas d'espaces. C'est la même variable que la ligne de commande place devant les liens qu'elle affiche : voir [Comptes et inscriptions](configuration_accounts.md#accounts).
- **Sans elle**, ou avec une adresse qui enfreint ces règles, aucun e-mail contenant un lien n'est envoyé : un tel e-mail est refusé avec `EMAIL_LINKS_UNAVAILABLE`, alors que l'e-mail de test continue de fonctionner, et **Exiger la vérification de l'adresse e-mail** ne peut pas être activée ([Vérification de l'adresse e-mail](#verification)). Les liens que vous copiez, depuis la [ligne de commande](cli_tools.md) par exemple, restent inchangés.
- **Ce que dit l'e-mail** : il nomme votre instance par l'hôte de `LIBREFOLIO_PUBLIC_URL`, et indique combien de temps le lien reste valable : 7 jours pour une nouvelle invitation, 30 minutes pour un lien de réinitialisation, 24 heures pour un lien de vérification, 72 heures pour le lien d'installation de l'administrateur initial. Un lien ne fonctionne qu'une fois.
- **La partie secrète** du lien vient après `#` : les navigateurs ne l'envoient jamais au serveur, elle reste donc hors des journaux du serveur et du proxy.
- **Pour le vérifier** : lorsque l'e-mail est **Prêt**, Paramètres › Administration › E-mail affiche un avertissement si `LIBREFOLIO_PUBLIC_URL` n'est pas défini ou ne peut pas être utilisé, et le journal de démarrage contient une ligne ([Ce que dit le journal](email_troubleshooting.md#logs)). Une fois l'adresse utilisable, l'onglet affiche l'adresse et vérifie, depuis votre navigateur, que cette instance y répond : voir [L'adresse dans les liens envoyés par e-mail](email.md#links-check). Depuis n'importe où, `/api/v1/system/instance` affiche `"links": true` lorsque l'e-mail et l'adresse fonctionnent tous les deux.

---

## 📨 Liens envoyés par un administrateur {: #admin-links }

Un lien d'invitation ou de réinitialisation du mot de passe créé par un administrateur peut être envoyé par e-mail, au lieu d'être copié à la main. Tant que l'e-mail est **Prêt** et que `LIBREFOLIO_PUBLIC_URL` peut être utilisé ([E-mails contenant un lien](#public-url)), les boîtes de dialogue d'invitation et de réinitialisation de [Utilisateurs et invitations](users.md#send-by-email) affichent **Envoyer par e-mail** sous le lien :

1. Créez le lien comme d'habitude : **Inviter**, ou **Lien de réinitialisation du mot de passe** sur la ligne de la personne.
2. Pour une invitation, vérifiez l'adresse dans **Envoyer à** : elle est préremplie avec celle indiquée dans l'invitation, et vous pouvez la modifier. Un lien de réinitialisation n'a pas de champ : il est envoyé à l'adresse de son compte.
3. Pour une invitation, choisissez la **Langue de l'e-mail** : **La langue de l'instance** l'écrit dans la **Langue par défaut** de l'instance ([Paramètres globaux](settings.md)) ; choisissez English, Italiano, Français ou Español pour une personne qui en lit une autre. Un lien de réinitialisation est envoyé dans la langue de son compte. Pour définir la **Langue par défaut** avant qu'un administrateur ne l'ait enregistrée, placez `LIBREFOLIO_DEFAULT_LANGUAGE` dans le fichier `.env` (`en`, `it`, `fr` ou `es`) : voir [Variables d'environnement](configuration_accounts.md#accounts).
4. Cliquez sur **Envoyer par e-mail**. La boîte de dialogue indique *Envoyé à …* avec l'adresse et la langue dans laquelle l'e-mail a été rédigé, ou pourquoi l'e-mail n'est pas parti ([Erreurs d'envoi](email_troubleshooting.md#sending-errors)).

Les règles :

- **Le lien contenu dans l'e-mail commence par `LIBREFOLIO_PUBLIC_URL`**, quelle que soit l'**Adresse du serveur** affichée dans la boîte de dialogue : seule la partie secrète du lien provient de la boîte de dialogue. La boîte de dialogue le précise au-dessus du bouton.
- **Une invitation** est envoyée à l'adresse indiquée dans **Envoyer à**, ou sinon à celle indiquée dans l'invitation, dans la langue choisie dans **Langue de l'e-mail**, la **Langue par défaut** de l'instance sauf si vous en avez choisi une autre. Il s'agit uniquement de la langue de l'e-mail : elle ne devient pas la langue du compte que l'invitation crée. L'e-mail vous nomme comme la personne qui invite, et le précise lorsque le nouveau compte sera administrateur.
- **Un lien de réinitialisation du mot de passe** n'est envoyé qu'à l'adresse de son compte, dans la langue du compte, et uniquement tant que le compte est actif.
- **Seul un lien actif** est envoyé : un lien expiré, utilisé ou révoqué est refusé, et un nouveau lien doit être créé.
- Chaque e-mail compte dans la limite horaire.

---

## 🗝️ Mots de passe oubliés {: #forgot-password }

Une personne qui a oublié son mot de passe peut demander un lien de réinitialisation par e-mail, avec son nom d'utilisateur ou son adresse e-mail, sans se connecter. Sur la page de connexion, **Mot de passe oublié ?** ouvre un formulaire à cet effet lorsque des e-mails contenant un lien peuvent partir : e-mail **Prêt** et `LIBREFOLIO_PUBLIC_URL` utilisable. Sous le formulaire, un panneau fermé jusqu'au clic conserve la commande qu'un administrateur peut exécuter sur le serveur. Sinon, la page affiche cette commande, ouverte, sous l'avertissement *La récupération par e-mail n'est pas disponible sur cette instance. Réinitialisez votre mot de passe depuis le terminal du serveur, ou demandez à votre administrateur un lien de réinitialisation du mot de passe.* Lorsque la page ne peut pas lire la configuration de l'instance depuis le serveur, elle affiche seulement le conseil *Demandez à votre administrateur un lien de réinitialisation du mot de passe : il peut en créer un pour votre compte.* Un administrateur crée ce lien dans **Paramètres › Administration › Utilisateurs**, même sans e-mail ([Liens de réinitialisation du mot de passe](users.md#reset-links)).

C'est sûr parce que changer l'adresse e-mail d'un compte demande son mot de passe actuel ([Profil](../user/settings/profile.md)) : voir [Notes de sécurité](email_troubleshooting.md#security).

Cela fonctionne ainsi :

- **La même réponse pour tout le monde** : *Si un compte actif correspond, son propriétaire reçoit un e-mail contenant un lien pour choisir un nouveau mot de passe*, qu'un compte corresponde ou non. La recherche du compte et l'envoi de l'e-mail interviennent après la réponse, afin que personne ne puisse s'en servir pour découvrir quels comptes existent.
- **Le compte** est trouvé comme lors de la connexion, par nom d'utilisateur ou adresse e-mail. Seul un compte actif reçoit l'e-mail, à sa propre adresse et dans sa langue.
- **Le lien** fonctionne une fois, pendant 30 minutes, et remplace les liens de réinitialisation envoyés par les demandes précédentes au compte. Tant qu'un lien de réinitialisation créé par un administrateur est encore actif, rien n'est envoyé : une demande ne l'annule jamais.
- **Lorsque l'e-mail ou `LIBREFOLIO_PUBLIC_URL` n'est pas prêt**, la demande est refusée avec un court message, le même pour tout le monde.

Les limites :

| Limite | Au-delà |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` demandes par heure (20 par défaut) depuis la même adresse, un décompte partagé avec les inscriptions et les demandes de **Renvoyer le lien** ([Limites des e-mails d'activation et de réinitialisation du mot de passe](#activation-limits)) ; une adresse IPv6 compte par son /64, le bloc qu'un abonné détient généralement | La demande est refusée jusqu'à ce qu'une place se libère dans ce décompte, ou dans la limite horaire de l'instance si celle-ci attend plus longtemps ; la réponse indique combien de temps. |
| 3 demandes par heure pour le même nom d'utilisateur ou la même adresse e-mail, qu'un compte corresponde ou non | La demande est refusée jusqu'à ce que la plus ancienne ait une heure. |
| La limite horaire de l'instance, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | La demande est refusée jusqu'à ce qu'un e-mail puisse à nouveau être envoyé. |
| 3 e-mails par heure vers la même boîte aux lettres, quel que soit le compte destinataire et quelle que soit la façon dont son adresse est écrite | Rien n'est envoyé, et la réponse reste la même. |
| 1 e-mail toutes les 5 minutes, et 3 par heure, pour le même compte, y compris les liens de réinitialisation créés par un administrateur | Rien n'est envoyé, et la réponse reste la même. Deux demandes au même moment ne peuvent pas toutes deux envoyer. |

La limite par compte prend en compte les liens de réinitialisation du compte dans la base de données. Les autres sont conservées dans la mémoire de chaque processus serveur : avec plusieurs processus, chacun tient son propre décompte, et un redémarrage les oublie. Un e-mail de réinitialisation qui n'est pas parti compte quand même, pour le compte et pour la boîte aux lettres.

**Une boîte aux lettres, quelle que soit la façon dont son adresse est écrite.** La limite par boîte aux lettres considère les alias d'une adresse comme une seule boîte aux lettres : les majuscules ne comptent pas, ni un `+tag` sur n'importe quel domaine (`name+news@example.com` est `name@example.com`), ni les points d'une adresse Gmail, où `googlemail.com` est `gmail.com` (`first.last@googlemail.com` est `firstlast@gmail.com`). Les limites des [e-mails de vérification](#verification-limits) et des [avis de changement d'e-mail](#email-change-notice) se comptent de la même façon. Chaque e-mail est tout de même envoyé à l'adresse exactement telle que le compte l'a enregistrée. Une boîte aux lettres qui accepte le courrier sous n'importe quel nom, comme un domaine catch-all ou `anything@user.fastmail.com` de Fastmail, compte chaque nom séparément : seule la limite horaire de l'instance les retient.

**Derrière un proxy inverse**, l'adresse qui compte est celle du visiteur, telle que LibreFolio la lit (voir [L'adresse du visiteur](connection_proxy.md#client-address)) :

- Lorsque `LIBREFOLIO_CLIENT_IP_HEADER` nomme l'en-tête que votre proxy définit avec l'adresse du visiteur (`Fly-Client-IP` sur Fly.io, `X-Real-IP` depuis Nginx), LibreFolio la lit à cet endroit. Ne la définissez que si chaque requête traverse ce proxy : un visiteur qui atteint LibreFolio directement pourrait écrire l'en-tête.
- Sinon, c'est l'adresse que le serveur (uvicorn) voit, qui ne prend l'adresse du visiteur dans l'en-tête `X-Forwarded-For` du proxy que lorsque l'adresse du proxy figure dans `FORWARDED_ALLOW_IPS` (`127.0.0.1` lorsqu'il n'est pas défini). Listez-y les adresses ou réseaux de votre proxy, par exemple `172.18.0.0/16`, jamais `*` : avec `*`, uvicorn prend la première adresse de l'en-tête, que le visiteur peut écrire.
- **Un proxy auquel LibreFolio ne fait pas confiance, sur une adresse locale** (un réseau Docker, votre propre réseau ou votre VPN), par exemple un conteneur proxy devant l'image Docker, la configuration habituelle : ces limites par adresse excluent les requêtes qui le traversent, afin que les requêtes d'un visiteur ne puissent pas épuiser le décompte des demandes via **Mot de passe oublié ?**, des demandes de **Renvoyer le lien** et des inscriptions pour tout le monde. Les limites par nom d'utilisateur ou adresse e-mail, par compte et par boîte aux lettres, ainsi que la limite horaire de l'instance, les comptent toujours. Le journal avertit une fois par processus serveur, et les contrôles de sécurité le signalent comme un avertissement de `platform.client_address` (voir [L'adresse du visiteur](connection_proxy.md#client-address)).
- **Un proxy auquel LibreFolio ne fait pas confiance, sur une adresse publique**, par exemple un CDN : chaque visiteur partage l'adresse du proxy et son décompte, donc les premières `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` requêtes de n'importe qui épuisent le décompte de ces requêtes à travers le proxy pour tout le monde, pendant jusqu'à une heure. Indiquez le proxy à LibreFolio.

---

## 🚦 Limites des e-mails d'activation et de réinitialisation du mot de passe {: #activation-limits }

Les e-mails qui activent un compte et ceux qui réinitialisent un mot de passe sont retenus par **deux compteurs**, les mêmes pour chaque façon de les demander. Chacun compte sur les 60 dernières minutes, dans la mémoire de chaque processus serveur.

| Compteur | Variable | Valeur par défaut | Ce qu'il compte |
| --- | --- | --- | --- |
| **Par adresse** | `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | 20 par heure | Les e-mails qui partent pour une adresse client (une adresse IPv6 par son /64), dans un seul décompte : les inscriptions, les demandes de **Renvoyer le lien** avec le bon mot de passe, et les demandes via **Mot de passe oublié ?** pour un compte qui existe. Les tentatives ne sont pas comptées : un mauvais mot de passe, une demande pour un nom qu'aucun compte ne possède, ou une demande refusée par une autre limite ne lui coûte rien |
| **Par instance** | `LIBREFOLIO_SMTP_MAX_PER_HOUR` | 50 par heure | Chaque e-mail envoyé par l'instance : activations, réinitialisations, invitations, avis |

Trois autres limites restent inchangées. Ce ne sont pas des compteurs d'e-mails d'activation, et elles importent rarement pour un compte dont l'e-mail a été retenu, puisque rien n'a encore atteint sa boîte aux lettres :

- la limite de connexion sur les **mots de passe erronés** ([Connexions échouées](configuration_accounts.md#login-limit)), que les demandes de **Renvoyer le lien** partagent avec la page de connexion ;
- **3 e-mails par heure vers la même boîte aux lettres**, afin que LibreFolio ne puisse pas servir à inonder l'adresse de quelqu'un d'autre ;
- **1 e-mail toutes les 5 minutes, et 3 par heure, pour le même compte**, pour les demandes de **Renvoyer le lien**.

Le compteur par adresse compte les **e-mails qui partent**, pas les tentatives. Il est consulté en premier, donc une demande est refusée immédiatement, avant la vérification du mot de passe, lorsque le décompte est plein ; il est débité au dernier moment, lorsque l'e-mail est sur le point de partir, et par rien d'autre : les mauvais mots de passe ont leur propre limite, une demande pour un nom qu'aucun compte ne possède ne coûte rien (et, pour **Mot de passe oublié ?**, la réponse est la même, que le compte corresponde ou non), et une demande de **Renvoyer le lien** refusée par la limite par compte ou par boîte aux lettres ne dépense rien. Un e-mail que le serveur SMTP refuse ensuite reste compté : il a été tenté.

Lorsqu'un compteur retient une demande, la réponse indique combien de secondes attendre, et ce temps est exact : c'est le **plus long** des temps d'attente des compteurs qui l'ont retenue, donc la même demande effectuée alors passe, sauf si d'autres personnes du même réseau ont utilisé la place entre-temps (la réponse indique alors le nouveau temps).

**Un exemple.** Un bureau disposant d'une seule adresse Internet et d'une limite de 20. Vingt collègues s'inscrivent entre 9 h 00 et 9 h 40, et leurs vingt e-mails partent. À 9 h 45, le 21e, Mario, s'inscrit : son compte est créé, mais son e-mail est retenu, et la page lui indique de réessayer dans environ 15 minutes, le temps que l'e-mail de 9 h 00 quitte le décompte à 10 h 00. À 9 h 46, il se connecte et demande à nouveau le lien : le même compteur le refuse, pour 14 minutes. À 10 h 00, il redemande avec son nom d'utilisateur et son mot de passe, et le lien part.

Le compteur par adresse est partagé volontairement, avec une conséquence à connaître : lorsqu'un réseau a épuisé son décompte avec des inscriptions, **Mot de passe oublié ?** depuis ce réseau attend aussi, jusqu'à ce qu'une place se libère. Augmentez `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` pour un réseau où beaucoup de personnes s'inscrivent ensemble, comme une école ou un bureau, puis redémarrez.

---

## ✅ Vérification de l'adresse e-mail {: #verification }

Lorsque l'option **Exiger la vérification de l'adresse e-mail** est activée, un nouveau compte ne peut pas se connecter tant que son propriétaire n'a pas confirmé l'adresse au moyen d'un lien que LibreFolio envoie par e-mail au compte. L'interrupteur se trouve dans **Paramètres › Administration › Paramètres globaux**, dans la catégorie **Sécurité** ([Paramètres globaux](settings.md)), et il est désactivé par défaut.

- **Qui attend** : chaque compte créé depuis la page d'inscription tant que l'interrupteur est activé, y compris ceux ouverts avec une invitation. Le premier compte d'une nouvelle instance, son administrateur, n'attend jamais, pas plus que l'administrateur que LibreFolio crée à partir de `LIBREFOLIO_ADMIN_EMAIL`, que son lien d'installation active. Les comptes créés avec `user create` en [ligne de commande](cli_tools.md) n'attendent pas non plus, pas plus que les comptes qui existent déjà.
- **Juste après l'inscription**, la page de connexion indique : *Compte créé. Nous vous envoyons un e-mail contenant un lien pour l'activer : ouvrez-le dans les 24 heures, puis connectez-vous. Pas d'e-mail après quelques minutes ? Vérifiez le dossier de courrier indésirable, puis connectez-vous avec votre nom d'utilisateur et votre mot de passe : un nouveau lien vous sera proposé.* Lorsque l'adresse client avait déjà reçu, au cours de la dernière heure, les e-mails correspondant à `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` inscriptions (20 par défaut), ou que la limite horaire de l'instance est épuisée, aucun e-mail ne part, et la page l'indique à la place, avec le temps d'attente : *Compte créé, mais l'e-mail d'activation n'a pas pu partir maintenant. Réessayez dans environ N minutes : connectez-vous avec votre nom d'utilisateur et votre mot de passe, et un nouveau lien vous sera proposé.* N est exact : c'est le temps jusqu'à ce que les deux compteurs admettent un nouvel e-mail ([Limites des e-mails d'activation et de réinitialisation du mot de passe](#activation-limits)). Derrière un proxy inverse auquel LibreFolio ne fait pas confiance, sur une adresse locale (la configuration Docker habituelle), rien n'est compté par adresse, donc ce second texte ne s'affiche jamais ([Mots de passe oubliés](#forgot-password)). Dans tous les cas, le compte est créé et attend.
- **L'e-mail**, *Confirmez votre adresse e-mail*, part juste après cette réponse, sauf si une limite le retient ([Limites des e-mails de vérification](#verification-limits)), dans la **Langue par défaut** de l'instance : un nouveau compte n'a pas encore de langue propre. Son bouton, **Confirmer mon adresse e-mail**, ouvre un lien qui commence par `LIBREFOLIO_PUBLIC_URL` ([E-mails contenant un lien](#public-url)) et fonctionne une fois, pendant 24 heures.
- **Tant que l'adresse n'est pas confirmée**, le compte ne peut pas se connecter. Se connecter avec le bon mot de passe indique que l'adresse n'est pas encore vérifiée, et propose **Renvoyer le lien** : un nouveau lien, qui invalide les précédents. Avec un mauvais mot de passe, la connexion donne son refus habituel, afin que personne n'apprenne plus que lors de toute autre tentative.
- **Une fois que le propriétaire a confirmé**, le compte est actif, et son propriétaire revient sur la page de connexion avec une confirmation. Ce que la personne voit, étape par étape : *Si LibreFolio vous demande de confirmer votre adresse e-mail* dans [Premiers pas](../user/getting-started.md).
- **Ouvrir le lien ne confirme rien** : cela affiche une page de LibreFolio avec un bouton, **Confirmer mon adresse e-mail**, et seul le clic sur ce bouton consomme le lien. Cela s'explique par les filtres de messagerie qui analysent les liens, tels que Microsoft Defender Safe Links : ils ouvrent les liens d'un message dans un navigateur qui exécute des scripts, et si l'ouverture suffisait, le filtre activerait le compte à la place de son propriétaire. Une telle ouverture ne dépense rien ; le lien reste valable pour son propriétaire. Quelqu'un qui ouvre un lien sans s'être inscrit n'a qu'à fermer la page.

### 🔀 Activer et désactiver {: #verification-switch }

- **Il ne s'active que lorsque des e-mails contenant un lien peuvent partir** : e-mail **Prêt** ([Paramètres › Administration › E-mail](email.md#email-tab)) et `LIBREFOLIO_PUBLIC_URL` utilisable ([E-mails contenant un lien](#public-url)). D'ici là, tant qu'il est désactivé, l'interrupteur est grisé, avec l'indication *Nécessite qu'un e-mail contenant un lien puisse partir : configurez d'abord SMTP et LIBREFOLIO_PUBLIC_URL (Paramètres › Administration › E-mail).* Si cela change entre le moment où vous ouvrez l'onglet et votre enregistrement, l'enregistrement est refusé — *La vérification de l'adresse e-mail nécessite qu'un e-mail contenant un lien puisse partir, et aucun ne le peut actuellement : vérifiez Paramètres › Administration › E-mail.* — et rien n'en est enregistré.
- **Le désactiver fonctionne toujours.** Les comptes déjà en attente continuent d'attendre : leurs liens fonctionnent toujours, tout comme **Renvoyer le lien**. Pour en laisser entrer un immédiatement, activez-le ([Comptes en attente](#verification-waiting)).
- **Tant qu'il est activé, l'enregistrement des autres paramètres fonctionne toujours**, même si l'e-mail a cessé de fonctionner depuis.
- **Si l'e-mail cesse de fonctionner alors qu'il est activé** — le serveur ou une variable cesse de fonctionner — plus personne ne peut s'inscrire, pas même avec une invitation, qui reste valable : la page d'inscription indique *L'inscription n'est pas possible pour le moment : cette instance ne peut pas envoyer l'e-mail de vérification. Réessayez plus tard, ou demandez à son administrateur.*, et aucun compte n'est créé. Seul le premier compte d'une nouvelle instance est autorisé. La demande de **Renvoyer le lien** échoue de la même manière. Corrigez l'e-mail ([Quand cela ne fonctionne pas](email_troubleshooting.md#troubleshooting)), ou désactivez l'interrupteur.

### ⏳ Comptes en attente {: #verification-waiting }

Dans **Paramètres › Administration › Utilisateurs**, un compte en attente affiche le badge **En attente de vérification**, et non **Désactivé**, même une fois son lien expiré. Survolez le badge, ou ouvrez la ligne, pour voir l'indication : son propriétaire n'a pas encore ouvert le lien, la connexion en propose un nouveau, et **Réactiver** laisse entrer le compte immédiatement.

- **Il occupe une place** de la limite d'utilisateurs (`LIBREFOLIO_MAX_USERS`) tant que son lien est actif, comme une invitation ouverte. Lorsque le dernier lien envoyé expire, 24 heures plus tard, la place est de nouveau libre, et une demande de **Renvoyer le lien** nécessite alors une place libre : sur une instance complète, son propriétaire est invité à vous en faire la demande.
- **Pour le laisser entrer sans l'e-mail**, cliquez sur **Réactiver** sur sa ligne ([Comptes en attente de leur e-mail](users.md#waiting)), ou exécutez `user activate` en [ligne de commande](cli_tools.md) : il peut se connecter immédiatement, et les liens déjà envoyés cessent de fonctionner. Tant que son lien est actif, cela n'occupe pas de place supplémentaire, puisque sa place est déjà comptée : **Réactiver** fonctionne même sur une instance complète, et `user activate` n'affiche aucun avertissement de limite. Une fois le lien expiré, le réactiver nécessite une place libre, comme pour tout compte désactivé.
- **Pour le refuser**, supprimez-le ([Supprimer un compte](users.md#delete)), ou désactivez-le : avec `user deactivate` en ligne de commande, ou avec l'API d'administration (`PATCH /api/v1/users/{id}` avec `is_active: false`). Désactivé, il cesse d'attendre : ses liens cessent de fonctionner, sa place est libre, sa ligne indique **Désactivé** à partir de ce moment, et la connexion indique à son propriétaire que le compte est désactivé. L'onglet Utilisateurs lui-même ne propose pas de **Désactiver** pour un compte qui n'est pas actif : là, **Supprimer** est la solution.

### 📏 Limites des e-mails de vérification {: #verification-limits }

| Limite | Au-delà |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` e-mails par heure (20 par défaut) depuis la même adresse, en comptant les e-mails qui partent : les inscriptions, les demandes de **Renvoyer le lien** avec le bon mot de passe et les demandes via **Mot de passe oublié ?** pour un compte qui existe ; une adresse IPv6 compte par son /64 | Les nouveaux comptes suivants sont tout de même créés et attendent, mais leurs e-mails ne partent pas : la page de connexion l'indique juste après l'inscription, avec le temps d'attente, et leurs propriétaires demandent à nouveau le lien depuis la page de connexion une fois ce temps écoulé. La demande de **Renvoyer le lien** est refusée pendant le même temps. |
| La limite propre à la connexion sur les mots de passe erronés, partagée avec la page de connexion : 10 toutes les 15 minutes pour le même nom d'utilisateur ou la même adresse e-mail, 50 depuis la même adresse (voir [Connexions échouées](configuration_accounts.md#login-limit)) | La demande est refusée avant la vérification du mot de passe : la page indique dans combien de minutes réessayer. Le bon mot de passe efface les échecs liés à la saisie. |
| 1 e-mail toutes les 5 minutes, et 3 par heure, pour le même compte, y compris l'e-mail de l'inscription | La demande est refusée : la page indique dans combien de minutes réessayer. |
| 3 e-mails par heure vers la même boîte aux lettres, quel que soit le compte destinataire et quelle que soit la façon dont son adresse est écrite ([Mots de passe oubliés](#forgot-password)) : l'e-mail d'une inscription et les liens envoyés à nouveau également, et uniquement les e-mails qui sont partis | La demande de **Renvoyer le lien** est refusée : la page indique dans combien de minutes réessayer. Après une inscription, le compte est créé et attend, mais aucun e-mail ne part, et rien ne prévient son propriétaire : la page affiche son texte habituel, qui indique déjà quoi faire (chercher dans le dossier de courrier indésirable, puis se connecter pour qu'un nouveau lien soit proposé). |
| La limite horaire de l'instance, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | La demande est refusée jusqu'à ce qu'un e-mail puisse à nouveau être envoyé. Une inscription effectuée alors que la limite est épuisée est retenue comme une inscription au-delà de la limite de son adresse. |
| Une place libre, une fois le lien du compte expiré | La demande est refusée : son propriétaire est invité à vous en faire la demande. |

**Ce qui reste invisible.** Après une inscription, *Nous vous envoyons un e-mail* signifie que l'e-mail est en file d'attente, pas qu'il a été remis : il part après la réponse, et il peut encore ne pas partir. La limite de 3 e-mails de vérification par heure de la boîte aux lettres, la limite horaire de l'instance, un échec SMTP, l'e-mail ou `LIBREFOLIO_PUBLIC_URL` qui a cessé de fonctionner entre-temps, un redémarrage : rien de tout cela n'atteint la page. Seul le journal l'indique, avec `Verification email: not sent` ou `Verification email: the request failed` ([Ce que dit le journal](email_troubleshooting.md#logs)), et un redémarrage avant que l'e-mail ne parte ne laisse aucune ligne du tout. Le compte reste en attente, avec sa retenue, et une demande de **Renvoyer le lien** permet de le récupérer ; c'est pourquoi le texte de la page indique à la personne quoi faire lorsque rien n'arrive. La limite de la boîte aux lettres n'est volontairement pas vérifiée avant la réponse : une inscription qui répondrait différemment lorsque la boîte aux lettres vient de recevoir des e-mails révélerait à quiconque s'inscrit avec l'adresse de quelqu'un d'autre si cette boîte aux lettres les reçoit.

Un lien dont l'e-mail n'est pas parti ne compte ni pour le compte ni pour la boîte aux lettres. Si le compte cesse d'attendre entre-temps — parce que son adresse a été confirmée, ou parce qu'un administrateur l'a activé ou désactivé — aucun nouveau lien n'est envoyé. Les limites par adresse et par boîte aux lettres sont conservées dans la mémoire de chaque processus serveur : avec plusieurs processus, chacun tient son propre décompte, et un redémarrage les oublie. Derrière un proxy inverse, l'adresse qui compte suit les règles données dans [Mots de passe oubliés](#forgot-password).

---

## 🔔 Changements d'adresse e-mail {: #email-change-notice }

Lorsque quelqu'un change l'adresse e-mail de son compte, dans [Profil](../user/settings/profile.md), LibreFolio écrit à l'adresse que le compte avait **avant** :

- **Uniquement à l'ancienne adresse** : la nouvelle ne reçoit rien.
- **Rien de la nouvelle adresse, et aucun nom d'utilisateur** : l'e-mail indique seulement que l'adresse a changé, sans aucune partie de la nouvelle, pas même son domaine, et il commence par un simple « Bonjour, » ([Notes de sécurité](email_troubleshooting.md#security)).
- **Aucun lien.** Il indique au propriétaire que, si le changement n'est pas de son fait, quelqu'un utilise peut-être son compte : qu'il change le mot de passe immédiatement s'il le peut encore, et qu'il vous prévienne.
- **Dans la langue du compte.** Il nomme votre instance par l'hôte de `LIBREFOLIO_PUBLIC_URL`, avec son port s'il en a un, ou « LibreFolio » lorsque la variable n'est pas définie ou ne peut pas être utilisée : sans lien à l'intérieur, l'avis n'en a pas besoin.
- **Après le changement** : l'e-mail part après la réponse, et le changement n'attend jamais celui-ci. Si l'e-mail est désactivé, rien n'est envoyé, et le journal l'indique dans une ligne d'information, pas un avertissement. L'avis compte dans la limite horaire comme tout e-mail.
- **Au plus 3 par heure pour un compte, et 3 par heure vers la même boîte aux lettres**, quelle que soit la façon dont son adresse est écrite ([Mots de passe oubliés](#forgot-password)). Au-delà de l'une ou de l'autre, le changement est tout de même effectué et l'avis est ignoré. Sans ces limites, un compte pourrait faire pointer son e-mail vers n'importe quelle adresse et le changer à nouveau, pour faire écrire votre instance à cette adresse.
- **Pas pour les majuscules seules.** Changer uniquement les majuscules des lettres A à Z, par exemple `Anna@example.com` pour `anna@example.com`, n'est pas un changement d'adresse, donc aucun avis n'est envoyé. Les lettres accentuées comptent comme différentes : `Émile@example.com` pour `émile@example.com` est un changement, avec son avis.

---

## 🔗 Voir aussi

- 📄 **[E-mail](email.md)** — Où se trouve la configuration, Les variables, Exemples, …
- 📄 **[E-mail : quand cela ne fonctionne pas](email_troubleshooting.md)** — Quand cela ne fonctionne pas, Notes de sécurité
