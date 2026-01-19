// Глобальная переменная для хранения загруженных курсов
let allCourses = [];


window.onload = async function() {
    // Сначала запускаем проверку системы
    await checkSystem();
    await loadCourses();
    await loadSettings();
};

// Загружаем настройки при старте
async function loadSettings() {
    const settings = await eel.get_current_settings()();
    document.getElementById('install-path').value = settings.download_path;
}

// Вызов диалога выбора папки
async function changeFolder() {
    // Меняем текст кнопки, чтобы показать реакцию
    const btn = document.querySelector('.btn-secondary');
    const originalText = btn.textContent;
    btn.textContent = 'Opening...';

    // Вызываем Python (окно откроется поверх браузера)
    const newPath = await eel.choose_folder()();

    if (newPath) {
        // Если выбрали папку — обновляем поле
        document.getElementById('install-path').value = newPath;
        console.log("New path saved:", newPath);
    }

    btn.textContent = originalText;
}
// Функция запуска проверки системы
async function checkSystem() {
    console.log("🔍 Starting Environment Check...");

    // 1. Устанавливаем статус "loading" перед запросом (UX)
    const tools = ['java', 'node', 'git'];
    tools.forEach(tool => setStatusLoading(tool));

    try {
        // 2. Вызываем Python функцию (await, так как это асинхронный вызов через Eel)
        // Ожидаем ответ вида: {"java": {"installed": true, "version": "17.0"}, ...}
        const results = await eel.check_software_versions()();

        console.log("📊 System Check Results:", results);

        // 3. Обновляем UI на основе данных
        for (const [tool, data] of Object.entries(results)) {
            updateStatusUI(tool, data);
        }

    } catch (error) {
        console.error("❌ Failed to check system requirements:", error);
        // В случае критической ошибки помечаем всё красным
        tools.forEach(tool => updateStatusUI(tool, { installed: false, version: "Error" }));
    }
}

// Хелпер для установки UI (Clean Code: разделяем логику и представление)
function updateStatusUI(toolName, data) {
    const container = document.getElementById(`status-${toolName}`);
    if (!container) return;

    const iconSpan = container.querySelector('.status-icon');
    const versionSpan = container.querySelector('.status-version');

    // Сброс классов
    container.classList.remove('status-loading', 'status-ok', 'status-fail');

    if (data.installed) {
        // Успех ✅
        container.classList.add('status-ok');
        iconSpan.textContent = '✅'; // Или используй иконку FontAwesome
        versionSpan.textContent = data.version;
        container.title = `${toolName} installed: v${data.version}`; // Tooltip при наведении
    } else {
        // Ошибка ❌
        container.classList.add('status-fail');
        iconSpan.textContent = '❌';
        versionSpan.textContent = 'Not Found';
        container.title = `${toolName} is missing!`;
    }
}

// Хелпер для состояния загрузки
function setStatusLoading(toolName) {
    const container = document.getElementById(`status-${toolName}`);
    if (container) {
        container.classList.add('status-loading');
        container.querySelector('.status-icon').textContent = '⏳';
    }
}


async function loadCourses() {
    const courses = await eel.get_courses()();
    // Сохраняем данные глобально, чтобы использовать в других функциях
    allCourses = courses;

    const grid = document.getElementById('courses-grid');
    grid.innerHTML = '';

    courses.forEach(course => {
        const projectCount = course.projects.length;
        const suffix = projectCount === 1 ? "projekt" : "projekti";

        const cardHtml = `
            <div class="course-card" onclick="openCourse('${course.id}')">
                <div class="card-icon">📚</div> 
                <h3>${course.title}</h3>
                <p>${projectCount} ${suffix}</p>
            </div>
        `;
        grid.innerHTML += cardHtml;
    });
}

// 1. Функция открытия курса
function openCourse(courseId) {
    // Находим нужный курс в массиве по ID
    const course = allCourses.find(c => c.id === courseId);

    if (!course) {
        console.error("Курс не найден:", courseId);
        return;
    }

    // Заполняем заголовок
    document.getElementById('course-title').innerText = course.title;

    // Генерируем список проектов
    const projectsContainer = document.getElementById('projects-list');
    projectsContainer.innerHTML = ''; // Очищаем старое


    // Очищаем и поле имени при открытии нового курса
    document.getElementById('student-name').value = '';

    course.projects.forEach((proj, index) => {
        // Создаем уникальные ID для элементов этого проекта
        // Например: progress-bar-0, status-text-0
        const progressBarId = `progress-bar-${index}`;
        const statusTextId = `status-text-${index}`;
        const containerId = `progress-container-${index}`;

        const projectHtml = `
            <div class="project-item">
                <div class="project-info">
                    <h3>${proj.name}</h3>
                    
                    <div id="${containerId}" class="progress-container">
                        <div class="progress-info">
                            <span id="${statusTextId}">Ожидание...</span>
                            <span></span>
                        </div>
                        <div class="progress-track">
                            <div id="${progressBarId}" class="progress-fill"></div>
                        </div>
                    </div>

                </div>
                
                <button class="btn-download" onclick="startDownload('${course.id}', '${proj.name}', ${index})">
                    Скачать
                </button>
            </div>
        `;
        projectsContainer.innerHTML += projectHtml;
    });

    // ПЕРЕКЛЮЧЕНИЕ ВИДИМОСТИ (Суть задачи)
    document.getElementById('main-view').style.display = 'none';
    document.getElementById('details-view').style.display = 'block';
}

// 2. Функция "Назад"
function goBack() {
    document.getElementById('details-view').style.display = 'none';
    document.getElementById('main-view').style.display = 'block';
}


async function startDownload(courseId, projectName, index) {
    const nameInput = document.getElementById('student-name');
    const name = nameInput.value;

    if (!name) {
        alert("Пожалуйста, введите имя!");
        return;
    }

    // 1. Показываем бар
    const container = document.getElementById(`progress-container-${index}`);
    container.style.display = 'block';

    // Блокируем кнопку
    const btn = container.parentElement.querySelector('.btn-download');
    if (btn) btn.disabled = true;

    console.log("Вызываю Python..."); // Лог для проверки в браузере

    // 2. ЗОВЕМ PYTHON (Вот этого могло не хватать)
    // Мы передаем ID курса, Имя проекта, Имя студента и Индекс (для прогресс-бара)
    let result = await eel.download_project(courseId, projectName, name, index)();

    // 3. Смотрим результат
    console.log("Ответ от Python:", result);

    if (result && result.status === "success") {
        alert("Папка создана: " + result.path);
        // Тут можно поставить прогресс на 100%
        update_ui_progress(index, 100, "Готово!");
    } else {
        alert("Ошибка: " + (result ? result.msg : "Неизвестная ошибка"));
    }

    if (btn) btn.disabled = false;
}
// Делаем функцию доступной, чтобы Python мог её вызывать
eel.expose(update_ui_progress);

/**
 * Обновляет прогресс-бар конкретного проекта.
 * @param {number} index - Индекс проекта в списке (0, 1, 2...)
 * @param {number} percent - Процент загрузки (0-100)
 * @param {string} text - Текстовое сообщение (например, "Скачивание...")
 */
function update_ui_progress(index, percent, text) {
    // 1. Находим элементы по ID, которые мы создали в DIG-14
    const progressBar = document.getElementById(`progress-bar-${index}`);
    const statusText = document.getElementById(`status-text-${index}`);

    if (progressBar && statusText) {
        // 2. Меняем ширину полоски
        progressBar.style.width = percent + '%';

        // 3. Меняем текст
        statusText.innerText = text;

        // 4. Маленькая красота: если 100%, меняем цвет на зеленый
        if (percent >= 100) {
            progressBar.style.backgroundColor = '#2ecc71'; // Зеленый
        } else {
             // Возвращаем синий (на случай, если качаем второй раз)
            progressBar.style.backgroundColor = '#3498db';
        }
    } else {
        console.error(`Элементы прогресс-бара для индекса ${index} не найдены!`);
    }
}