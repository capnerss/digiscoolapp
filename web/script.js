// script.js - Final Sprint 3 Version

// Глобальные переменные
let allCourses = [];
let currentCourse = null;

// --- 1. ЗАПУСК (INITIALIZATION) ---
window.addEventListener('load', async () => {
    console.log("🚀 App Starting...");

    // 1. Проверяем систему
    await checkSystem();

    // 2. Грузим настройки
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
    if (!container) return;

    container.innerHTML = '';

    courses.forEach(course => {
        const item = document.createElement('div');
        item.className = 'menu-item';
        item.id = `menu-${course.id}`;
        item.onclick = () => selectCourse(course.id);

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

    // Рендер секции создания
    renderCreateSection(currentCourse);

    // Рендер установленных проектов
    try {
        await renderInstalledProjects(courseId);
    } catch (e) {
        console.warn("⚠️ Cannot load installed projects:", e);
    }

    // Обновляем шапку (требования)
    updateRequirementsUI(currentCourse);
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

        item.onclick = (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
            selectTemplateUI(item);
        };

        item.innerHTML = `
            <div class="template-info">
                <span class="tmpl-name" style="margin-left: 10px;">${proj.name}</span>
            </div>
            
            <div class="create-controls" style="display:none; gap:10px;">
                <input type="text" class="input-dark student-name" placeholder="Name (e.g. Alex)">
                <button class="btn-add" onclick="startDownload('${proj.name}', this)">[ + ]</button>
            </div>
        `;

        container.appendChild(item);
        if (index === 0) selectTemplateUI(item);
    });
}

function selectTemplateUI(domElement) {
    document.querySelectorAll('.template-item').forEach(el => {
        el.classList.remove('selected');
        const controls = el.querySelector('.create-controls');
        const name = el.querySelector('.tmpl-name');
        if (controls) controls.style.display = 'none';
        if (name) name.style.fontWeight = 'normal';
    });

    domElement.classList.add('selected');
    const controls = domElement.querySelector('.create-controls');
    const name = domElement.querySelector('.tmpl-name');

    if (controls) {
        controls.style.display = 'flex';
        setTimeout(() => {
            const input = controls.querySelector('input');
            if (input) input.focus();
        }, 50);
    }
    if (name) name.style.fontWeight = 'bold';
}

// --- 4. СЕКЦИЯ "УСТАНОВЛЕННЫЕ ПРОЕКТЫ" (INSTALLED) ---
// ВАЖНО: Эта функция была полностью переписана для поддержки запуска редакторов

async function renderInstalledProjects(courseId) {
    const container = document.querySelector('.section-list');
    if (!container) return;

    container.innerHTML = '<div style="padding:10px; color:#666;">Loading...</div>';

    const projects = await eel.get_installed_projects(courseId)();

    container.innerHTML = '';

    if (!projects || projects.length === 0) {
        container.innerHTML = '<div style="padding:15px; color:#555; font-style:italic;">No projects installed yet.</div>';
        return;
    }

    projects.forEach(proj => {
        const safePath = (proj.path || "").replace(/\\/g, '\\\\');

        // 1. Определяем тип редактора для кнопки
        const editorType = currentCourse.editor || 'vscode';
        let runButtonHTML = '';

        // 2. Генерируем красивую кнопку в зависимости от редактора
        if (editorType === 'unity') {
            runButtonHTML = `
                <button class="btn-action" 
                        style="background-color: #000; color: #fff; border: 1px solid #333;"
                        onclick="openProjectInEditor('${safePath}', 'unity', this)">
                    OPEN UNITY 🧊
                </button>`;
        } else if (editorType === 'intellij') {
            runButtonHTML = `
                <button class="btn-action" 
                        style="background: linear-gradient(45deg, #FF6B6B, #9B59B6); color: white; border:none;"
                        onclick="openProjectInEditor('${safePath}', 'intellij', this)">
                    OPEN IDEA 🚀
                </button>`;
        } else {
            // Default: VS Code
            runButtonHTML = `
                <button class="btn-action" 
                        style="color: #4facfe; border-color: #4facfe;"
                        onclick="openProjectInEditor('${safePath}', 'vscode', this)">
                    OPEN CODE 🔵
                </button>`;
        }

        const row = document.createElement('div');
        row.className = 'project-row';
        row.innerHTML = `
            <div>
                <div class="project-name">${proj.name}</div>
                <div style="font-size:0.75rem; color:#666;">Student: ${proj.student}</div>
            </div>
            <div class="project-actions">
                ${runButtonHTML}
                <button class="btn-action" onclick="eel.open_folder('${safePath}')">📂 FOLDER</button>
            </div>
        `;
        container.appendChild(row);
    });
}

// --- НОВАЯ ФУНКЦИЯ ЗАПУСКА РЕДАКТОРА ---
async function openProjectInEditor(path, editorType, btnElement) {
    const originalText = btnElement.innerHTML;

    // Анимация загрузки
    btnElement.textContent = "⏳ Launching...";
    btnElement.disabled = true;

    // Вызываем Python
    const result = await eel.launch_editor(path, editorType)();

    if (result.status === 'error') {
        alert(`Ошибка запуска редактора (${editorType}):\n${result.msg}\n\nОткрываем просто папку.`);
        eel.open_folder(path);
    }

    // Возвращаем кнопку
    setTimeout(() => {
        btnElement.innerHTML = originalText;
        btnElement.disabled = false;
    }, 2000);
}

// --- 5. ЛОГИКА СКАЧИВАНИЯ (DOWNLOAD) ---

async function startDownload(projectName, btnElement) {
    const parent = btnElement.parentElement;
    const input = parent.querySelector('input');
    const studentName = input.value.trim();

    if (!studentName) {
        alert("Enter student name!");
        input.focus();
        return;
    }

    btnElement.disabled = true;
    const originalText = btnElement.textContent;
    btnElement.textContent = "⏳";

    const courseId = currentCourse.id;

    // Запускаем скачивание
    const result = await eel.download_project(courseId, projectName, studentName, 0)();

    if (result.status === 'success') {
        btnElement.textContent = "✔";
        btnElement.style.backgroundColor = "#4caf50";

        setTimeout(() => {
            btnElement.textContent = originalText;
            btnElement.disabled = false;
            btnElement.style.backgroundColor = "";
            input.value = "";
            // Обновляем список установленных
            renderInstalledProjects(courseId);
        }, 2000);
    } else {
        alert("Error: " + result.msg);
        btnElement.textContent = "❌";
        setTimeout(() => {
            btnElement.textContent = originalText;
            btnElement.disabled = false;
        }, 2000);
    }
}

eel.expose(update_ui_progress);
function update_ui_progress(index, percent, message) {
    const activeBtn = document.querySelector('.template-item.selected .btn-add');
    if (activeBtn) {
        activeBtn.style.minWidth = "80px";
        activeBtn.textContent = `${percent}%`;
        if (percent >= 100) activeBtn.textContent = "DONE";
    }
}

// --- 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

function getColorForCourse(id) {
    const colors = {'minecraft': '#4caf50', 'python': '#ffeb3b', 'roblox': '#e53935', 'unity': '#000000'};
    for (let key in colors) {
        if (id.toLowerCase().includes(key)) return colors[key];
    }
    return '#4f46e5';
}

async function checkSystem() {
    try {
        const results = await eel.check_software_versions()();
        // Используем список ключей, согласованный с HTML
        const tools = [ 'intellij', 'vscode', 'unity', 'visualstudio', 'mcedu'];

        tools.forEach(tool => {
            if (results[tool]) {
                updateStatusUI(tool, results[tool]);
            }
        });
    } catch (e) {
        console.warn("System check failed:", e);
    }
}

function updateStatusUI(tool, data) {
    const el = document.getElementById(`status-${tool}`);
    if (!el) return;

    const icon = el.querySelector('.status-icon');

    if (data.installed) {
        if (icon) icon.textContent = '🟢';
        el.title = `${tool}: Installed`;
        el.style.opacity = '1';
    } else {
        if (icon) icon.textContent = '🔴';
        el.title = `${tool} missing`;
        el.style.opacity = '0.5';
    }
}

async function loadSettings() {
    try {
        const settings = await eel.get_current_settings()();
        const label = document.getElementById('install-path-label');
        if (label) {
            label.innerText = settings.download_path || "Default (DigiScool)";
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
        if (currentCourse) renderInstalledProjects(currentCourse.id);
    }
}

// Функция для DIG-38 (Подсветка требований)
function updateRequirementsUI(course) {
    const allTools = ['intellij', 'vscode', 'unity', 'visualstudio', 'mcedu'];
    const requiredTools = course.requirements || [];

    allTools.forEach(tool => {
        const el = document.getElementById(`status-${tool}`);
        if (!el) return;

        el.classList.remove('dimmed', 'highlight');
        const isInstalled = el.querySelector('.status-icon').textContent.includes('🟢');

        if (requiredTools.includes(tool)) {
            el.classList.add('highlight');
            if (!isInstalled) {
                el.title = `⚠️ Missing Requirement: ${tool}`;
            }
        } else {
            el.classList.add('dimmed');
            el.title = `${tool} (Not required)`;
        }
    });
}