from getpass import getpass

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Génère un hash Django du code admin saisi sans afficher le code."

    def handle(self, *args, **options):
        code = getpass("Saisissez le code administrateur : ")
        confirmation = getpass("Confirmez le code administrateur : ")
        if not code or code != confirmation:
            raise CommandError("Les codes sont vides ou ne correspondent pas.")
        self.stdout.write(make_password(code))
