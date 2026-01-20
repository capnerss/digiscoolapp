import eel
import json
import os
import re
import requests
import zipfile
import io
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog


CONFIG_FILE = 'config.json'


def _load_config():
    """Читает конфиг. Если файла нет — возвращает дефолт."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass  # Если файл битый, игнорируем
    return {"download_path": ""}


def _save_config(key, value):
    """Обновляет одно значение в конфиге и сохраняет файл."""
    config = _load_config()
    config[key] = value
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)


def _get_default_download_path():
    """Путь по умолчанию: Documents/DigiSchool"""
    return os.path.join(os.path.expanduser("~"), "Documents", "DigiSchool")


# --- API EEL ---

@eel.expose
def get_current_settings():
    """Отдает Frontend текущую папку загрузки"""
    config = _load_config()
    current_path = config.get("download_path")

    if not current_path:
        current_path = _get_default_download_path()

    return {"download_path": current_path}


@eel.expose
def choose_folder():
    """
    Открывает нативное окно выбора папки через Tkinter.
    Возвращает выбранный путь или None, если отменили.
    """
    # Создаем скрытое окно Tkinter (оно нужно, чтобы запустить диалог)
    root = tk.Tk()
    root.withdraw()  # Скрываем главное окно
    root.wm_attributes('-topmost', 1)  # Окно диалога будет поверх всех окон

    folder_selected = filedialog.askdirectory()

    root.destroy()  # Уничтожаем окно после выбора

    if folder_selected:
        # Нормализуем путь (меняем слэши для красоты)
        folder_selected = os.path.normpath(folder_selected)
        # Сохраняем сразу в конфиг
        _save_config("download_path", folder_selected)
        return folder_selected

    return None


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
    # 1. Получаем путь из конфига
    config = _load_config()
    base_path = config.get("download_path")
    if not base_path:
        base_path = _get_default_download_path()

    print(f"📥 Downloading to: {base_path}")

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
    folder_result = ensure_project_folder(base_path, course_id, student_name, project_name)
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


def ensure_project_folder(base_path, course_name, student_name, project_name):
    # Очищаем имена от спецсимволов
    clean_course = sanitize_filename(course_name)
    clean_student = sanitize_filename(student_name)
    clean_project = sanitize_filename(project_name)

    # ЛОГИКА СТРУКТУРЫ:
    # 1. base_path - то, что выбрал юзер (например, F:/)
    # 2. "DigiSchool" - наш системный контейнер (чтобы легко находить установленное)
    # 3. clean_course - группировка по курсу (Python, Web...)
    # 4. clean_student - папка конкретного ученика
    # 5. clean_project - папка проекта

    # Если ты хочешь, чтобы ВСЕ проекты ученика были в одной папке независимо от курса,
    # можно поменять местами clean_course и clean_student.
    # Но пока оставим как было в Спринте 1 (Курс -> Ученик).

    full_path = os.path.join(
        base_path,
        "DigiSchool",  # <--- ВОТ ЭТО МЫ ВЕРНУЛИ
        clean_course,
        clean_student,
        clean_project
    )

    try:
        os.makedirs(full_path, exist_ok=True)
        print(f"📂 Folder ready: {full_path}")  # Лог для контроля
        return {"status": "success", "path": full_path}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# main.py

@eel.expose
def get_installed_projects(course_id):
    """
    Сканирует папку установки и возвращает список найденных проектов для конкретного курса.
    Структура: base_path / DigiSchool / course_id / student_name / project_name
    """
    config = _load_config()
    base_path = config.get("download_path") or _get_default_download_path()

    # Путь к папке курса
    course_path = os.path.join(base_path, "DigiSchool", sanitize_filename(course_id))

    found_projects = []

    if os.path.exists(course_path):
        # Проходимся по всем студентам внутри курса
        try:
            students = os.listdir(course_path)
            for student in students:
                student_path = os.path.join(course_path, student)
                if os.path.isdir(student_path):
                    # Проходимся по проектам студента
                    projects = os.listdir(student_path)
                    for proj in projects:
                        # Добавляем в список (можно добавить проверку на наличие файлов внутри)
                        found_projects.append({
                            "name": proj,
                            "student": student,
                            "path": os.path.join(student_path, proj),
                            "course_id": course_id
                        })
        except Exception as e:
            print(f"Error scanning projects: {e}")

    return found_projects


@eel.expose
def open_folder(path):
    """Открывает папку в проводнике (Explorer/Finder)"""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])

if __name__ == '__main__':
    eel.init('web')
    eel.start('index.html', size=(1000, 700))