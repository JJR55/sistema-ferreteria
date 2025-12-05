document.addEventListener('DOMContentLoaded', function() {
    const historyTab = document.getElementById('history-tab');
    const historyTableBody = document.getElementById('quotations-history-table');
    const emptyStateDiv = document.getElementById('history-empty-state');

    if (historyTab) {
        historyTab.addEventListener('shown.bs.tab', function() {
            loadQuotationsHistory();
        });
    }

    async function loadQuotationsHistory() {
        try {
            const response = await fetch('/api/quotations');
            const quotations = await response.json();

            historyTableBody.innerHTML = ''; // Limpiar tabla

            if (quotations.length === 0) {
                emptyStateDiv.style.display = 'block';
            } else {
                emptyStateDiv.style.display = 'none';
                quotations.forEach(q => {
                    const isExpired = new Date(q.fecha_expiracion) < new Date();
                    const statusBadge = isExpired
                        ? `<span class="badge bg-danger">Expirada</span>`
                        : `<span class="badge bg-success">Vigente</span>`;

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${q._id}</td>
                        <td>${q.cliente || 'Consumidor Final'}</td>
                        <td>${new Date(q.fecha).toLocaleDateString()}</td>
                        <td>RD$ ${q.total.toFixed(2)}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <a href="/api/quotation/generate_pdf/${q._id}" target="_blank" class="btn btn-sm btn-outline-primary" title="Ver/Imprimir PDF">
                                <i class="bi bi-printer"></i>
                            </a>
                        </td>
                    `;
                    historyTableBody.appendChild(row);
                });
            }
        } catch (error) {
            console.error('Error al cargar el historial de cotizaciones:', error);
            historyTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error al cargar el historial.</td></tr>';
            emptyStateDiv.style.display = 'none';
        }
    }

    // Cargar historial si la pestaña de historial está activa por defecto (en caso de recarga)
    if (document.querySelector('#history-tab.active')) {
        loadQuotationsHistory();
    }
});