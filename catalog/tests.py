from urllib.parse import parse_qs, urlparse

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Book, Order, Review


class StorefrontTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Le petit nuage",
            description="Une histoire douce.",
            price="2500.00",
        )

    def test_catalogue_shows_available_books_only(self):
        hidden_book = Book.objects.create(
            title="Livre masqué",
            description="Non publié.",
            price="1000.00",
            is_available=False,
        )

        response = self.client.get(reverse("catalog"))

        self.assertContains(response, self.book.title)
        self.assertNotContains(response, hidden_book.title)

    @override_settings(WHATSAPP_PHONE_NUMBER="2250102030405")
    def test_order_redirects_to_whatsapp_and_creates_review_token(self):
        response = self.client.post(
            reverse("order_book", args=[self.book.pk]),
            {"customer_name": "Awa", "customer_phone": "0700000000"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://wa.me/2250102030405?"))
        order = Order.objects.get(book=self.book)
        self.assertEqual(order.customer_name, "Awa")
        message = parse_qs(urlparse(response["Location"]).query)["text"][0]
        self.assertIn(order.order_token, message)

    def test_order_page_does_not_create_order_without_post(self):
        response = self.client.get(reverse("order_book", args=[self.book.pk]))

        self.assertRedirects(response, self.book.get_absolute_url())
        self.assertEqual(Order.objects.count(), 0)

    @override_settings(WHATSAPP_PHONE_NUMBER="")
    def test_order_requires_seller_whatsapp_configuration(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.post(
                reverse("order_book", args=[self.book.pk]),
                {"customer_name": "Awa", "customer_phone": "0700000000"},
            )
        self.assertEqual(Order.objects.count(), 0)

    def test_review_requires_a_valid_order_token_and_is_moderated(self):
        order = Order.objects.create(
            book=self.book,
            customer_name="Awa",
            customer_phone="0700000000",
            order_token="secure-order-token",
        )
        review_url = reverse("submit_review", args=[order.order_token])
        payload = {
            "customer_name": "Awa",
            "rating": 5,
            "comment": "Une très belle histoire.",
        }

        self.assertEqual(self.client.get(reverse("submit_review", args=["unknown"])).status_code, 404)
        response = self.client.post(review_url, payload)

        self.assertRedirects(response, self.book.get_absolute_url())
        review = Review.objects.get(order=order)
        self.assertFalse(review.is_approved)
        self.assertEqual(review.rating, 5)
        self.assertEqual(
            self.client.post(review_url, payload).status_code, 302
        )
        self.assertEqual(Review.objects.filter(order=order).count(), 1)

    def test_review_rating_is_limited_to_five_stars(self):
        order = Order.objects.create(
            book=self.book,
            customer_name="Awa",
            customer_phone="0700000000",
            order_token="another-secure-order",
        )

        response = self.client.post(
            reverse("submit_review", args=[order.order_token]),
            {"customer_name": "Awa", "rating": 6, "comment": "Avis."},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Review.objects.exists())

    def test_only_approved_reviews_are_public(self):
        order = Order.objects.create(
            book=self.book,
            customer_name="Awa",
            customer_phone="0700000000",
            order_token="pending-review-order",
        )
        review = Review.objects.create(
            book=self.book,
            order=order,
            customer_name="Awa",
            rating=5,
            comment="En attente de modération.",
        )

        response = self.client.get(self.book.get_absolute_url())
        self.assertNotContains(response, review.comment)

        review.is_approved = True
        review.save(update_fields=["is_approved"])
        response = self.client.get(self.book.get_absolute_url())
        self.assertContains(response, review.comment)


@override_settings(ADMIN_ACCESS_CODE_HASH=make_password("local-test-code"))
class PrivateAdminTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Le petit nuage",
            description="Une histoire douce.",
            price="2500.00",
        )

    def test_admin_routes_require_login(self):
        response = self.client.get(reverse("admin_books"))

        self.assertRedirects(response, reverse("admin_login"))
        self.assertEqual(self.client.get(reverse("admin_reviews")).status_code, 302)

    def test_admin_login_adds_books_and_logs_out(self):
        login_response = self.client.post(
            reverse("admin_login"), {"code": "local-test-code"}
        )
        self.assertRedirects(login_response, reverse("admin_books"))

        response = self.client.post(
            reverse("admin_add_book"),
            {
                "title": "Le jardin magique",
                "author": "A. Diallo",
                "description": "Un conte.",
                "price": "3000.00",
                "is_available": "on",
                "pdf": SimpleUploadedFile("conte.pdf", b"%PDF-1.4 contenu"),
            },
        )
        self.assertRedirects(response, reverse("admin_books"))
        added_book = Book.objects.get(title="Le jardin magique")
        self.addCleanup(added_book.pdf.delete, save=False)

        self.client.post(reverse("admin_logout"))
        self.assertRedirects(self.client.get(reverse("admin_books")), reverse("admin_login"))

    def test_admin_rejects_non_pdf_upload(self):
        self.client.post(reverse("admin_login"), {"code": "local-test-code"})

        response = self.client.post(
            reverse("admin_add_book"),
            {
                "title": "Fichier incorrect",
                "description": "Doit échouer.",
                "price": "1000.00",
                "pdf": SimpleUploadedFile("document.txt", b"texte"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Book.objects.filter(title="Fichier incorrect").exists())

    def test_admin_rejects_file_with_pdf_extension_but_invalid_content(self):
        self.client.post(reverse("admin_login"), {"code": "local-test-code"})

        response = self.client.post(
            reverse("admin_add_book"),
            {
                "title": "Faux PDF",
                "description": "Doit échouer.",
                "price": "1000.00",
                "pdf": SimpleUploadedFile("faux.pdf", b"ceci n'est pas un PDF"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Book.objects.filter(title="Faux PDF").exists())

    def test_admin_can_moderate_and_delete_with_post(self):
        order = Order.objects.create(
            book=self.book,
            customer_name="Awa",
            customer_phone="0700000000",
            order_token="moderation-order",
        )
        review = Review.objects.create(
            book=self.book,
            order=order,
            customer_name="Awa",
            rating=4,
            comment="Très bien.",
        )
        self.client.post(reverse("admin_login"), {"code": "local-test-code"})

        self.assertEqual(
            self.client.post(reverse("moderate_review", args=[review.pk])).status_code,
            302,
        )
        review.refresh_from_db()
        self.assertTrue(review.is_approved)
        self.assertEqual(
            self.client.post(reverse("admin_delete_book", args=[self.book.pk])).status_code,
            302,
        )
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_pdf_download_is_limited_to_logged_in_admin(self):
        self.client.post(reverse("admin_login"), {"code": "local-test-code"})
        response = self.client.get(reverse("admin_add_book"))
        self.assertEqual(response.status_code, 200)

        self.client.post(reverse("admin_logout"))
        response = self.client.get(reverse("admin_download_book", args=[self.book.pk]))
        self.assertRedirects(response, reverse("admin_login"))
