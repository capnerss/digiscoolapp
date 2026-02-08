import eel
import json
import os
import re
import requests
import zipfile
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

CONFIG_FILE = 'config.json'


# --- СИСТЕМНЫЕ УТИЛИТЫ ---

def resource_path(relative_path):
    """
    Получает абсолютный путь к ресурсу.
    Нужен для работы внутри .exe (PyInstaller).
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def _load_course_data():
    """
    Гибридная загрузка: ищет data.json снаружи (рядом с exe),
    если нет — берет встроенный.
    """
    external_path = 'data.json'
    if os.path.exists(external_path):
        return external_path
    return resource_path('data.json')


def _load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"download_path": ""}


def _save_config(key, value):
    config = _load_config()
    config[key] = value
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)


def _get_default_download_path():
    # ИСПРАВЛЕНО: DigiSchool -> DigiScool
    return os.path.join(os.path.expanduser("~"), "Documents", "DigiScool")


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


# --- API EEL ---

@eel.expose
def get_current_settings():
    config = _load_config()
    current_path = config.get("download_path")
    if not current_path:
        current_path = _get_default_download_path()
    return {"download_path": current_path}


@eel.expose
def choose_folder():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder_selected = filedialog.askdirectory()
    root.destroy()

    if folder_selected:
        folder_selected = os.path.normpath(folder_selected)
        _save_config("download_path", folder_selected)
        return folder_selected
    return None


@eel.expose
def get_courses():
    try:
        json_path = _load_course_data()
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading courses: {e}")
        return []


# --- ПРОВЕРКА ОКРУЖЕНИЯ (ENVIRONMENT CHECK) ---

def _check_java_17():
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            ["java", "-version"],
            capture_output=True, text=True, startupinfo=startupinfo
        )
        output = result.stderr + result.stdout

        version_match = re.search(r'version "17\.\d+\.\d+', output)
        is_17 = bool(version_match)

        version_str = "Unknown"
        if version_match:
            version_str = version_match.group(0).replace('version "', '')

        return {"installed": is_17, "version": version_str if is_17 else "Wrong Ver", "tooltip": output.split('\n')[0]}
    except FileNotFoundError:
        return {"installed": False, "version": "Missing", "tooltip": "Java not in PATH"}


def _check_program_path(possible_paths, name_for_display):
    for path in possible_paths:
        expanded_path = os.path.expandvars(path)
        if os.path.exists(expanded_path):
            return {"installed": True, "version": "Installed", "tooltip": f"Found at: {expanded_path}"}
    return {"installed": False, "version": "Missing", "tooltip": f"{name_for_display} not found"}


def _find_jetbrains_product(product_name_start):
    base_paths = [
        r"C:\Program Files\JetBrains",
        r"C:\Program Files (x86)\JetBrains",
        r"C:\Program Files (x86)\JetBrains",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs")
    ]
    for base in base_paths:
        if os.path.exists(base):
            try:
                for folder in os.listdir(base):
                    if folder.startswith(product_name_start):
                        return {"installed": True, "version": folder,
                                "tooltip": f"Found at: {os.path.join(base, folder)}"}
            except:
                continue
    return {"installed": False, "version": "Missing", "tooltip": "Not found"}


@eel.expose
def check_software_versions():
    print("🔎 Checking software...")
    report = {}

    # 1. VS Code
    report["vscode"] = _check_program_path([
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe"
    ], "VS Code")

    # 2. Unity Hub
    report["unity"] = _check_program_path([
        r"C:\Program Files\Unity Hub\Unity Hub.exe",
        r"C:\Program Files (x86)\Unity Hub\Unity Hub.exe"
    ], "Unity Hub")

    # 3. Visual Studio
    report["visualstudio"] = _check_program_path([
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\Common7\IDE\devenv.exe",
        r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\devenv.exe"
    ], "Visual Studio")

    # 4. Minecraft Education
    report["mcedu"] = _check_program_path([
        r"C:\Program Files (x86)\Minecraft Education Edition\minecraft.windows.exe",
        r"%LOCALAPPDATA%\Packages\Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe"
    ], "MC Education")

    # 5. IntelliJ IDEA (Твой кастомный путь + стандартный поиск)
    custom_idea = r"D:\IntelliJ IDEA 2025.3.1.1\bin\idea64.exe"
    if os.path.exists(custom_idea):
        report["intellij"] = {
            "installed": True,
            "version": "Custom (D:)",
            "tooltip": f"Found at: {custom_idea}"
        }
    else:
        report["intellij"] = _find_jetbrains_product("IntelliJ IDEA")

    return report


# --- ЗАПУСК РЕДАКТОРОВ (LAUNCHER) ---

@eel.expose
def launch_editor(path, editor_type):
    clean_path = os.path.normpath(path)
    print(f"🚀 Launching {editor_type} for: {clean_path}")

    try:
        if editor_type == 'vscode':
            cmd = f'code "{clean_path}"'
            subprocess.Popen(cmd, shell=True)
            return {"status": "success"}

        elif editor_type == 'unity':
            hub_paths = [
                r"C:\Program Files\Unity Hub\Unity Hub.exe",
                r"C:\Program Files (x86)\Unity Hub\Unity Hub.exe"
            ]
            hub_exe = None
            for p in hub_paths:
                if os.path.exists(p):
                    hub_exe = p
                    break

            if not hub_exe:
                return {"status": "error", "msg": "Unity Hub не найден."}

            subprocess.Popen([hub_exe, "--", "--open", clean_path])
            return {"status": "success"}

        elif editor_type == 'intellij':
            # === ОБНОВЛЕННЫЙ ЗАПУСК IDEA ===
            custom_exe = r"D:\IntelliJ IDEA 2025.3.1.1\bin\idea64.exe"

            if os.path.exists(custom_exe):
                # Запускаем конкретный файл
                subprocess.Popen([custom_exe, clean_path])
            else:
                # Пытаемся запустить через команду системы (если в PATH)
                subprocess.Popen(["idea64.exe", clean_path], shell=True)

            return {"status": "success"}

        else:
            return {"status": "error", "msg": f"Unknown editor: {editor_type}"}

    except Exception as e:
        return {"status": "error", "msg": str(e)}


@eel.expose
def open_folder(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.call(["open", path])


# --- СКАЧИВАНИЕ ПРОЕКТОВ (STREAM TO DISK) ---

def ensure_project_folder(base_path, course_name, student_name, project_name):
    full_path = os.path.join(
        base_path,
        "DigiScool",  # ИСПРАВЛЕНО НА DIGISCOOL
        sanitize_filename(course_name),
        sanitize_filename(student_name),
        sanitize_filename(project_name)
    )
    try:
        os.makedirs(full_path, exist_ok=True)
        return {"status": "success", "path": full_path}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@eel.expose
def download_project(course_id, project_name, student_name, project_index):
    # 1. Config
    config = _load_config()
    base_path = config.get("download_path") or _get_default_download_path()

    # 2. URL Search
    target_url = None
    try:
        json_path = _load_course_data()
        with open(json_path, 'r', encoding='utf-8') as f:
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
        return {"status": "error", "msg": "URL not found!"}

    # 3. Folder Prep
    folder_result = ensure_project_folder(base_path, course_id, student_name, project_name)
    if folder_result['status'] == 'error':
        return folder_result
    target_dir = folder_result['path']
    temp_zip_path = os.path.join(target_dir, "temp.zip")

    try:
        # 4. DOWNLOAD STREAM
        eel.update_ui_progress(project_index, 5, "Connecting...")
        response = requests.get(target_url, stream=True)
        total_length = response.headers.get('content-length')

        with open(temp_zip_path, 'wb') as f:
            dl_size = 0
            chunk_size = 65536
            if total_length is None:
                fake_percent = 10
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    dl_size += len(chunk)
                    mb = round(dl_size / 1048576, 1)
                    fake_percent = 10 if fake_percent > 90 else fake_percent + 1
                    if dl_size % (1024 * 1024) == 0:
                        eel.update_ui_progress(project_index, fake_percent, f"DL: {mb} MB...")
                        eel.sleep(0.001)
            else:
                total_length = int(total_length)
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    dl_size += len(chunk)
                    percent = int((dl_size / total_length) * 100)
                    if dl_size % (1024 * 512) == 0:
                        eel.update_ui_progress(project_index, percent, f"Loading: {percent}%")
                        eel.sleep(0.001)

        # 5. UNZIP
        eel.update_ui_progress(project_index, 98, "Unzipping...")
        with zipfile.ZipFile(temp_zip_path, 'r') as z:
            root = z.namelist()[0]
            for file in z.namelist():
                if file == root: continue
                rel_path = file[len(root):]
                if not rel_path or rel_path.startswith("__MACOSX"): continue

                dest = os.path.join(target_dir, rel_path)
                if file.endswith('/'):
                    os.makedirs(dest, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f_out:
                        f_out.write(z.read(file))

        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

        eel.update_ui_progress(project_index, 100, "Done!")
        return {"status": "success", "path": target_dir}

    except Exception as e:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        return {"status": "error", "msg": str(e)}


@eel.expose
def get_installed_projects(course_id):
    config = _load_config()
    base_path = config.get("download_path") or _get_default_download_path()
    course_path = os.path.join(base_path, "DigiScool", sanitize_filename(course_id))  # DigiScool fix

    found_projects = []
    if os.path.exists(course_path):
        try:
            students = os.listdir(course_path)
            for student in students:
                student_path = os.path.join(course_path, student)
                if os.path.isdir(student_path):
                    projects = os.listdir(student_path)
                    for proj in projects:
                        found_projects.append({
                            "name": proj,
                            "student": student,
                            "path": os.path.join(student_path, proj),
                            "course_id": course_id
                        })
        except:
            pass
    return found_projects


if __name__ == '__main__':
    eel.init('web')
    eel.start('index.html', size=(1000, 700))