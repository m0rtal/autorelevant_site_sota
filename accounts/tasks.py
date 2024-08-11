import asyncio
import threading
import aiohttp
import json
import pandas as pd
import os
from django.conf import settings
from .models import UploadedFile


async def get_uploaded_file(uploaded_file_id):
    return await asyncio.to_thread(UploadedFile.objects.get, id=uploaded_file_id)


async def save_uploaded_file(uploaded_file):
    return await asyncio.to_thread(uploaded_file.save)


async def fetch_yandex(session, url, search_string, yandex_region, semaphore):
    async with semaphore:
        async with session.get('http://176.9.48.55:5000/process-url/', params={
            'url': url,
            'search_string': search_string,
            'region': yandex_region,
            'return_as_json': 1
        }) as response:
            # r = await response.json(encoding='utf-8')
            return await response.json(encoding='utf-8')


async def fetch_google(session, url, search_string, google_region, semaphore):
    async with semaphore:
        async with session.get('http://176.9.48.55:5000/search-google/', params={
            'url': url,
            'search_string': search_string,
            'location': google_region,
            'domain': 'google.ru',
            'return_as_json': 1
        }) as response:
            # r = await response.json(encoding='utf-8')
            return await response.json(encoding='utf-8')


async def process_row(session, row, google_region, yandex_region, semaphore):
    yandex_task = fetch_yandex(session, row['url'], row['search_string'], yandex_region, semaphore)
    google_task = fetch_google(session, row['url'], row['search_string'], google_region, semaphore)

    yandex_result, google_result = await asyncio.gather(yandex_task, google_task)
    yandex_result, google_result = json.loads(yandex_result), json.loads(google_result)
    yandex_result['url'] = row['url']
    yandex_result['search_string'] = row['search_string']
    yandex_result['yandex_region'] = yandex_region
    google_result['url'] = row['url']
    google_result['search_string'] = row['search_string']
    google_result['google_region'] = google_region

    return {
        'yandex_result': yandex_result,
        'google_result': google_result
    }


async def process_file_async(uploaded_file_id, google_region, yandex_region):
    uploaded_file = await get_uploaded_file(uploaded_file_id)

    try:
        df = pd.read_excel(uploaded_file.file)
        df = df.rename({
            'Запрос': 'search_string',
            'URL': 'url',
        }, axis=1)

        uploaded_file.status = 'Начата обработка'

        semaphore = asyncio.Semaphore(1)

        async with aiohttp.ClientSession() as session:
            tasks = []
            for _, row in df.iterrows():
                task = asyncio.ensure_future(process_row(session, row, google_region, yandex_region, semaphore))
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            combined_results = []
            for result in results:
                yandex_result = result['yandex_result']
                google_result = result['google_result']

                combined_lsi = list(set(yandex_result.get('lsi', []) + google_result.get('lsi', [])))
                combined_increase_freq = {k: max(yandex_result.get('увеличить частотность', {}).get(k, 0),
                                                 google_result.get('увеличить частотность', {}).get(k, 0)) for k in
                                          set(yandex_result.get('увеличить частотность', {}).keys()).union(
                                              google_result.get('увеличить частотность', {}).keys())}
                combined_decrease_freq = {k: min(yandex_result.get('уменьшить частотность', {}).get(k, 0),
                                                 google_result.get('уменьшить частотность', {}).get(k, 0)) for k in
                                          set(yandex_result.get('уменьшить частотность', {}).keys()).union(
                                              google_result.get('уменьшить частотность', {}).keys())}

                yandex_links = yandex_result.get('обработанные ссылки', {})
                google_links = google_result.get('обработанные ссылки', {})

                combined_results.append({
                    'url': yandex_result['url'],
                    'search_string': yandex_result['search_string'],
                    'yandex_region': yandex_result['yandex_region'],
                    'google_region': google_result['google_region'],
                    'lsi': '\n'.join(combined_lsi),
                    'увеличить частотность': '\n'.join([f"{k}: {v}" for k, v in combined_increase_freq.items()]),
                    'уменьшить частотность': '\n'.join([f"{k}: {v}" for k, v in combined_decrease_freq.items()]),
                    'обработанные ссылки Yandex': '\n'.join(yandex_links.values()),
                    'обработанные ссылки Google': '\n'.join(google_links.values())
                })

            results_df = pd.DataFrame(combined_results)

            # Создание пути для сохранения файла
            results_file_name = f'results_{uploaded_file_id}.xlsx'
            results_file_path = os.path.join(settings.MEDIA_ROOT, 'results', results_file_name)

            # Сохранение DataFrame в Excel файл
            results_df.to_excel(results_file_path, index=False)

            # Обновление поля result модели UploadedFile
            uploaded_file.status = 'Обработка завершена'
            uploaded_file.result = os.path.join('results', results_file_name)

    except Exception as e:
        uploaded_file.status = 'Ошибка при обработке'
        uploaded_file.result = str(e)

    await save_uploaded_file(uploaded_file)


def start_processing(uploaded_file_id, google_region, yandex_region):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process_file_async(uploaded_file_id, google_region, yandex_region))
    loop.close()


class FileProcessingThread(threading.Thread):
    def __init__(self, uploaded_file_id, google_region, yandex_region):
        self.yandex_region = yandex_region
        self.google_region = google_region
        self.uploaded_file_id = uploaded_file_id
        threading.Thread.__init__(self)

    def run(self):
        start_processing(self.uploaded_file_id, self.google_region, self.yandex_region)
