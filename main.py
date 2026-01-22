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


def _check_java_17():
    """
    Проверяет наличие Java 17 (желательно Adoptium/Temurin).
    Возвращает: {"installed": bool, "version": str, "details": str}
    """
    try:
        # 1. Пробуем штатную команду java -version
        # startuinfo скрывает окно консоли
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            ["java", "-version"],
            capture_output=True, text=True, startupinfo=startupinfo
        )
        output = result.stderr + result.stdout  # Java пишет версию в stderr

        # Ищем версию 17.x.x
        version_match = re.search(r'version "17\.\d+\.\d+', output)
        is_17 = bool(version_match)

        # Проверяем, это Adoptium/Temurin или нет (не критично, но полезно знать)
        is_adoptium = "Temurin" in output or "Adoptium" in output

        version_str = "Unknown"
        if version_match:
            version_str = version_match.group(0).replace('version "', '')

        return {
            "installed": is_17,
            "version": version_str if is_17 else f"Wrong Ver ({version_str})",
            "tooltip": output.split('\n')[0]
        }
    except FileNotFoundError:
        return {"installed": False, "version": "Missing", "tooltip": "Java not in PATH"}


def _check_program_path(possible_paths, name_for_display):
    """
    Проверяет наличие программы по списку путей.
    """
    for path in possible_paths:
        expanded_path = os.path.expandvars(path)  # Раскрывает %LOCALAPPDATA%
        if os.path.exists(expanded_path):
            return {
                "installed": True,
                "version": "Installed",  # Версию exe файла доставать долго, просто "Есть"
                "tooltip": f"Found at: {expanded_path}"
            }

    return {"installed": False, "version": "Missing", "tooltip": f"{name_for_display} not found"}


@eel.expose
def check_software_versions():
    print("🔎 Checking specific course software...")

    report = {}

    # 1. JDK 17 (Checking Command Line)
    report["java"] = _check_java_17()

    # 2. Visual Studio Code (Checking Paths)
    vscode_paths = [
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe"
    ]
    report["vscode"] = _check_program_path(vscode_paths, "VS Code")

    # 3. Unity Hub (Checking Paths)
    unity_hub_paths = [
        r"C:\Program Files\Unity Hub\Unity Hub.exe",
        r"C:\Program Files (x86)\Unity Hub\Unity Hub.exe"
    ]
    report["unity"] = _check_program_path(unity_hub_paths, "Unity Hub")

    # 4. Visual Studio (Community 2022/2019) - для Unity
    # Проверяем наличие devenv.exe
    vs_paths = [
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\Common7\IDE\devenv.exe"
    ]
    report["visualstudio"] = _check_program_path(vs_paths, "Visual Studio")

    # 5. Minecraft Education
    # (Сложно проверить Store-версию, проверяем десктопную или папку данных)
    mc_edu_paths = [
        r"C:\Program Files (x86)\Minecraft Education Edition\minecraft.windows.exe",
        r"%LOCALAPPDATA%\Packages\Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe"  # Папка Store версии
    ]
    report["mcedu"] = _check_program_path(mc_edu_paths, "MC Education")

    return report


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
    """Путь по умолчанию: Documents/DigisCool"""
    return os.path.join(os.path.expanduser("~"), "Documents", "DigisCool")


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
def download_project(course_id, project_name, student_name, project_index):
    # 1. Загружаем конфиг и пути
    config = _load_config()
    base_path = config.get("download_path")
    if not base_path:
        base_path = _get_default_download_path()

    print(f"📥 Downloading to: {base_path}")

    # 2. Ищем URL (по старой логике)
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
        return {"status": "error", "msg": f"Config error: {e}"}

    if not target_url:
        return {"status": "error", "msg": "GitHub URL not found!"}

    # 3. Готовим папку назначения
    folder_result = ensure_project_folder(base_path, course_id, student_name, project_name)
    if folder_result['status'] == 'error':
        return folder_result

    target_dir = folder_result['path']

    # Временный файл для скачивания (внутри целевой папки)
    temp_zip_path = os.path.join(target_dir, "temp_download.zip")

    try:
        # --- СТАДИЯ 1: СКАЧИВАНИЕ (STREAM TO DISK) ---
        eel.update_ui_progress(project_index, 0, "Подключение к GitHub...")

        response = requests.get(target_url, stream=True)
        total_length = response.headers.get('content-length')

        # Открываем файл на диске для записи
        with open(temp_zip_path, 'wb') as f:
            downloaded_size = 0
            chunk_size = 1024 * 64  # Читаем по 64 КБ

            if total_length is None:
                # Если GitHub не сказал размер -> показываем сколько скачали в МБ
                # И делаем "фейковый" прогресс бар (бегает 10-90%)
                fake_percent = 10
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    mb = round(downloaded_size / (1024 * 1024), 1)

                    # Простая анимация: 10 -> 90 -> 10
                    fake_percent += 1
                    if fake_percent > 90: fake_percent = 10

                    # Обновляем UI (важно: eel.sleep дает интерфейсу дышать)
                    if downloaded_size % (
                            1024 * 512) == 0:  # Обновляем не каждый чанк, а каждые 0.5 МБ (чтобы не тормозить)
                        eel.update_ui_progress(project_index, fake_percent, f"Скачано: {mb} MB...")
                        eel.sleep(0.001)
            else:
                # Если размер известен -> честные проценты
                total_length = int(total_length)
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    percent = int((downloaded_size / total_length) * 100)

                    if downloaded_size % (1024 * 512) == 0:
                        eel.update_ui_progress(project_index, percent, f"Загрузка: {percent}%")
                        eel.sleep(0.001)

        # --- СТАДИЯ 2: РАСПАКОВКА ---
        eel.update_ui_progress(project_index, 95, "Распаковка архива...")

        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as z:
                # GitHub кладет всё в папку "repo-name-main", нам надо вытащить содержимое
                root_folder_inside_zip = z.namelist()[0]

                # Получаем список всех файлов
                all_files = z.namelist()
                total_files = len(all_files)

                for i, file in enumerate(all_files):
                    # Пропускаем саму корневую папку
                    if file == root_folder_inside_zip:
                        continue

                    # Убираем корневую папку из пути (strip root folder)
                    # Пример: "game-main/Assets/Script.cs" -> "Assets/Script.cs"
                    rel_path = file[len(root_folder_inside_zip):]

                    # Пропускаем пустые пути и MACOSX мусор
                    if not rel_path or rel_path.startswith("__MACOSX") or rel_path.startswith("."):
                        continue

                    dest_path = os.path.join(target_dir, rel_path)

                    # Распаковка
                    if file.endswith('/'):
                        os.makedirs(dest_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with open(dest_path, "wb") as f_out:
                            f_out.write(z.read(file))

        except zipfile.BadZipFile:
            return {"status": "error", "msg": "Ошибка: Скачанный файл поврежден (Bad Zip)."}

        # --- СТАДИЯ 3: ЧИСТКА ---
        # Удаляем zip архив, чтобы не занимать место
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

        eel.update_ui_progress(project_index, 100, "Готово!")
        return {"status": "success", "path": target_dir}

    except Exception as e:
        print(f"Download Error: {e}")
        # Пытаемся почистить мусор при ошибке
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
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
    # 2. "DigisCool" - наш системный контейнер (чтобы легко находить установленное)
    # 3. clean_course - группировка по курсу (Python, Web...)
    # 4. clean_student - папка конкретного ученика
    # 5. clean_project - папка проекта

    # Если ты хочешь, чтобы ВСЕ проекты ученика были в одной папке независимо от курса,
    # можно поменять местами clean_course и clean_student.
    # Но пока оставим как было в Спринте 1 (Курс -> Ученик).

    full_path = os.path.join(
        base_path,
        "DigisCool",  # <--- ВОТ ЭТО МЫ ВЕРНУЛИ
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
    Структура: base_path / DigisCool / course_id / student_name / project_name
    """
    config = _load_config()
    base_path = config.get("download_path") or _get_default_download_path()

    # Путь к папке курса
    course_path = os.path.join(base_path, "DigisCool", sanitize_filename(course_id))

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


@eel.expose
def launch_editor(path, editor_type):
    # Нормализуем путь (меняем слеши на системные)
    clean_path = os.path.normpath(path)
    print(f"🚀 Launching {editor_type} for: {clean_path}")

    try:
        # --- ВАРИАНТ 1: VS CODE ---
        if editor_type == 'vscode':
            # Добавляем кавычки вокруг пути вручную, чтобы cmd не подавилась пробелами
            # shell=True позволяет Windows найти команду 'code' в переменных среды
            cmd = f'code "{clean_path}"'
            print(f"Executing: {cmd}")
            subprocess.Popen(cmd, shell=True)
            return {"status": "success"}

        # --- ВАРИАНТ 2: UNITY (Через Hub) ---
        elif editor_type == 'unity':
            # Список стандартных путей к Unity Hub
            possible_paths = [
                r"C:\Program Files\Unity Hub\Unity Hub.exe",
                r"C:\Program Files (x86)\Unity Hub\Unity Hub.exe",
                # Можно добавить свой путь, если он нестандартный
            ]

            hub_exe = None
            for p in possible_paths:
                if os.path.exists(p):
                    hub_exe = p
                    break

            if not hub_exe:
                print("❌ Unity Hub not found")
                return {"status": "error", "msg": "Unity Hub не найден в Program Files."}

            # Аргументы списком безопаснее для subprocess
            print(f"Opening via Hub: {hub_exe}")
            subprocess.Popen([hub_exe, "--", "--open", clean_path])
            return {"status": "success"}

        else:
            return {"status": "error", "msg": f"Unknown editor: {editor_type}"}

    except Exception as e:
        print(f"❌ Error launching editor: {e}")
        return {"status": "error", "msg": str(e)}


if __name__ == '__main__':
    eel.init('web')
    eel.start('index.html', size=(1000, 700))