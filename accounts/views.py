# from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from .forms import UploadFileForm
from .models import UploadedFile
import openpyxl

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})



@login_required
def profile(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # Получение данных из формы
            google_region = form.cleaned_data['google_region']
            yandex_region = form.cleaned_data['yandex_region']
            file = form.cleaned_data['file']

            # Сохранение информации в базе данных
            uploaded_file = UploadedFile.objects.create(
                user=request.user,
                file=file,
                google_region=google_region,
                yandex_region=yandex_region,
            )

            # Обработка файла (пример)
            try:
                wb = openpyxl.load_workbook(uploaded_file.file)
                # Обработка данных...
                uploaded_file.status = 'Успешно'
                uploaded_file.result = 'Результаты обработки...'
            except Exception as e:
                uploaded_file.status = 'Ошибка'
                uploaded_file.result = str(e)
            uploaded_file.save()

            return redirect('profile')
    else:
        form = UploadFileForm()

    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def history(request):
    uploads = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'accounts/history.html', {'uploads': uploads})


def home(request):
    return render(request, 'accounts/home.html')