import eel
import json
import os
import re
import requests
import zipfile
import io
import subprocess


def _get_cmd_output(command_list):
    """
    Внутренняя функция для запуска команды в терминале.
    Скрывает черное окно консоли на Windows.
    """
    startupinfo = None

    # Специфика Windows: подавляем появление черного окна
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        # Запускаем процесс
        result = subprocess.run(
            command_list,
            stdout=subprocess.PIPE,  # Перехват обычного вывода
            stderr=subprocess.PIPE,  # Перехват ошибок (Java пишет версию сюда)
            text=True,  # Получаем сразу строки, а не байты
            startupinfo=startupinfo  # Применяем настройки скрытия окна
        )

        # Если код возврата 0 (Успех), возвращаем вывод
        if result.returncode == 0:
            # Некоторые программы (Java) пишут версию в stderr, другие в stdout.
            # Берем то, что не пустое.
            return result.stdout.strip() or result.stderr.strip()
        return None

    except FileNotFoundError:
        return None  # Команда не найдена (программа не установлена)
    except Exception as e:
        print(f"Error checking {command_list}: {e}")
        return None


@eel.expose
def check_software_versions():
    """
    Проверяет версии Java, Node.js и Git.
    Возвращает словарь со статусами.
    """
    print("--- Проверка окружения... ---")

    status = {
        "java": {"installed": False, "version": ""},
        "node": {"installed": False, "version": ""},
        "git": {"installed": False, "version": ""}
    }

    # 1. Проверка Java (java -version)
    java_out = _get_cmd_output(["java", "-version"])
    if java_out:
        status["java"]["installed"] = True
        # Парсим первую строку, например: "openjdk version 17.0.1..."
        # Берем только первую строку для красоты
        status["java"]["version"] = java_out.split('\n')[0]

    # 2. Проверка Node.js (node -v)
    node_out = _get_cmd_output(["node", "-v"])
    if node_out:
        status["node"]["installed"] = True
        status["node"]["version"] = node_out  # Обычно просто "v16.13.0"

    # 3. Проверка Git (git --version)
    git_out = _get_cmd_output(["git", "--version"])
    if git_out:
        status["git"]["installed"] = True
        # git output: "git version 2.33.0.windows.1" -> Очистим лишнее
        status["git"]["version"] = git_out.replace("git version", "").strip()

    print(f"Результат проверки: {status}")
    return status


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