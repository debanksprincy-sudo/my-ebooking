from django import forms

from .models import Book, Review


class AdminCodeForm(forms.Form):
    code = forms.CharField(
        label="Code administrateur",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class OrderForm(forms.Form):
    customer_name = forms.CharField(
        label="Votre nom",
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    customer_phone = forms.CharField(
        label="Votre numéro WhatsApp",
        max_length=32,
        widget=forms.TextInput(attrs={"autocomplete": "tel"}),
    )


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["customer_name", "rating", "comment"]
        widgets = {
            "customer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "rating": forms.Select(choices=[(value, f"{value}/5") for value in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 4, "maxlength": 1200}),
        }


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "description", "price", "cover", "pdf", "is_available"]

    def clean_pdf(self):
        uploaded_file = self.cleaned_data.get("pdf")
        if uploaded_file:
            if not uploaded_file.name.lower().endswith(".pdf"):
                raise forms.ValidationError("Le fichier du livre doit être au format PDF.")
            position = uploaded_file.tell()
            header = uploaded_file.read(1024)
            uploaded_file.seek(position)
            if b"%PDF-" not in header:
                raise forms.ValidationError("Le fichier envoyé ne semble pas être un PDF valide.")
        return uploaded_file
