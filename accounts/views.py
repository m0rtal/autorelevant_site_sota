# from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from avtorelevant_site import settings
from .forms import CustomUserCreationForm
from .forms import UploadFileForm
from .models import UploadedFile
from .tasks import FileProcessingThread
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
                status='Успешно загружен',
                # result='Отправлен на обработку',
            )

            # Запуск фоновой задачи для обработки файла
            processing_thread = FileProcessingThread(uploaded_file.id, google_region, yandex_region)
            processing_thread.start()

            return redirect('profile')
    else:
        form = UploadFileForm()

    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def history(request):
    uploads = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    context = {
        'uploads': uploads,
        'MEDIA_URL': settings.MEDIA_URL,  # Добавляем MEDIA_URL в контекст
    }
    # return render(request, 'accounts/history.html', {'uploads': uploads})
    return render(request, 'accounts/history.html', context)


def home(request):
    return render(request, 'accounts/home.html')