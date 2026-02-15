document.addEventListener('DOMContentLoaded', async function() {
    
    const userResponse = await fetch('/api/current-user');
    const user = await userResponse.json();
    const username = user.username;

    const response = await fetch(`/api/forgetting-curves/${username}`);
    const lessons = await response.json();

    // Generate distinct colors dynamically based on number of lessons
    const generateColors = (count) => {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const hue = (i * 360 / count) % 360;
            const saturation = 70 + (i % 3) * 10; // Vary saturation
            const lightness = 45 + (i % 2) * 10; // Vary lightness
            colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
        }
        return colors;
    };
    
    const colors = generateColors(lessons.length);
    const datasets = lessons.map((lesson, index) => {
        return {
            label: lesson.name,
            data: lesson.curve,
            borderColor: colors[index % colors.length],
            borderWidth: 2,
            tension: 0.4,
            pointRadius: 0,
            fill: false
        };
    });

    const ctx = document.getElementById('forgettingChart').getContext('2d');

    new Chart(ctx, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            // parsing: false,
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Days Since Last Study'
                    }
                },
                y: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Retention (%)'
                    }
                }
            }
        }
    });
});
