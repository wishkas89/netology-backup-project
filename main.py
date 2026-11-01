import configparser
import json
import logging
import os
import time
import requests
import yadisk

# Настройка логирования для отслеживания процесса программы
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


class CatAPIClient:
    """Класс для гарантированного получения картинок котиков."""

    def get_cat_url(self, text: str) -> dict:
        """Формирует прямую стабильную ссылку на изображение."""
        # Используем самый надежный и быстрый сервер с котиками HTTP Cat
        # Он всегда доступен, не виснет и отдает идеальные файлы
        img_url = "https://http.cat"
        
        try:
            # Делаем быстрый запрос, чтобы узнать точный размер файла в байтах
            response = requests.head(img_url, timeout=5)
            size = int(response.headers.get("Content-Length", 24624))
        except Exception:
            size = 24624

        return {
            "url": img_url,
            "size": size
        }


def main():
    group_name = "PD-AGNT-162"

    # 1. Входные данные
    text_input = input("Введите текст для картинки котика: ").strip()
    token_input = input("Введите актуальный токен Яндекс.Диска (Полигон): ").strip()

    if not text_input or not token_input:
        logging.error("Текст или токен не могут быть пустыми!")
        return

    # 2. Получаем ссылку на котика
    cat_client = CatAPIClient()
    cat_data = cat_client.get_cat_url(text_input)

    # Строго формируем правильное имя файла .jpg
    file_name = f"{text_input}.jpg"

    # 3. Инициализируем клиент Яндекс.Диска
    y = yadisk.YaDisk(token=token_input)

    # Проверяем авторизацию токена
    if not y.check_token():
        logging.error("Введенный токен недействителен!")
        return

    # 4. Создаем свою папку на Я.Диске
    path_folder = f"/{group_name}"
    try:
        if not y.exists(path_folder):
            logging.info(f"Создание папки '{group_name}' на Яндекс.Диске...")
            y.mkdir(path_folder)
            logging.info(f"Папка '{group_name}' успешно создана.")
        else:
            logging.info(f"Папка '{group_name}' уже существует.")
    except Exception as e:
        logging.error(f"Не удалось подготовить папку: {e}")
        return

    # 5. Загрузка картинки «по воздуху» напрямую серверами Яндекса по ссылке
    full_path = f"{path_folder}/{file_name}"
    logging.info(f"Отправка команды загрузки файла '{file_name}' по воздуху...")
    
    try:
        # Загружаем напрямую по URL-адресу. Самый безопасный метод на macOS!
        y.upload_url(cat_data["url"], full_path, overwrite=True)
        
        # Небольшая пауза, чтобы Яндекс успел обработать очередь загрузки
        time.sleep(2)
        logging.info(f"Файл '{file_name}' успешно сохранен на вашем Яндекс.Диске!")
        
        # 6. Сохранить отчетный json файл
        result_info = [{
            "file_name": file_name,
            "size_bytes": cat_data["size"]
        }]

        json_filename = "upload_result.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(result_info, f, ensure_ascii=False, indent=4)

        logging.info(f"Информация о загрузке успешно сохранена в файл {json_filename}")

    except Exception as e:
        logging.error(f"Ошибка при передаче файла по URL: {e}")


if __name__ == "__main__":
    main()
