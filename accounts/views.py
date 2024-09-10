# from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from accounts.utils import random_human_code

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
            form_fields = request.POST.dict()
            del form_fields['csrfmiddlewaretoken']
            request.session['user_creation_form'] = form_fields
            request.session['confirmation_code'] = random_human_code(6)
            return redirect('confirm_email')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def confirm_email(request):
    valid_code = request.session.get('confirmation_code')
    if valid_code:
        user_email = request.session['user_creation_form']['email']
        send_error = False
        wrong_code = False
        try:
            send_mail(
                "Подтверждение регистрации", 
                f"Код подтверждения: {valid_code}",
                'no-reply@autorelevant.org',
                [user_email]
            )
        except Exception as error:
            print('Email send error: ', error)
            send_error = True
        if request.method == 'POST':
            if request.POST['code'] == valid_code:
                form = CustomUserCreationForm(request.session['user_creation_form'])
                form.save()
                del request.session['user_creation_form']
                del request.session['confirmation_code']
                return redirect('login')
            else:
                wrong_code = True
        return render(request, 'accounts/confirm_email.html', {
            'email': user_email,
            'wrong_code': wrong_code,
            'send_error': send_error
        })
    else:
        return redirect('register')

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
5

def home(request):
    return render(request, 'accounts/home.html')