document.addEventListener('DOMContentLoaded', function() {
    const viewSelect = document.getElementById('view-select');
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const calendarDiv = document.getElementById('calendar');
    const addButton = document.getElementById('add-event-btn');
    const modal = document.getElementById('event-modal');
    const closeBtn = modal.querySelector('.close-btn');
    const eventDateInput = document.getElementById('event-date');
    const eventTitleInput = document.getElementById('event-title');
    const eventDescriptionInput = document.getElementById('event-description');
    const saveEventBtn = modal.querySelector('.save-event-btn');
    const eventForm = document.getElementById('new-event-form');
    const eventListContainer = document.createElement('div');
    eventListContainer.id = 'event-list-container';
    calendarDiv.parentNode.insertBefore(eventListContainer, calendarDiv.nextSibling);

    const eventsModal = document.createElement('div');
    eventsModal.id = 'events-of-day-modal';
    eventsModal.className = 'modal';
    eventsModal.innerHTML = `
        <div class="modal-content">
            <span class="close-btn">&times;</span>
            <h3>Eventos del día <span id="selected-date-display"></span></h3>
            <ul id="events-list-of-day"></ul>
        </div>
    `;
    document.body.appendChild(eventsModal);
    const eventsModalElement = document.getElementById('events-of-day-modal');
    const closeEventsModalBtn = eventsModalElement.querySelector('.close-btn');
    const eventsListOfDay = document.getElementById('events-list-of-day');
    const selectedDateDisplay = document.getElementById('selected-date-display');

    const prevMonthBtn = document.getElementById('prev-month-btn');
    const nextMonthBtn = document.getElementById('next-month-btn');
    const currentMonthYearSpan = document.getElementById('current-month-year');

    let currentEditingEventId = null;
    let cachedEvents = [];
    let currentYear = new Date().getFullYear();
    let currentMonth = new Date().getMonth() + 1;

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

    function updateMonthYearDisplay() {
        const date = new Date(currentYear, currentMonth - 1, 1);
        const monthName = new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric' }).format(date);
        currentMonthYearSpan.textContent = monthName;
    }

    function generateMiniCalendar(year, month, events) {
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
            const date = new Date(year, month - 1, day);
            const formattedDate = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
            const dayEvents = events.filter(event => event.date === formattedDate);
            const hasEvent = dayEvents.length > 0;
            const eventIndicator = hasEvent ? `<span class="event-indicator">${dayEvents.length}</span>` : '';
            let dayStyle = '';
            // Verificar si es domingo (getDay() === 0)
            if (date.getDay() === 0) {
                dayStyle = 'style="background-color: rgba(255, 204, 204, 0.5);"';
            }
            calendarHTML += `<div data-day="${day}" data-month="${month}" data-year="${year}" ${dayStyle}>${day}${eventIndicator}</div>`;
        }

        calendarHTML += '</div></div>';
        return calendarHTML;
    }

    function generateYearView(events) {
        calendarDiv.innerHTML = '';
        const currentYear = parseInt(yearSelect.value);

        for (let month = 1; month <= 12; month++) {
            calendarDiv.innerHTML += generateMiniCalendar(currentYear, month, events);
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
                const eventsOnDay = cachedEvents.filter(event => event.date === formattedDate);
                selectedDateDisplay.textContent = formattedDate;
                eventsListOfDay.innerHTML = '';
                if (eventsOnDay.length > 0) {
                    const ul = document.createElement('ul');
                    eventsOnDay.forEach(event => {
                        const li = document.createElement('li');
                        li.textContent = `${event.title}: ${event.description || 'Sin descripción'}`;
                        ul.appendChild(li);
                    });
                    eventsListOfDay.appendChild(ul);
                } else {
                    eventsListOfDay.textContent = 'No hay eventos para este día.';
                }
                eventsModalElement.style.display = 'block';
            });
        });
    }

    function generateMonthView(year, month, events) {
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
            const date = new Date(year, month - 1, day);
            const dayCell = document.createElement('div');
            dayCell.classList.add('day');
            dayCell.textContent = day;
            dayCell.dataset.day = day;
            dayCell.dataset.month = month;
            dayCell.dataset.year = year;

            // Verificar si es domingo (getDay() === 0)
            if (date.getDay() === 0) {
                dayCell.style.backgroundColor = 'rgba(255, 204, 204, 0.5)'; // Rojo pastel con transparencia
            }

            const formattedDate = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
            const dayEvents = events.filter(event => event.date === formattedDate);
            if (dayEvents.length > 0) {
                const eventIndicator = document.createElement('span');
                eventIndicator.classList.add('event-indicator');
                eventIndicator.textContent = dayEvents.length;
                dayCell.appendChild(eventIndicator);
            }
            calendarDiv.appendChild(dayCell);

            dayCell.addEventListener('click', function() {
                const selectedDay = this.dataset.day;
                const selectedMonth = this.dataset.month;
                const selectedYear = this.dataset.year;
                const formattedDate = `${selectedYear}-${selectedMonth.padStart(2, '0')}-${selectedDay.padStart(2, '0')}`;
                const eventsOnDay = cachedEvents.filter(event => event.date === formattedDate);
                selectedDateDisplay.textContent = formattedDate;
                eventsListOfDay.innerHTML = '';
                if (eventsOnDay.length > 0) {
                    const ul = document.createElement('ul');
                    eventsOnDay.forEach(event => {
                        const li = document.createElement('li');
                        li.textContent = `${event.title}: ${event.description || 'Sin descripción'}`;
                        ul.appendChild(li);
                    });
                    eventsListOfDay.appendChild(ul);
                } else {
                    eventsListOfDay.textContent = 'No hay eventos para este día.';
                }
                eventsModalElement.style.display = 'block';
            });
        }
    }
    function generateWeekView(events) {
        calendarDiv.innerHTML = '';
        calendarDiv.classList.remove('year-view', 'month-view', 'day-view');

        const today = new Date();
        const currentDayOfWeek = today.getDay();
        const diff = today.getDate() - currentDayOfWeek + (currentDayOfWeek === 0 ? -6 : 1);

        for (let i = 0; i < 7; i++) {
            const day = new Date(today.setDate(diff + i));
            const dayOfWeek = new Intl.DateTimeFormat('es-ES', { weekday: 'short' }).format(day);
            const dayOfMonth = day.getDate();
            const year = day.getFullYear();
            const month = day.getMonth() + 1;
            const date = `${year}-${month.toString().padStart(2, '0')}-${dayOfMonth.toString().padStart(2, '0')}`;
            const dayEvents = events.filter(event => event.date === date);
            const eventIndicator = dayEvents.length > 0 ? `<span class="event-indicator">${dayEvents.length}</span>` : '';

            const dayCell = document.createElement('div');
            dayCell.classList.add('day');
            dayCell.innerHTML = `<strong>${dayOfWeek}</strong><br>${dayOfMonth}${eventIndicator}`;
            dayCell.dataset.day = dayOfMonth;
            dayCell.dataset.month = month;
            dayCell.dataset.year = year;

            // Verificar si es domingo (getDay() === 0)
            if (day.getDay() === 0) {
                dayCell.style.backgroundColor = 'rgba(255, 204, 204, 0.5)'; // Rojo pastel con transparencia
            }

            calendarDiv.appendChild(dayCell);

            dayCell.addEventListener('click', function() {
                const selectedDay = this.dataset.day;
                const selectedMonth = this.dataset.month;
                const selectedYear = this.dataset.year;
                const formattedDate = `${selectedYear}-${selectedMonth.padStart(2, '0')}-${selectedDay.padStart(2, '0')}`;
                const eventsOnDay = cachedEvents.filter(event => event.date === formattedDate);
                selectedDateDisplay.textContent = formattedDate;
                eventsListOfDay.innerHTML = '';
                if (eventsOnDay.length > 0) {
                    const ul = document.createElement('ul');
                    eventsOnDay.forEach(event => {
                        const li = document.createElement('li');
                        li.textContent = `${event.title}: ${event.description || 'Sin descripción'}`;
                        ul.appendChild(li);
                    });
                    eventsListOfDay.appendChild(ul);
                } else {
                    eventsListOfDay.textContent = 'No hay eventos para este día.';
                }
                eventsModalElement.style.display = 'block';
            });
        }
        today.setDate(today.getDate() - 7); // Restaurar la fecha actual para no afectar otras partes
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

        const eventsOnDay = cachedEvents.filter(event => event.date === `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`);
        if (eventsOnDay.length > 0) {
            const eventsList = document.createElement('ul');
            eventsList.innerHTML = '<h3>Eventos del día:</h3>';
            eventsOnDay.forEach(event => {
                const listItem = document.createElement('li');
                listItem.textContent = `${event.title}: ${event.description || 'Sin descripción'}`;
                eventsList.appendChild(listItem);
            });
            calendarDiv.appendChild(eventsList);
        } else {
            const noEventsMessage = document.createElement('p');
            noEventsMessage.textContent = 'No hay eventos para este día.';
            calendarDiv.appendChild(noEventsMessage);
        }
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
            generateMonthView(currentYear, currentMonth, cachedEvents);
        } else if (selectedView === 'week') {
            generateWeekView(cachedEvents);
            yearSelect.style.display = 'none';
            monthSelect.style.display = 'none';
        } else if (selectedView === 'year') {
            generateYearView(cachedEvents);
            yearSelect.style.display = 'none';
            monthSelect.style.display = 'none';
        } else if (selectedView === 'day') {
            generateDayView(currentYear, currentMonth, currentDay);
        }
    }

    function fetchAndRenderEvents() {
        fetch('/api/events')
            .then(response => response.json())
            .then(events => {
                cachedEvents = events;
                eventListContainer.innerHTML = '<h2 class="mt-3">Próximos Eventos:</h2>'; // Añadimos margen superior

                if (events && events.length > 0) {
                    const ul = document.createElement('ul');
                    ul.classList.add('list-group'); // Clase para un listado básico de Bootstrap

                    events.forEach(event => {
                        const formattedDate = new Date(event.date).toLocaleDateString();
                        const li = document.createElement('li');
                        li.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center'); // Elemento de lista con flexbox para alinear contenido

                        const eventInfo = document.createElement('div');
                        eventInfo.innerHTML = `<span class="font-weight-bold">${formattedDate}</span> - ${event.title}: ${event.description || 'Sin descripción'}`;
                        li.appendChild(eventInfo);

                        const actions = document.createElement('div');
                        actions.classList.add('btn-group', 'btn-group-sm'); // Grupo de botones pequeños

                        const deleteButton = document.createElement('button');
                        deleteButton.textContent = 'Borrar';
                        deleteButton.classList.add('btn', 'btn-danger');
                        deleteButton.dataset.id = event.id;
                        deleteButton.addEventListener('click', function() {
                            const eventIdToDelete = this.dataset.id;
                            if (confirm(`¿Seguro que quieres borrar el evento "${event.title}"?`)) {
                                fetch(`/api/events/${eventIdToDelete}`, {
                                    method: 'DELETE'
                                })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.message) {
                                            alert(data.message);
                                            fetchAndRenderEvents();
                                        } else if (data.error) {
                                            alert(data.error);
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error al borrar el evento:', error);
                                        alert('Error al intentar borrar el evento.');
                                    });
                            }
                        });

                        const editButton = document.createElement('button');
                        editButton.textContent = 'Editar';
                        editButton.classList.add('btn', 'btn-secondary', 'ml-2'); // Añadimos margen izquierdo
                        editButton.dataset.id = event.id;
                        editButton.addEventListener('click', function() {
                            const eventIdToEdit = this.dataset.id;
                            currentEditingEventId = eventIdToEdit;
                            fetch(`/api/events/${eventIdToEdit}`)
                                .then(response => response.json())
                                .then(eventData => {
                                    eventDateInput.value = eventData.date;
                                    eventTitleInput.value = eventData.title;
                                    eventDescriptionInput.value = eventData.description || '';
                                    modal.style.display = 'block';
                                })
                                .catch(error => {
                                    console.error('Error al obtener el evento para editar:', error);
                                    alert('Error al cargar los detalles del evento para editar.');
                                });
                        });

                        actions.appendChild(deleteButton);
                        actions.appendChild(editButton);
                        li.appendChild(actions);
                        ul.appendChild(li);
                    });
                    eventListContainer.appendChild(ul);
                } else {
                    const p = document.createElement('p');
                    p.classList.add('mt-2'); // Añadimos margen superior
                    p.textContent = 'No hay eventos guardados.';
                    eventListContainer.appendChild(p);
                }
                updateCalendarView();
            })
            .catch(error => {
                console.error('Error al obtener los eventos:', error);
                const p = document.createElement('p');
                p.classList.add('mt-2', 'text-danger'); // Añadimos margen superior y color de texto rojo
                p.textContent = 'Error al cargar los eventos.';
                eventListContainer.appendChild(p);
                updateCalendarView();
            });
    }

    populateYearSelect();
    updateMonthYearDisplay(); // Llamamos a la función para mostrar el mes y el año actual
    const initialYear = parseInt(yearSelect.value);
    const initialMonth = parseInt(monthSelect.value);
    generateMonthView(initialYear, initialMonth, cachedEvents);
    fetchAndRenderEvents();

    viewSelect.addEventListener('change', updateCalendarView);

    yearSelect.addEventListener('change', function() {
        const selectedView = viewSelect.value;
        if (selectedView === 'month' || selectedView === 'year') {
            updateCalendarView();
        }
    });

    monthSelect.addEventListener('change', function() {
        const selectedView = viewSelect.value;
        if (selectedView === 'month') {
            updateCalendarView();
        }
    });

    prevMonthBtn.addEventListener('click', function() {
        currentMonth--;
        if (currentMonth < 1) {
            currentMonth = 12;
            currentYear--;
        }
        updateMonthYearDisplay();
        generateMonthView(currentYear, currentMonth, cachedEvents);
    });

    nextMonthBtn.addEventListener('click', function() {
        currentMonth++;
        if (currentMonth > 12) {
            currentMonth = 1;
            currentYear++;
        }
        updateMonthYearDisplay();
        generateMonthView(currentYear, currentMonth, cachedEvents);
    });

    addButton.addEventListener('click', function() {
        modal.style.display = 'block';
        currentEditingEventId = null;
        eventForm.reset();
    });

    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
        currentEditingEventId = null;
        eventForm.reset();
    });

    closeEventsModalBtn.addEventListener('click', function() {
        eventsModalElement.style.display = 'none';
    });

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
            currentEditingEventId = null;
            eventForm.reset();
        }
        if (event.target === eventsModalElement) {
            eventsModalElement.style.display = 'none';
        }
    });

    eventForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const date = eventDateInput.value;
        const title = eventTitleInput.value;
        const description = eventDescriptionInput.value;

        const eventData = {
            date: date,
            title: title,
            description: description
        };

        const method = currentEditingEventId ? 'PUT' : 'POST';
        const url = currentEditingEventId ? `/api/events/${currentEditingEventId}` : '/api/events';

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(eventData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error(`Error al ${method === 'PUT' ? 'editar' : 'guardar'} el evento:`, data.error);
                    alert(`Hubo un error al ${method === 'PUT' ? 'editar' : 'guardar'} el evento.`);
                } else {
                    console.log(`Evento ${method === 'PUT' ? 'editado' : 'guardado'}:`, data);
                    alert(`Evento ${method === 'PUT' ? 'editado' : 'guardado'} exitosamente.`);
                    modal.style.display = 'none';
                    eventForm.reset();
                    fetchAndRenderEvents();
                    currentEditingEventId = null;
                }
            })
            .catch(error => {
                console.error(`Error de red al intentar ${method === 'PUT' ? 'editar' : 'guardar'} el evento:`, error);
                alert(`Error de red al intentar ${method === 'PUT' ? 'editar' : 'guardar'} el evento.`);
            });
    });
});
