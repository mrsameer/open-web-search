document.addEventListener('DOMContentLoaded', () => {
    // Setup Autocomplete for all search inputs
    const searchInputs = document.querySelectorAll('input[name="query"]');
    searchInputs.forEach(input => {
        setupAutocomplete(input);
    });

    // If on results page, fetch extra data
    if (window.location.pathname === '/search') {
        const query = new URLSearchParams(window.location.search).get('query') || document.querySelector('input[name="query"]').value;
        if (query) {
            fetchInstantAnswer(query);
            fetchImages(query);
            fetchRelatedTopics(query);
        }
    }
});

function setupAutocomplete(input) {
    let currentFocus;
    const container = document.createElement('div');
    container.setAttribute('class', 'autocomplete-items');
    input.parentNode.appendChild(container); // Append to input-group

    input.addEventListener('input', async function (e) {
        const val = this.value;
        closeAllLists();
        if (!val) return false;
        currentFocus = -1;

        try {
            const response = await fetch(`/api/autocomplete?query=${encodeURIComponent(val)}`);
            const data = await response.json();
            const suggestions = data.suggestions || [];

            suggestions.forEach(item => {
                const b = document.createElement('div');
                b.innerHTML = `<strong>${item.phrase.substr(0, val.length)}</strong>${item.phrase.substr(val.length)}`;
                b.innerHTML += `<input type='hidden' value='${item.phrase}'>`;
                b.addEventListener('click', function (e) {
                    input.value = this.getElementsByTagName('input')[0].value;
                    closeAllLists();
                    input.form.submit();
                });
                container.appendChild(b);
            });
            if (suggestions.length > 0) container.style.display = 'block';
        } catch (err) {
            console.error('Error fetching suggestions:', err);
        }
    });

    input.addEventListener('keydown', function (e) {
        let x = container.getElementsByTagName('div');
        if (e.keyCode == 40) { // DOWN
            currentFocus++;
            addActive(x);
        } else if (e.keyCode == 38) { // UP
            currentFocus--;
            addActive(x);
        } else if (e.keyCode == 13) { // ENTER
            e.preventDefault();
            if (currentFocus > -1) {
                if (x) x[currentFocus].click();
            } else {
                // If no suggestion selected, submit form normally
                input.form.submit();
            }
        }
    });

    function addActive(x) {
        if (!x) return false;
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        x[currentFocus].classList.add('autocomplete-active');
    }

    function removeActive(x) {
        for (let i = 0; i < x.length; i++) {
            x[i].classList.remove('autocomplete-active');
        }
    }

    function closeAllLists(elmnt) {
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        container.style.display = 'none';
    }

    document.addEventListener('click', function (e) {
        closeAllLists(e.target);
    });
}

async function fetchInstantAnswer(query) {
    const container = document.getElementById('instant-answer-container');
    if (!container) return;

    try {
        const response = await fetch(`/api/instant-answer?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        if (data.answer && data.answer !== "No instant answer available.") {
            container.innerHTML = `
                <div class="instant-answer-card">
                    <h3>Instant Answer</h3>
                    <p>${data.answer}</p>
                </div>
            `;
            container.style.display = 'block';
        }
    } catch (err) {
        console.error('Error fetching instant answer:', err);
    }
}

async function fetchImages(query) {
    const container = document.getElementById('images-container');
    if (!container) return;

    try {
        const response = await fetch(`/api/images?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        if (data.images && data.images.length > 0) {
            let html = '<div class="images-grid">';
            data.images.slice(0, 8).forEach(img => {
                html += `
                    <a href="${img.image}" target="_blank" class="image-item">
                        <img src="${img.thumbnail}" alt="${img.title}" title="${img.title}">
                    </a>
                `;
            });
            html += '</div>';
            container.innerHTML = `<h3>Images</h3>${html}`;
            container.style.display = 'block';
        }
    } catch (err) {
        console.error('Error fetching images:', err);
    }
}

async function fetchRelatedTopics(query) {
    const container = document.getElementById('related-topics-container');
    if (!container) return;

    try {
        const response = await fetch(`/api/related-topics?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        if (data.topics && data.topics.length > 0) {
            let html = '<ul class="related-topics-list">';
            data.topics.slice(0, 5).forEach(topic => {
                if (topic.Text) {
                    html += `<li><a href="${topic.FirstURL}" target="_blank">${topic.Text}</a></li>`;
                }
            });
            html += '</ul>';
            container.innerHTML = `<h3>Related Topics</h3>${html}`;
            container.style.display = 'block';
        }
    } catch (err) {
        console.error('Error fetching related topics:', err);
    }
}
