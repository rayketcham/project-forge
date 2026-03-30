async function apiAction(url, method = 'POST') {
    try {
        const response = await fetch(url, { method });
        if (!response.ok) {
            const data = await response.json();
            alert(data.detail || 'Action failed');
            return null;
        }
        return await response.json();
    } catch (err) {
        alert('Request failed: ' + err.message);
        return null;
    }
}

async function approveIdea(id) {
    const result = await apiAction('/ideas/' + id + '/approve');
    if (result) location.reload();
}

async function rejectIdea(id) {
    const result = await apiAction('/ideas/' + id + '/reject');
    if (result) location.reload();
}

async function scaffoldIdea(id) {
    const result = await apiAction('/ideas/' + id + '/scaffold');
    if (result) location.reload();
}

// Auto-refresh stats every 60 seconds on dashboard
if (window.location.pathname === '/') {
    setInterval(async () => {
        try {
            const resp = await fetch('/api/stats');
            if (resp.ok) {
                const stats = await resp.json();
                const numbers = document.querySelectorAll('.stat-number');
                if (numbers.length >= 6) {
                    numbers[0].textContent = stats.total_ideas;
                    numbers[1].textContent = stats.ideas_by_status.new || 0;
                    numbers[2].textContent = stats.ideas_by_status.approved || 0;
                    numbers[3].textContent = stats.ideas_by_status.scaffolded || 0;
                    numbers[4].textContent = stats.avg_feasibility_score;
                    numbers[5].textContent = stats.total_runs;
                }
            }
        } catch (e) { /* silently ignore refresh errors */ }
    }, 60000);
}
