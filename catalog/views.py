import secrets
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import AdminCodeForm, BookForm, OrderForm, ReviewForm
from .models import Book, Order, Review


def catalog(request):
    books = Book.objects.filter(is_available=True)
    return render(request, "catalog/catalog.html", {"books": books})


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk, is_available=True)
    reviews = book.reviews.filter(is_approved=True)
    return render(
        request,
        "catalog/book_detail.html",
        {"book": book, "reviews": reviews, "order_form": OrderForm()},
    )


def order_book(request, pk):
    book = get_object_or_404(Book, pk=pk, is_available=True)
    if request.method != "POST":
        return redirect(book.get_absolute_url())
    form = OrderForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "catalog/book_detail.html",
            {
                "book": book,
                "reviews": book.reviews.filter(is_approved=True),
                "order_form": form,
            },
            status=400,
        )

    phone_number = settings.WHATSAPP_PHONE_NUMBER
    if not phone_number or not phone_number.isascii() or not phone_number.isdecimal():
        raise ImproperlyConfigured(
            "Configurez WHATSAPP_PHONE_NUMBER avec l'indicatif pays, uniquement des chiffres."
        )
    order = Order.objects.create(
        book=book,
        customer_name=form.cleaned_data["customer_name"],
        customer_phone=form.cleaned_data["customer_phone"],
        order_token=secrets.token_urlsafe(24),
    )
    review_url = request.build_absolute_uri(
        reverse("submit_review", kwargs={"order_token": order.order_token})
    )
    message = (
        f"Bonjour, je souhaite commander « {book.title} » "
        f"({book.price} {settings.CURRENCY}). "
        f"Nom : {order.customer_name}. Téléphone : {order.customer_phone}. "
        f"Après la commande, je pourrai déposer un avis ici : {review_url}"
    )
    return redirect(
        f"https://wa.me/{phone_number}?text={quote(message)}"
    )


def submit_review(request, order_token):
    order = get_object_or_404(Order, order_token=order_token)
    if hasattr(order, "review"):
        messages.info(request, "Un avis a déjà été envoyé pour cette commande.")
        return redirect(order.book.get_absolute_url())

    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.book = order.book
        review.order = order
        review.save()
        messages.success(
            request,
            "Merci ! Votre avis sera visible après modération par notre équipe.",
        )
        return redirect(order.book.get_absolute_url())
    return render(
        request,
        "catalog/review_form.html",
        {"form": form, "book": order.book},
        status=400 if request.method == "POST" else 200,
    )


def _admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.session.get("ebooking_admin"):
            return redirect("admin_login")
        return view(request, *args, **kwargs)

    return wrapped


def admin_login(request):
    if not settings.ADMIN_ACCESS_CODE_HASH:
        raise ImproperlyConfigured(
            "Configurez ADMIN_ACCESS_CODE_HASH avec un hash Django généré par make_password()."
        )
    form = AdminCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if check_password(form.cleaned_data["code"], settings.ADMIN_ACCESS_CODE_HASH):
            request.session.cycle_key()
            request.session["ebooking_admin"] = True
            return redirect("admin_books")
        form.add_error("code", "Code incorrect.")
    return render(request, "catalog/admin_login.html", {"form": form})


@_admin_required
def admin_books(request):
    books = Book.objects.all()
    return render(request, "catalog/admin_books.html", {"books": books})


@_admin_required
def admin_add_book(request):
    form = BookForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le livre a été ajouté au catalogue.")
        return redirect("admin_books")
    return render(request, "catalog/admin_book_form.html", {"form": form})


@require_POST
@_admin_required
def admin_delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    book.delete()
    messages.success(request, "Le livre et les avis associés ont été supprimés.")
    return redirect("admin_books")


@_admin_required
def admin_download_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if not book.pdf:
        raise Http404("Aucun fichier PDF n'est associé à ce livre.")
    try:
        pdf = book.pdf.open("rb")
    except FileNotFoundError as exc:
        raise Http404("Le fichier PDF est introuvable.") from exc
    return FileResponse(pdf, as_attachment=True, filename=book.pdf.name.rsplit("/", 1)[-1])


@_admin_required
def admin_reviews(request):
    reviews = Paginator(Review.objects.select_related("book", "order"), 25).get_page(
        request.GET.get("page")
    )
    return render(request, "catalog/admin_reviews.html", {"reviews": reviews})


@require_POST
@_admin_required
def moderate_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.is_approved = not review.is_approved
    review.save(update_fields=["is_approved"])
    messages.success(request, "La visibilité de l’avis a été mise à jour.")
    return redirect("admin_reviews")


@require_POST
@_admin_required
def admin_logout(request):
    request.session.pop("ebooking_admin", None)
    return redirect("admin_login")
