# forms.py
from django import forms
from .models import CustomUser
from django.contrib.auth.forms import UserCreationForm


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email',)  # или другие поля, которые вы хотите включить


class UploadFileForm(forms.Form):
    google_region = forms.CharField(max_length=100, label='Google Region')
    yandex_region = forms.CharField(max_length=100, label='Yandex Region')
    file = forms.FileField(label='Загрузить файл')
