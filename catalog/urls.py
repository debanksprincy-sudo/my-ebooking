from django.urls import path

from . import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("livre/<int:pk>/", views.book_detail, name="book_detail"),
    path("livre/<int:pk>/commander/", views.order_book, name="order_book"),
    path("avis/<str:order_token>/", views.submit_review, name="submit_review"),
    path("gestion-privee/", views.admin_login, name="admin_login"),
    path("gestion-privee/livres/", views.admin_books, name="admin_books"),
    path(
        "gestion-privee/livres/ajouter/",
        views.admin_add_book,
        name="admin_add_book",
    ),
    path(
        "gestion-privee/livres/<int:pk>/supprimer/",
        views.admin_delete_book,
        name="admin_delete_book",
    ),
    path(
        "gestion-privee/livres/<int:pk>/telecharger/",
        views.admin_download_book,
        name="admin_download_book",
    ),
    path("gestion-privee/avis/", views.admin_reviews, name="admin_reviews"),
    path(
        "gestion-privee/avis/<int:pk>/moderation/",
        views.moderate_review,
        name="moderate_review",
    ),
    path("gestion-privee/deconnexion/", views.admin_logout, name="admin_logout"),
]
