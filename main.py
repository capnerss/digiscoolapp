import eel
import json
import os
import re
import requests
import zipfile
import io
import subprocess
import sys


def _get_cmd_output(command_list):
    """
    Внутренняя функция: запускает команду скрытно и возвращает текст вывода.
    Работает и с stdout, и с stderr (так как Java пишет версию в stderr).
    """
    startupinfo = None

    # Специфика Windows: скрываем черное окно консоли
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    try:
        result = subprocess.run(
            command_list,
            capture_output=True,  # Перехватываем вывод
            text=True,  # Автоматически декодируем байты в строки
            startupinfo=startupinfo,
            check=False  # Не выбрасывать ошибку, если код возврата != 0
        )
        # Объединяем stdout и stderr, чтобы найти версию везде
        return (result.stdout + result.stderr).strip()

    except FileNotFoundError:
        # Программа не найдена в PATH
        return None
    except Exception as e:
        print(f"Error checking {command_list[0]}: {e}")
        return None


def _extract_version(output_text):
    """
    Ищет паттерн версии (например, 1.8.0, 17.0.1, 20.5.0) в тексте.
    """
    if not output_text:
        return None

    # Regex: ищет цифры с точками (минимум X.Y)
    # Пример совпадения: "17.0.2" из "openjdk version 17.0.2 2022-01-18"
    match = re.search(r'(\d+\.\d+(\.\d+)?)', output_text)
    if match:
        return match.group(1)
    return "Unknown"


@eel.expose
def check_software_versions():
    print("Checking system environment...")  # Лог в консоль разработчика

    # Список команд для проверки
    checks = {
        "java": ["java", "-version"],
        "node": ["node", "-v"],
        "git": ["git", "--version"]
    }

    report = {}

    for tool, cmd in checks.items():
        raw_output = _get_cmd_output(cmd)

        if raw_output:
            version = _extract_version(raw_output)
            report[tool] = {
                "installed": True,
                "version": version,
                "raw": raw_output[:50]  # Для отладки (обрезаем длинные строки)
            }
        else:
            report[tool] = {
                "installed": False,
                "version": None
            }

    return report


@eel.expose
def download_project(course_id, project_name, student_name, project_index):
    print(f"--- START DOWNLOAD: {project_name} for {student_name} ---")

    # 1. Сначала ищем URL в data.json по ID курса и имени проекта
    # (В реальном проекте лучше передавать URL сразу из JS, но так безопаснее)
    target_url = None
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for course in data:
                if course['id'] == course_id:
                    for proj in course['projects']:
                        if proj['name'] == project_name:
                            target_url = proj['github_url']
                            break
    except Exception as e:
        return {"status": "error", "msg": f"Ошибка чтения config: {e}"}

    if not target_url:
        return {"status": "error", "msg": "Ссылка на GitHub не найдена!"}

    # 2. Создаем папку (используем функцию из DIG-17)
    folder_result = ensure_project_folder(course_id, student_name, project_name)
    if folder_result['status'] == 'error':
        return folder_result

    target_dir = folder_result['path']

    # 3. СКАЧИВАНИЕ
    try:
        # Сообщаем UI: "Начинаю качать..."
        eel.update_ui_progress(project_index, 0, "Ühendamine GitHubiga...")
        eel.sleep(0.1)  # Даем UI время обновиться

        response = requests.get(target_url, stream=True)
        total_length = response.headers.get('content-length')

        downloaded_data = io.BytesIO()  # Буфер в памяти
        downloaded_size = 0
        chunk_size = 1024 * 16  # 16 КБ

        if total_length is None:
            # Если GitHub не отдал размер, просто показываем МБ
            for chunk in response.iter_content(chunk_size=chunk_size):
                downloaded_data.write(chunk)
                downloaded_size += len(chunk)
                mb = round(downloaded_size / (1024 * 1024), 2)
                eel.update_ui_progress(project_index, 50, f"Laetud: {mb} MB...")
                eel.sleep(0.01)  # ВАЖНО: Не дает интерфейсу зависнуть
        else:
            # Если размер известен, считаем честные проценты
            total_length = int(total_length)
            for chunk in response.iter_content(chunk_size=chunk_size):
                downloaded_data.write(chunk)
                downloaded_size += len(chunk)
                percent = int((downloaded_size / total_length) * 100)
                eel.update_ui_progress(project_index, percent, f"Laadimine: {percent}%")
                eel.sleep(0.01)

        # 4. РАСПАКОВКА
        eel.update_ui_progress(project_index, 90, "Lahtipakkimine...")
        eel.sleep(0.1)

        with zipfile.ZipFile(downloaded_data) as z:
            # GitHub кладет всё в папку "repo-main", нам надо её пропустить
            root_folder = z.namelist()[0]

            for file in z.namelist():
                # Убираем корневую папку из пути
                rel_path = os.path.relpath(file, root_folder)

                # Если это сама папка или системный файл - пропускаем
                if rel_path == "." or rel_path.startswith("__MACOSX"):
                    continue

                dest_path = os.path.join(target_dir, rel_path)

                # Создаем папки/файлы
                if file.endswith('/'):
                    os.makedirs(dest_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        f.write(z.read(file))

        # 5. ФИНАЛ
        eel.update_ui_progress(project_index, 100, "Valmis! (Готово)")
        return {"status": "success", "path": target_dir}

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "msg": str(e)}


@eel.expose
def get_courses():
    """
    Read fail data.json and return list of courses.
    """
    try:
        # Open file data.json and read it. encoding='utf-8' is important!
        with open('data.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            # return list of courses
            return data

    except FileNotFoundError:
        print("Error: File not found!")
        return []
    except json.JSONDecodeError as e:
        print(f"Error wrong JSON format: {e}")
        return []


def sanitize_filename(name):
    """Удаляет запрещенные символы из имени папки"""
    # Оставляем только буквы, цифры, пробелы, дефис и подчеркивание
    # Все остальное меняем на пустоту
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def ensure_project_folder(course_name, student_name, project_name):
    # Очищаем входные данные
    clean_course = sanitize_filename(course_name)
    clean_student = sanitize_filename(student_name)
    clean_project = sanitize_filename(project_name)

    home_dir = os.path.expanduser('~')
    full_path = os.path.join(
        home_dir, 'Documents', "DigiSchool",
        clean_course, clean_student, clean_project
    )

    try:
        os.makedirs(full_path, exist_ok=True)
        return {"status": "success", "path": full_path}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


if __name__ == '__main__':
    eel.init('web')
    eel.start('index.html', size=(1000, 700))