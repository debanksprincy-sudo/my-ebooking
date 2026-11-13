# My ebooking

Boutique Django de livres PDF pour enfants : catalogue public, commande par WhatsApp, dépôt d'avis à partir d'un lien de commande et espace privé pour gérer les livres et modérer les avis.

## Installation locale (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
```

Le numéro WhatsApp du vendeur est nécessaire pour activer les commandes. Saisissez-le avec l'indicatif international, uniquement des chiffres (par exemple `2250102030405`) :

```powershell
$env:WHATSAPP_PHONE_NUMBER = "VOTRE_NUMERO_INTERNATIONAL"
```

Le code admin communiqué ne doit pas être enregistré en clair dans le dépôt. Générez son hash Django ; la saisie est masquée, et seul le hash est affiché :

```powershell
$env:ADMIN_ACCESS_CODE_HASH = (python manage.py hash_admin_code)
```

Saisissez le code admin à l'invite. Le hash et le numéro WhatsApp doivent rester configurés dans l'environnement lors de chaque lancement. En déploiement, stockez-les dans le gestionnaire de secrets de la plateforme.

Lancez le site :

```powershell
python manage.py runserver
```

Le catalogue est accessible sur `http://127.0.0.1:8000/`. L'espace privé est sur `/gestion-privee/`. L'administration Django standard n'est pas exposée.

## Fonctionnement

- L'espace privé donne accès à l'ajout et à la suppression des livres, ainsi qu'à la modération (publication/masquage) des avis.
- Le clic sur « Commander sur WhatsApp » crée une commande, puis redirige vers le numéro vendeur avec le livre et les coordonnées du client préremplis.
- Chaque commande possède un lien d'avis aléatoire et non devinable envoyé dans la conversation WhatsApp. Seule cette URL permet de déposer un avis lié à une commande ; un seul avis est accepté par commande. Les avis restent invisibles jusqu'à leur approbation par l'admin.
- Les fichiers PDF sont conservés dans `private_books/` et ne sont téléchargeables que depuis l'espace admin authentifié. Les couvertures restent dans `media/`.
- WhatsApp ne confirme pas à l'application qu'une vente a été conclue. L'éligibilité aux avis repose donc sur la création de la commande via le site, et non sur une preuve de paiement.

Avant déploiement, configurez `DJANGO_SECRET_KEY` avec une clé aléatoire privée, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `WHATSAPP_PHONE_NUMBER` et `ADMIN_ACCESS_CODE_HASH`. Servez les fichiers de couverture depuis `MEDIA_ROOT` et gardez `PRIVATE_BOOK_ROOT` hors du répertoire des fichiers statiques/publics.

## Déploiement sur Render

1. Envoyez le projet dans un dépôt GitHub/GitLab privé. Ne versionnez jamais le code admin en clair, le hash, les clés secrètes, `db.sqlite3`, `media/` ou `private_books/`.
2. Dans Render, créez une base **PostgreSQL**. Utilisez son URL **interne** pour `DATABASE_URL` dans le service web.
3. Créez un **Web Service** relié au dépôt, runtime Python :
   - Build command : `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
   - Start command : `gunicorn my_ebooking.wsgi:application --bind 0.0.0.0:$PORT`
4. Configurez ces variables d'environnement sur le Web Service :

   | Variable | Valeur |
   | --- | --- |
   | `DJANGO_SECRET_KEY` | Une nouvelle clé aléatoire générée dans Render |
   | `DJANGO_DEBUG` | `False` |
   | `DATABASE_URL` | L'URL interne PostgreSQL fournie par Render |
   | `WHATSAPP_PHONE_NUMBER` | Numéro du vendeur avec indicatif international, chiffres uniquement |
   | `ADMIN_ACCESS_CODE_HASH` | Hash Django du code admin, jamais le code en clair |

   Render fournit `RENDER_EXTERNAL_HOSTNAME`, utilisé automatiquement pour les hôtes autorisés et la protection CSRF. Si vous configurez un domaine personnalisé, ajoutez-le à `DJANGO_ALLOWED_HOSTS` et son origine HTTPS à `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. Pour ne pas perdre les couvertures et PDF lors d'un redéploiement, ajoutez un **Persistent Disk** au service (fonctionnalité sur une offre payante), monté sur `/var/data`, puis ajoutez `RENDER_DISK_PATH=/var/data`. Sans disque persistant ou stockage objet externe, les fichiers ajoutés sur Render sont éphémères. La base PostgreSQL conserve séparément les livres, commandes et avis.
6. Dans Render, lancez le déploiement, puis ouvrez `https://<nom-du-service>.onrender.com/gestion-privee/`. Une fois connecté, ajoutez les livres.

Pour générer le hash à saisir dans Render, depuis PowerShell à la racine du projet, exécutez `python manage.py hash_admin_code`, saisissez le code à l'invite puis copiez le hash affiché dans la variable `ADMIN_ACCESS_CODE_HASH`. Ne collez jamais le code lui-même dans une variable, un commit ou un message. Toute modification des variables dans Render doit être suivie d'un redéploiement.

Après déploiement, testez la page d'accueil, l'ajout d'un livre (couverture et PDF), la commande WhatsApp et le lien d'avis. Conservez des sauvegardes PostgreSQL et des fichiers téléversés.
