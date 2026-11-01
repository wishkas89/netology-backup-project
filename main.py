import io
import json
import logging
import requests
import yadisk

# Настройка логирования для отслеживания процесса программы
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


class CatAPIClient:
    """Класс для работы с API сайта cataas.com."""

    BASE_URL = "https://cataas.com"

    def get_cat_with_text(self, text: str) -> dict:
        """Получает метаданные и скачивает котика в оперативную память."""
        url = f"{self.BASE_URL}/cat/says/{text}"
        params = {"json": "true"}

        logging.info(f"Запрос картинки котика с текстом '{text}'...")
        response = requests.get(url, params=params)

        if response.status_code != 200:
            logging.error(f"Ошибка получения котика с CATAAS: {response.status_code}")
            response.raise_for_status()

        data = response.json()
        file_id = data.get("_id")
        
        # Скачиваем саму картинку в оперативную память (in-memory)
        img_url = f"{self.BASE_URL}/cat/{file_id}/says/{text}"
        logging.info("Загрузка байт картинки 'по воздуху'...")
        img_response = requests.get(img_url)
        
        size = len(img_response.content)

        return {
            "content": img_response.content,
            "size": size,
            "mimetype": data.get("mimetype", "image/jpeg"),
        }


def main():
    group_name = "PD-AGNT-162"

    # 1. Входные данные — запрашиваем всё вручную через консоль
    text_input = input("Введите текст для картинки котика: ").strip()
    token_input = input("Введите актуальный токен Яндекс.Диска (Полигон): ").strip()

    if not text_input or not token_input:
        logging.error("Текст или токен не могут быть пустыми!")
        return

    # 2. Получаем котика
    cat_client = CatAPIClient()
    try:
        cat_data = cat_client.get_cat_with_text(text_input)
    except Exception as e:
        logging.error(f"Не удалось получить данные с CATAAS: {e}")
        return

    ext = cat_data["mimetype"].split("/")[-1]
    if ext == "mpeg" or not ext:
        ext = "jpg"
    file_name = f"{text_input}.{ext}"

    # 3. Инициализируем официальный клиент Яндекс.Диска
    y = yadisk.YaDisk(token=token_input)

    # Проверяем авторизацию токена
    if not y.check_token():
        logging.error("Введенный токен Яндекс.Диска недействителен! Пожалуйста, скопируйте его заново с Полигона.")
        return

    # 4. Создаем папку (если её нет)
    path_folder = f"/{group_name}"
    try:
        if not y.exists(path_folder):
            logging.info(f"Создание папки '{group_name}' на Яндекс.Диске...")
            y.mkdir(path_folder)
            logging.info(f"Папка '{group_name}' успешно создана.")
        else:
            logging.info(f"Папка '{group_name}' уже существует.")
    except Exception as e:
        logging.error(f"Не удалось подготовить папку через библиотеку: {e}")
        return

    # 5. Загружаем файл из оперативной памяти напрямую в облако
    full_path = f"{path_folder}/{file_name}"
    logging.info(f"Отправка файла '{file_name}' на Яндекс.Диск...")
    
    try:
        file_stream = io.BytesIO(cat_data["content"])
        y.upload(file_stream, full_path, overwrite=True)
        logging.info(f"Файл '{file_name}' успешно сохранен на вашем Яндекс.Диске!")
        
        # 6. Сохраняем отчетный JSON-файл
        result_info = [{
            "file_name": file_name,
            "size_bytes": cat_data["size"]
        }]

        json_filename = "upload_result.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(result_info, f, ensure_ascii=False, indent=4)

        logging.info(f"Информация о загрузке успешно сохранена в файл {json_filename}")

    except Exception as e:
        logging.error(f"Ошибка при передаче файла в облако: {e}")


if __name__ == "__main__":
    main()
