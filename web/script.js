// Глобальная переменная для хранения загруженных курсов
let allCourses = [];

window.onload = async function() {
    await loadCourses();
};

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

    course.projects.forEach(proj => {
        const projectHtml = `
            <div class="project-item">
                <div class="project-info">
                    <h3>${proj.name}</h3>
                </div>
                <button class="btn-download" onclick="alert('Скоро здесь будет скачивание!')">
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