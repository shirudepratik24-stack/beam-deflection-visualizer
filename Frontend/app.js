const API_BASE_URL = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
    fetchWelcomeMessage();
    fetchAllStudents();

    document.getElementById('filter-btn').addEventListener('click', filterByCourse);
    document.getElementById('reset-btn').addEventListener('click', resetFilters);
    document.getElementById('search-id-btn').addEventListener('click', searchByStudentId);
    document.getElementById('course-filter').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') filterByCourse();
    });
    document.getElementById('student-id-search').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') searchByStudentId();
    });
});

function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('status-message');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.classList.remove('hidden');
}

function hideStatus() {
    const statusEl = document.getElementById('status-message');
    statusEl.classList.add('hidden');
}

async function fetchWelcomeMessage() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (!response.ok) throw new Error('Failed to fetch home message');
        const data = await response.json();
        document.getElementById('welcome-message').textContent = data.message || 'Connected to FastAPI';
    } catch (error) {
        console.error('Error fetching welcome message:', error);
        document.getElementById('welcome-message').textContent = '⚠️ API server disconnected or offline.';
    }
}

async function fetchAllStudents(course = null) {
    try {
        let url = `${API_BASE_URL}/students`;
        if (course) {
            url += `?course=${encodeURIComponent(course)}`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch students');
        const students = await response.json();

        renderStudents(students);
        if (course) {
            showStatus(`Showing students for course: "${course}"`, 'info');
        } else {
            hideStatus();
        }
    } catch (error) {
        console.error('Error fetching students:', error);
        showStatus('Failed to load students. Ensure the FastAPI server is running.', 'error');
    }
}

async function searchByStudentId() {
    const studentIdInput = document.getElementById('student-id-search');
    const studentId = studentIdInput.value.trim();

    if (!studentId) {
        showStatus('Please enter a Student ID.', 'error');
        return;
    }

    if (!/^\d+$/.test(studentId) || Number(studentId) < 1) {
        showStatus('Please enter a valid positive Student ID.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/students/${studentId}`);
        if (!response.ok) {
            throw new Error(`Student search failed with status ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            showStatus(`Student with ID ${studentId} not found.`, 'error');
            renderStudents([]);
        } else {
            hideStatus();
            renderStudents([data]);
        }
    } catch (error) {
        console.error('Error finding student:', error);
        showStatus('Error searching for student.', 'error');
    }
}

function filterByCourse() {
    const courseInput = document.getElementById('course-filter');
    const course = courseInput.value.trim();
    if (course) {
        fetchAllStudents(course);
    } else {
        fetchAllStudents();
    }
}

function resetFilters() {
    document.getElementById('course-filter').value = '';
    document.getElementById('student-id-search').value = '';
    fetchAllStudents();
}

function renderStudents(students) {
    const grid = document.getElementById('students-grid');
    const studentCount = document.getElementById('student-count');
    grid.innerHTML = '';

    if (!Array.isArray(students) || students.length === 0) {
        studentCount.textContent = '0 students';
        grid.innerHTML = '<p class="no-students">No students found.</p>';
        return;
    }

    studentCount.textContent = `${students.length} student${students.length === 1 ? '' : 's'}`;

    students.forEach(student => {
        const card = document.createElement('div');
        card.className = 'student-card';
        card.innerHTML = `
            <span class="student-id">ID: #${student.id}</span>
            <h3 class="student-name">${escapeHtml(student.name)}</h3>
            <p class="student-detail">Age: ${student.age} years old</p>
            <span class="course-badge">📚 ${escapeHtml(student.course)}</span>
        `;
        grid.appendChild(card);
    });
}

function escapeHtml(text) {
    if (!text) return '';
    return text.toString().replace(/[&<>"']/g, (m) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    })[m]);
}
