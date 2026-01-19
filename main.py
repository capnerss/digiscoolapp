import eel

eel.init('web')


@eel.expose
def hello_world():
    result = f"Hello world"
    return result


eel.start('index.html', size=(800, 600), port=5000)