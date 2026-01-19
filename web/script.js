// Глобальная переменная для хранения загруженных курсов
let allCourses = [];


window.onload = async function() {
    // Сначала запускаем проверку системы
    await checkSystem();
    await loadCourses();
};


// НОВАЯ ФУНКЦИЯ
async function checkSystem() {
    console.log("Checking system requirements...");

    // 1. Зовем Python (функцию из Task 1)
    const status = await eel.check_software_versions()();
    console.log("System Status:", status);

    // 2. Функция-помощник для обновления одного значка
    updateBadge('java', status.java);
    updateBadge('node', status.node);
    updateBadge('git', status.git);
}

function updateBadge(idName, info) {
    const el = document.getElementById(`status-${idName}`);
    const iconSpan = el.querySelector('.icon');

    // Удаляем старые классы (checking)
    el.classList.remove('checking', 'success', 'error');

    if (info.installed) {
        // УСПЕХ ✅
        el.classList.add('success');
        iconSpan.innerText = '✅';
        // Показываем версию при наведении
        el.title = `Installed: ${info.version}`;
    } else {
        // ОШИБКА ❌
        el.classList.add('error');
        iconSpan.innerText = '❌';
        el.title = "Not installed! (Puudub)";
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