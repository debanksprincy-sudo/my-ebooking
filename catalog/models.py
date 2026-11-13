from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateBookStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_BOOK_ROOT)


private_pdf_storage = PrivateBookStorage()


class Book(models.Model):
    title = models.CharField("titre", max_length=180)
    author = models.CharField("auteur", max_length=120, blank=True)
    description = models.TextField("description")
    price = models.DecimalField(
        "prix", max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    cover = models.ImageField("couverture", upload_to="covers/", blank=True)
    pdf = models.FileField(
        "livre PDF", upload_to="books/", storage=private_pdf_storage, blank=True
    )
    is_available = models.BooleanField("disponible", default=True)
    created_at = models.DateTimeField("ajouté le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "livre"
        verbose_name_plural = "livres"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("book_detail", kwargs={"pk": self.pk})


class Order(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="orders")
    customer_name = models.CharField("nom du client", max_length=120)
    customer_phone = models.CharField("téléphone du client", max_length=32)
    order_token = models.CharField("code de commande", max_length=32, unique=True)
    created_at = models.DateTimeField("commandé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "commande"
        verbose_name_plural = "commandes"

    def __str__(self):
        return f"{self.book.title} — {self.customer_name}"


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="review"
    )
    customer_name = models.CharField("nom affiché", max_length=120)
    rating = models.PositiveSmallIntegerField(
        "note", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("commentaire", max_length=1200)
    is_approved = models.BooleanField("publié", default=False)
    created_at = models.DateTimeField("envoyé le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "avis"
        verbose_name_plural = "avis"

    def __str__(self):
        return f"{self.rating}/5 — {self.book.title}"
