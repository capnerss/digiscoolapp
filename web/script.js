// Функция запускается при загрузке окна
window.onload = async function() {
    await loadCourses();
};

async function loadCourses() {
    // 1. Зовем Python функцию (из DIG-10)
    // Обрати внимание на двойные скобки ()() - особенность Eel для async
    const courses = await eel.get_courses()();

    // Для отладки выведем в консоль то, что пришло
    console.log("Data received from Python:", courses);

    const grid = document.getElementById('courses-grid');
    grid.innerHTML = ''; // Очистим контейнер на всякий случай

    // 2. Бежим по каждому курсу в списке
    courses.forEach(course => {
        // Считаем количество проектов
        const projectCount = course.projects.length;

        // Маленькая логика для красивого текста (1 projekt / 2 projekti)
        // Если проект 1 - "projekt", иначе "projekti"
        const suffix = projectCount === 1 ? "projekt" : "projekti";

        // 3. Создаем HTML карточки через шаблонную строку (обратные кавычки `)
        // Мы добавляем onclick, чтобы потом (в след. задачах) открывать курс
        const cardHtml = `
            <div class="course-card" onclick="openCourse('${course.id}')">
                <div class="card-icon">📚</div> 
                <h3>${course.title}</h3>
                <p>${projectCount} ${suffix}</p>
            </div>
        `;

        // 4. Добавляем полученный HTML в сетку
        grid.innerHTML += cardHtml;
    });
}

// Заглушка для клика (реализуем позже)
function openCourse(courseId) {
    console.log("Clicked course:", courseId);
    // В будущем здесь будет переход на другую страницу
}