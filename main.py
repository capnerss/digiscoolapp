import eel
import json
import os
import re

eel.init('web')


@eel.expose
def download_project(course_id, project_name, student_name, project_index):
    # --- ВАЖНО: В этой задаче мы пока НЕ качаем файл ---
    # Мы только проверяем создание папок

    # Сначала найдем красивое название курса по ID (из data.json логики)
    # Для простоты пока возьмем course_id, но лучше потом передавать title

    # Вызываем нашу новую функцию
    print("--- СИГНАЛ ПОЛУЧЕН! ---")  # <--- Добавь это
    print(f"Данные: {course_id}, {student_name}")
    result = ensure_project_folder(course_id, student_name, project_name)

    if result["status"] == "success":
        # Эмуляция процесса (чтобы проверить, что путь вернулся)
        return result
    else:
        return result


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
    eel.start('index.html', size=(1000, 700))