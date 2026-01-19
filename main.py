import eel
import json
import os


eel.init('web')


@eel.expose
def hello_world():
    result = f"Hello world"
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


if __name__ == '__main__':
    eel.start('index.html', size=(1000, 700))