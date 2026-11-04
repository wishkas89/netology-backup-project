import json
import logging
import sys
import requests
from tqdm import tqdm

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("backup.log", encoding="utf-8")]
)


class CatAPIClient:
    """Класс для работы с API CATAAS (Cat as a Service)."""
    BASE_URL = "https://cataas.com"

    def __init__(self, timeout=10):
        self.session = requests.Session()
        self.timeout = timeout

    def get_cat_url(self, text):
        """Получает рабочий URL картинки котика с текстом."""
        url = f"{self.BASE_URL}/cat/says/{text}"
        params = {"json": "true"}

        logging.info(f"Запрос метаданных котика с текстом: '{text}'")
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                logging.warning("JSON API недоступно, переключаемся на прямой URL")
                return f"{self.BASE_URL}/cat/says/{text}"
                
            data = response.json()
            image_id = data.get("_id") or data.get("id")
            
            if not image_id:
                return f"{self.BASE_URL}/cat/says/{text}"

            direct_url = f"{self.BASE_URL}/cat/{image_id}/says/{text}"
            logging.info(f"Получена персистентная ссылка на котика: {direct_url}")
            return direct_url

        except (requests.exceptions.Timeout, TimeoutError) as err:
            logging.error(f"Превышено время ожидания ответа от CATAAS API: {err}")
            return None
        except requests.exceptions.RequestException as err:
            logging.error(f"Сетевая ошибка API: {err}. Используем базовый эндпоинт.")
            return f"{self.BASE_URL}/cat/says/{text}"


class YandexDiskUploader:
    """Класс для взаимодействия с REST API Яндекс.Диска."""
    BASE_URL = "https://cloud-api.yandex.net/v1/disk"

    def __init__(self, token, timeout=15):
        self.headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.timeout = timeout

    def create_folder(self, folder_name):
        """Создает папку на Яндекс.Диске через чистый и изолированный PUT-запрос."""
        url = f"{self.BASE_URL}/resources"
        params = {"path": folder_name}
        
        logging.info(f"Создание папки '{folder_name}' на Я.Диске через изолированный PUT-запрос")
        try:
            # Используем прямой requests.put с явными заголовками авторизации
            response = requests.put(url, params=params, headers=self.headers, timeout=self.timeout)
            
            # 201 - создано, 409 - папка уже существует (оба варианта для нас успешны)
            if response.status_code == 201 or response.status_code == 409:
                logging.info(f"Папка '{folder_name}' успешно подготовлена.")
                return True
                
            print(f"\n[Диагностика Папки] Статус-код: {response.status_code}")
            print(f"[Диагностика Папки] Ответ сервера: {response.text}")
            return False
        except requests.exceptions.RequestException as err:
            logging.error(f"Ошибка при создании папки на Я.Диске: {err}")
            return False

    def upload_by_url(self, folder_name, file_name, file_url):
        """Загружает файл на Яндекс.Диск 'по воздуху' через URL (метод POST)."""
        url = f"{self.BASE_URL}/resources/upload"
        path_in_disk = f"{folder_name}/{file_name}"
        params = {
            "path": path_in_disk,
            "url": file_url
        }

        logging.info(f"Запуск асинхронной загрузки файла '{file_name}' по воздуху через POST")
        try:
            # Для загрузки по URL Яндекс.Диск жестко требует метод POST
            response = requests.post(url, params=params, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 202:
                logging.info(f"Файл '{file_name}' успешно принят Я.Диском на загрузку.")
                return True
            
            print(f"\n[Диагностика Загрузки] Статус-код: {response.status_code}")
            print(f"[Диагностика Загрузки] Ответ сервера: {response.text}")
            return False
        except requests.exceptions.RequestException as err:
            logging.error(f"Ошибка при отправке запроса на загрузку в Я.Диск: {err}")
            return False

    def get_file_meta(self, folder_name, file_name):
        """Получает метаданные загруженного файла с Яндекс.Диска."""
        url = f"{self.BASE_URL}/resources"
        path_in_disk = f"{folder_name}/{file_name}"
        params = {"path": path_in_disk}

        logging.info(f"Запрос метаданных файла '{path_in_disk}' с Я.Диска")
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            logging.error(f"Не удалось получить метаданные файла. Статус: {response.status_code}")
            return None
        except requests.exceptions.RequestException as err:
            logging.error(f"Ошибка запроса метаданных с Я.Диска: {err}")
            return None


def main():
    print("--- Программа резервного копирования картинок (v2.2) ---")

    text = input("Введите text для картинки котика: ").strip()
    token = input("Введите ваш токен Яндекс.Диска (Полигон): ").strip()
    group_name = input("Введите название вашей группы в Нетологии: ").strip()

    if not text or not token or not group_name:
        print("[Ошибка] Все поля ввода обязательны для заполнения!")
        sys.exit(1)

    cat_client = CatAPIClient()
    ya_uploader = YandexDiskUploader(token)

    with tqdm(total=4, desc="Резервное копирование") as pbar:
        
        # Этап 1: Получение стабильного URL картинки
        pbar.set_postfix_str("Получение ссылки")
        img_url = cat_client.get_cat_url(text)
        if not img_url:
            print("\n[Критическая ошибка] Не удалось получить рабочую ссылку от CATAAS. Завершение.")
            sys.exit(1)
        pbar.update(1)

        file_name = f"{text}.jpg"

        # Этап 2: Создание папки на Я.Диске через прямой PUT
        pbar.set_postfix_str("Создание папки")
        if not ya_uploader.create_folder(group_name):
            print("\n[Критическая ошибка] Не удалось создать или проверить папку на Яндекс.Диске. Завершение.")
            sys.exit(1)
        pbar.update(1)

        # Этап 3: Загрузка "по воздуху" через проверенный POST
        pbar.set_postfix_str("Загрузка по воздуху")
        if not ya_uploader.upload_by_url(group_name, file_name, img_url):
            print("\n[Критическая ошибка] Яндекс.Диск отклонил запрос на загрузку файла. Завершение.")
            sys.exit(1)
        pbar.update(1)

        # Этап 4: Запрос точного размера у Я.Диска и запись отчета
        pbar.set_postfix_str("Фиксация метаданных")
        file_meta = ya_uploader.get_file_meta(group_name, file_name)
        if not file_meta:
            print("\n[Предупреждение] Файл отправлен, но Яндекс.Диск еще обрабатывает его размер.")
            file_size = "unknown (processing)"
        else:
            file_size = file_meta.get("size", 0)
        pbar.update(1)

    # Запись итогового отчета
    result_data = [{
        "file_name": file_name,
        "size": file_size
    }]

    json_output_path = "upload_report.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print(f"\n[Успех] Котик успешно отправлен в облако '{group_name}/{file_name}'!")
    print(f"[Информация] Отчет сохранен в: '{json_output_path}'")


if __name__ == "__main__":
    main()
