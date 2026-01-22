// Глобальные переменные
let allCourses = [];
let currentCourse = null;

// --- 1. ЗАПУСК (INITIALIZATION) ---
window.addEventListener('load', async () => {
    console.log("🚀 App Starting...");

    // 1. Проверяем систему (Старая добрая функция)
    await checkSystem();

    // 2. Грузим настройки (Путь установки)
    await loadSettings();

    // 3. Загружаем курсы
    await loadCourses();
});

// --- 2. ЛОГИКА КУРСОВ (CORE LOGIC) ---

async function loadCourses() {
    try {
        allCourses = await eel.get_courses()();
        console.log("📚 Courses loaded:", allCourses.length);

        renderSidebar(allCourses);

        // Авто-выбор первого курса
        if (allCourses.length > 0) {
            selectCourse(allCourses[0].id);
        }
    } catch (e) {
        console.error("Critical Error loading courses:", e);
        document.body.innerHTML = `<h2 style="color:red; padding:20px;">Ошибка связи с Python backend. Проверьте консоль.</h2>`;
    }
}

function renderSidebar(courses) {
    const container = document.querySelector('.sidebar-menu');
    if (!container) return; // Защита если HTML не тот

    container.innerHTML = '';

    courses.forEach(course => {
        const item = document.createElement('div');
        item.className = 'menu-item';
        item.id = `menu-${course.id}`;
        item.onclick = () => selectCourse(course.id);

        // Простая иконка (первые 2 буквы)
        const shortName = (course.title || "??").substring(0, 2).toUpperCase();

        item.innerHTML = `
            <div class="icon-box" style="background: ${getColorForCourse(course.id)}">${shortName}</div>
            <span class="menu-label">${course.title}</span>
        `;
        container.appendChild(item);
    });
}

async function selectCourse(courseId) {
    console.log("👉 Selected course:", courseId);

    currentCourse = allCourses.find(c => c.id === courseId);
    if (!currentCourse) return;

    // Подсветка в меню
    document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
    const activeItem = document.getElementById(`menu-${courseId}`);
    if (activeItem) activeItem.classList.add('active');

    // Рендер правой части (Список проектов для создания)
    renderCreateSection(currentCourse);

    // Рендер уже установленных (Safe Mode: если функции нет в Python, не упадем)
    try {
        await renderInstalledProjects(courseId);
    } catch (e) {
        console.warn("⚠️ Cannot load installed projects (maybe function missing in main.py):", e);
        const list = document.querySelector('.section-list');
        if (list) list.innerHTML = `<div style="padding:15px; color:#666;">Список установленных проектов недоступен</div>`;
    }
}

// --- 3. СЕКЦИЯ "СОЗДАТЬ ПРОЕКТ" (CREATE NEW) ---

function renderCreateSection(course) {
    const container = document.querySelector('.template-list');
    if (!container) return;

    container.innerHTML = '';

    if (!course.projects || course.projects.length === 0) {
        container.innerHTML = '<div style="padding:15px;">Нет доступных шаблонов</div>';
        return;
    }

    course.projects.forEach((proj, index) => {
        const item = document.createElement('div');
        item.className = 'template-item';

        // Клик по строке
        item.onclick = (e) => {
            // Игнорируем клик, если нажали прямо в поле ввода или кнопку
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
            selectTemplateUI(item);
        };

        item.innerHTML = `
            <div class="template-info">
                <span class="tmpl-name" style="margin-left: 10px;">${proj.name}</span>
            </div>
            
            <div class="create-controls" style="display:none; gap:10px;">
                <input type="text" class="input-dark student-name" placeholder="Имя (напр. Alex)">
                <button class="btn-add" onclick="startDownload('${proj.name}', this)">+</button>
            </div>
        `;

        container.appendChild(item);

        // Выбираем первый элемент сразу
        if (index === 0) selectTemplateUI(item);
    });
}

function selectTemplateUI(domElement) {
    // Сброс всех
    document.querySelectorAll('.template-item').forEach(el => {
        el.classList.remove('selected');
        const controls = el.querySelector('.create-controls');
        const name = el.querySelector('.tmpl-name');
        if (controls) controls.style.display = 'none';
        if (name) name.style.fontWeight = 'normal';
    });

    // Активация текущего
    domElement.classList.add('selected');
    const controls = domElement.querySelector('.create-controls');
    const name = domElement.querySelector('.tmpl-name');

    if (controls) {
        controls.style.display = 'flex';
        // Фокус на поле ввода через 50мс (чтобы браузер успел отрисовать)
        setTimeout(() => {
            const input = controls.querySelector('input');
            if (input) input.focus();
        }, 50);
    }
    if (name) name.style.fontWeight = 'bold';
}

// --- 4. СЕКЦИЯ "УСТАНОВЛЕННЫЕ ПРОЕКТЫ" (INSTALLED) ---

async function renderInstalledProjects(courseId) {
    const container = document.querySelector('.section-list');
    if (!container) return;

    container.innerHTML = '<div style="padding:10px; color:#666;">Поиск проектов...</div>';

    // ВАЖНО: Тут может быть ошибка, если main.py старый
    // eel.get_installed_projects вернет ошибку, которую мы ловим выше
    const projects = await eel.get_installed_projects(courseId)();

    container.innerHTML = ''; // Очищаем "Loading..."

    if (!projects || projects.length === 0) {
        container.innerHTML = '<div style="padding:15px; color:#555; font-style:italic;">Установленных проектов пока нет.</div>';
        return;
    }

    projects.forEach(proj => {
        // 1. Защита путей Windows (превращаем C:\Project в C:\\Project)
        const safePath = (proj.path || "").replace(/\\/g, '\\\\');

        // 2. ОПРЕДЕЛЯЕМ ТИП РЕДАКТОРА
        // Берем настройку из текущего курса (если не указано — по умолчанию vscode)
        const editorType = currentCourse.editor || 'vscode';

        // 3. НАСТРАИВАЕМ КНОПКУ ЗАПУСКА
        let runButtonHTML = '';

        if (editorType === 'unity') {
            // Черная кнопка для Unity
            runButtonHTML = `
                <button class="btn-action" 
                        style="background-color: #222; color: #fff; border-color: #444;"
                        onclick="openProjectInEditor('${safePath}', 'unity', this)">
                    OPEN UNITY 🧊
                </button>`;
        } else {
            // Стандартная кнопка для VS Code
            runButtonHTML = `
                <button class="btn-action" 
                        onclick="openProjectInEditor('${safePath}', 'vscode', this)">
                    OPEN CODE 🔵
                </button>`;
        }

        // 4. СОБИРАЕМ HTML СТРОКИ
        const row = document.createElement('div');
        row.className = 'project-row';
        row.innerHTML = `
            <div>
                <div class="project-name">${proj.name}</div>
                <div style="font-size:0.75rem; color:#666;">Студент: ${proj.student}</div>
            </div>
            <div class="project-actions">
                ${runButtonHTML}
                
                <button class="btn-action" onclick="eel.open_folder('${safePath}')">📂 FOLDER</button>
            </div>
        `;
        container.appendChild(row);
    });
}

// --- 5. ЛОГИКА СКАЧИВАНИЯ (DOWNLOAD) ---

async function startDownload(projectName, btnElement) {
    // 1. Ищем поле ввода рядом с нажатой кнопкой
    const parent = btnElement.parentElement; // div.create-controls
    const input = parent.querySelector('input');
    const studentName = input.value.trim();

    if (!studentName) {
        alert("Пожалуйста, введите имя студента!");
        input.focus();
        return;
    }

    // 2. Блокируем кнопку
    btnElement.disabled = true;
    const originalText = btnElement.textContent;
    btnElement.textContent = "⏳";

    // 3. Запускаем
    const courseId = currentCourse.id;
    console.log(`📥 Start Download: ${courseId} / ${studentName} / ${projectName}`);

    // Передаем index=0, так как у нас теперь нет списка карточек с индексами
    const result = await eel.download_project(courseId, projectName, studentName, 0)();

    // 4. Обработка результата
    if (result.status === 'success') {
        btnElement.textContent = "✔";
        btnElement.style.backgroundColor = "#4caf50";

        setTimeout(() => {
            // Возвращаем как было
            btnElement.textContent = originalText;
            btnElement.disabled = false;
            btnElement.style.backgroundColor = "";
            input.value = ""; // Очищаем поле

            // Обновляем список сверху
            renderInstalledProjects(courseId);
        }, 2000);
    } else {
        alert("Ошибка: " + result.msg);
        btnElement.textContent = "❌";
        setTimeout(() => {
            btnElement.textContent = originalText;
            btnElement.disabled = false;
        }, 2000);
    }
}

// Эту функцию вызывает Python (eel.update_ui_progress)
eel.expose(update_ui_progress);
function update_ui_progress(index, percent, message) {
    console.log(`Progress: ${percent}% ${message}`);

    // Ищем кнопку внутри АКТИВНОГО (selected) шаблона
    const activeBtn = document.querySelector('.template-item.selected .btn-add');

    if (activeBtn) {
        // Превращаем кнопку в прогресс-бар
        activeBtn.style.minWidth = "60px";
        activeBtn.textContent = `${percent}%`;

        if (percent >= 100) {
            activeBtn.textContent = "OK";
        }
    }
}

// --- 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (HELPERS) ---

function getColorForCourse(id) {
    const colors = {'minecraft': '#4caf50', 'python': '#ffeb3b', 'roblox': '#e53935', 'js': '#fbc02d'};
    for (let key in colors) {
        if (id.toLowerCase().includes(key)) return colors[key];
    }
    return '#4f46e5';
}

// Старая логика проверки системы (работает с header)
async function checkSystem() {
    try {
        const results = await eel.check_software_versions()();
        for (const [tool, data] of Object.entries(results)) {
            updateStatusUI(tool, data);
        }
    } catch (e) {
        console.warn("System check failed:", e);
    }
}

// Функция обновления иконок статуса
function updateStatusUI(tool, data) {
    const el = document.getElementById(`status-${tool}`);
    if (!el) return;

    const icon = el.querySelector('.status-icon');

    if (data.installed) {
        // Успех
        if (icon) {
            icon.textContent = '🟢'; // Или используй CSS класс .status-ok
            icon.style.textShadow = "0 0 5px #4caf50"; // Легкое свечение
        }
        el.style.opacity = '1';
        el.style.color = '#fff'; // Яркий белый текст
        el.title = `OK: ${data.tooltip || data.version}`;
    } else {
        // Ошибка / Не найдено
        if (icon) {
            icon.textContent = '🔴';
        }
        el.style.opacity = '0.6'; // Приглушаем
        el.style.color = '#aaa';
        el.title = `MISSING: ${tool} not found`;
    }
}

// Убедись, что checkSystem вызывает Python и передает данные сюда
async function checkSystem() {
    console.log("Checking environment...");
    try {
        const results = await eel.check_software_versions()();
        console.log("Env Results:", results);

        // Список ключей должен совпадать с Python report и HTML IDs
        const tools = ['java', 'vscode', 'unity', 'visualstudio', 'mcedu'];

        tools.forEach(tool => {
            if (results[tool]) {
                updateStatusUI(tool, results[tool]);
            }
        });
    } catch (e) {
        console.warn("System check failed:", e);
    }
}

// Старая логика настроек (работает с header)
async function loadSettings() {
    try {
        const settings = await eel.get_current_settings()();
        const label = document.getElementById('install-path-label');
        if (label) {
            label.innerText = settings.download_path || "Документы";
            label.title = settings.download_path;
        }
    } catch (e) {
        console.warn("Settings load failed:", e);
    }
}

async function changeFolder() {
    const newPath = await eel.choose_folder()();
    if (newPath) {
        const label = document.getElementById('install-path-label');
        if (label) label.innerText = newPath;

        // Перечитываем список проектов, если курс выбран
        if (currentCourse) renderInstalledProjects(currentCourse.id);
    }
}
// Функция-обработчик клика по кнопке запуска редактора
async function openProjectInEditor(path, editorType, btnElement) {
    console.log(`Attempting to open: ${path} with ${editorType}`);

    // Сохраняем исходный текст кнопки
    const originalText = btnElement.textContent;
    const originalColor = btnElement.style.backgroundColor;

    // Визуальная реакция
    btnElement.textContent = "⏳...";
    btnElement.disabled = true;

    // Вызываем Python
    const result = await eel.launch_editor(path, editorType)();

    if (result.status === 'error') {
        alert(`Не удалось запустить редактор!\nОшибка: ${result.msg}\n\nПопробуем просто открыть папку.`);
        eel.open_folder(path); // Запасной план
    } else {
        console.log("Editor launched successfully");
    }

    // Возвращаем кнопку в исходное состояние через секунду
    setTimeout(() => {
        btnElement.textContent = originalText;
        btnElement.style.backgroundColor = originalColor;
        btnElement.disabled = false;
    }, 1500);
}