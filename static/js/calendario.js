document.addEventListener('DOMContentLoaded', function() {
    const viewSelect = document.getElementById('view-select');
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const calendarDiv = document.getElementById('calendar');
    const addButton = document.getElementById('add-event-btn');
    const modal = document.getElementById('event-modal');
    const closeBtn = modal.querySelector('.close-btn');
    const eventDateInput = document.getElementById('event-date');
    const eventListContainer = document.createElement('div');
    eventListContainer.id = 'event-list-container';
    calendarDiv.parentNode.insertBefore(eventListContainer, calendarDiv.nextSibling);

    function populateYearSelect() {
        const currentYear = new Date().getFullYear();
        for (let i = currentYear - 5; i <= currentYear + 5; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i;
            if (i === currentYear) {
                option.selected = true;
            }
            yearSelect.appendChild(option);
        }
    }

    function getFirstDayOfWeek(date) {
        const day = date.getDay();
        return day === 0 ? 0 : day - 1;
    }

    function generateMiniCalendar(year, month) {
        const firstDayOfMonth = new Date(year, month - 1, 1);
        const lastDayOfMonth = new Date(year, month, 0);
        const daysInMonth = lastDayOfMonth.getDate();
        const startingDay = firstDayOfMonth.getDay();
        const monthName = new Intl.DateTimeFormat('es-ES', { month: 'short' }).format(firstDayOfMonth);

        let calendarHTML = `<div class="mini-month"><h3>${monthName}</h3><div class="mini-weekdays"><div>D</div><div>L</div><div>M</div><div>X</div><div>J</div><div>V</div><div>S</div></div><div class="mini-days">`;

        for (let i = 0; i < startingDay; i++) {
            calendarHTML += '<div></div>';
        }

        for (let day = 1; day <= daysInMonth; day++) {
            calendarHTML += `<div data-day="${day}" data-month="${month}" data-year="${year}">${day}</div>`;
        }

        calendarHTML += '</div></div>';
        return calendarHTML;
    }

    function generateYearView() {
        calendarDiv.innerHTML = '';
        const currentYear = new Date().getFullYear();

        for (let month = 1; month <= 12; month++) {
            calendarDiv.innerHTML += generateMiniCalendar(currentYear, month);
        }
        calendarDiv.classList.add('year-view');
        calendarDiv.classList.remove('month-view', 'day-view');

        const miniDays = calendarDiv.querySelectorAll('.mini-days div[data-day]');
        miniDays.forEach(dayElement => {
            dayElement.addEventListener('click', function() {
                const selectedDay = this.dataset.day;
                const selectedMonth = this.dataset.month;
                const selectedYear = this.dataset.year;
                const formattedDate = `${selectedYear}-${selectedMonth.padStart(2, '0')}-${selectedDay.padStart(2, '0')}`;
                eventDateInput.value = formattedDate;
                modal.style.display = 'block';
            });
        });
    }

    function generateMonthView(year, month) {
        calendarDiv.innerHTML = `
            <div class="weekday-name">Dom</div>
            <div class="weekday-name">Lun</div>
            <div class="weekday-name">Mar</div>
            <div class="weekday-name">Mié</div>
            <div class="weekday-name">Jue</div>
            <div class="weekday-name">Vie</div>
            <div class="weekday-name">Sáb</div>
        `;
        calendarDiv.classList.add('month-view');
        calendarDiv.classList.remove('year-view', 'day-view');

        const firstDayOfMonth = new Date(year, month - 1, 1);
        const lastDayOfMonth = new Date(year, month, 0);
        const daysInMonth = lastDayOfMonth.getDate();
        const startingDay = firstDayOfMonth.getDay();

        for (let i = 0; i < startingDay; i++) {
            const emptyCell = document.createElement('div');
            calendarDiv.appendChild(emptyCell);
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dayCell = document.createElement('div');
            dayCell.classList.add('day');
            dayCell.textContent = day;
            dayCell.dataset.day = day;
            calendarDiv.appendChild(dayCell);

            dayCell.addEventListener('click', function() {
                const selectedDay = this.dataset.day;
                const selectedMonth = monthSelect.value;
                const selectedYear = yearSelect.value;
                const formattedDate = `${selectedYear}-${selectedMonth.padStart(2, '0')}-${selectedDay.padStart(2, '0')}`;
                eventDateInput.value = formattedDate;
                modal.style.display = 'block';
            });
        }
    }

    function generateWeekView() {
        calendarDiv.innerHTML = '';
        calendarDiv.classList.remove('year-view', 'month-view', 'day-view');

        const today = new Date();
        const currentDayOfWeek = today.getDay();
        const diff = today.getDate() - currentDayOfWeek + (currentDayOfWeek === 0 ? -6 : 1);

        for (let i = 0; i < 7; i++) {
            const day = new Date(today.setDate(diff + i));
            const dayOfWeek = new Intl.DateTimeFormat('es-ES', { weekday: 'short' }).format(day);
            const dayOfMonth = day.getDate();

            const dayCell = document.createElement('div');
            dayCell.classList.add('day');
            dayCell.innerHTML = `<strong>${dayOfWeek}</strong><br>${dayOfMonth}`;
            calendarDiv.appendChild(dayCell);
        }
        today.setDate(today.getDate() - 7);
    }

    function generateDayView(year, month, day) {
        calendarDiv.innerHTML = '';
        calendarDiv.classList.add('day-view');
        calendarDiv.classList.remove('year-view', 'month-view');
        const selectedDate = new Date(year, month - 1, day);
        const formattedDate = new Intl.DateTimeFormat('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).format(selectedDate);
        const dayViewElement = document.createElement('div');
        dayViewElement.textContent = formattedDate;
        calendarDiv.appendChild(dayViewElement);
    }

    function updateCalendarView() {
        const selectedView = viewSelect.value;
        const currentYear = parseInt(yearSelect.value);
        const currentMonth = parseInt(monthSelect.value);
        const today = new Date();
        const currentDay = today.getDate();

        yearSelect.style.display = 'inline-block';
        monthSelect.style.display = 'inline-block';

        if (selectedView === 'month') {
            generateMonthView(currentYear, currentMonth);
        } else if (selectedView === 'week') {
            generateWeekView();
            yearSelect.style.display = 'none';
            monthSelect.style.display = 'none';
        } else if (selectedView === 'year') {
            generateYearView();
            yearSelect.style.display = 'none';
            monthSelect.style.display = 'none';
        } else if (selectedView === 'day') {
            generateDayView(currentYear, currentMonth, currentDay);
        }
        fetchAndRenderEvents();
    }

    function fetchAndRenderEvents() {
        fetch('/api/events')
            .then(response => response.json())
            .then(events => {
                eventListContainer.innerHTML = '<h2>Próximos Eventos:</h2>';
                if (events && events.length > 0) {
                    const ul = document.createElement('ul');
                    events.forEach(event => {
                        const li = document.createElement('li');
                        const formattedDate = new Date(event.date).toLocaleDateString();
                        li.textContent = `${formattedDate} - ${event.title}: ${event.description || 'Sin descripción'}`;
                        ul.appendChild(li);
                    });
                    eventListContainer.appendChild(ul);
                } else {
                    const p = document.createElement('p');
                    p.textContent = 'No hay eventos guardados.';
                    eventListContainer.appendChild(p);
                }
            })
            .catch(error => {
                console.error('Error al obtener los eventos:', error);
                const p = document.createElement('p');
                p.textContent = 'Error al cargar los eventos.';
                eventListContainer.appendChild(p);
            });
    }

    populateYearSelect();
    const initialYear = parseInt(yearSelect.value);
    const initialMonth = parseInt(monthSelect.value);
    generateMonthView(initialYear, initialMonth);
    fetchAndRenderEvents();

    viewSelect.addEventListener('change', updateCalendarView);

    yearSelect.addEventListener('change', function() {
        const selectedView = viewSelect.value;
        if (selectedView === 'month' || selectedView === 'day') {
            updateCalendarView();
        }
    });

    monthSelect.addEventListener('change', function() {
        const selectedView = viewSelect.value;
        if (selectedView === 'month' || selectedView === 'day') {
            updateCalendarView();
        }
    });

    addButton.addEventListener('click', function() {
        modal.style.display = 'block';
    });

    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    const eventForm = document.getElementById('new-event-form');
    eventForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const date = document.getElementById('event-date').value;
        const title = document.getElementById('event-title').value;
        const description = document.getElementById('event-description').value;

        const eventData = {
            date: date,
            title: title,
            description: description
        };

        fetch('/api/events', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(eventData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error al guardar el evento:', data.error);
                alert('Hubo un error al guardar el evento.');
            } else {
                console.log('Evento guardado:', data);
                alert('Evento guardado exitosamente.');
                modal.style.display = 'none';
                eventForm.reset();
                fetchAndRenderEvents();
            }
        })
        .catch(error => {
            console.error('Error de red:', error);
            alert('Error de red al intentar guardar el evento.');
        });
    });
});