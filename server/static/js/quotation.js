// Funciones para la página de cotizaciones

let quotationItems = {};
let selectedClient = null;
const ITBIS_RATE = 0.18;

// Funciones principales (deben estar disponibles globalmente o definidas en HTML)

// Guardar Cotización
function initSaveQuotation() {
    const saveBtn = document.getElementById('save-quotation-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            if (Object.keys(quotationItems).length === 0) {
                alert('No hay productos en la cotización para guardar.');
                return;
            }

            const response = await fetch('/api/quotation/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items: Object.values(quotationItems),
                    client_id: selectedClient ? selectedClient.id : null
                })
            });

            const result = await response.json();
            if (result.success) {
                alert(result.message);
                // Limpiar cotización
                clearQuotation();
            } else {
                alert(`Error: ${result.error}`);
            }
        });
    }
}

// Cargar y mostrar cotizaciones guardadas
function initLoadSavedQuotations() {
    const modal = document.getElementById('savedQuotationsModal');
    if (modal) {
        modal.addEventListener('show.bs.modal', loadSavedQuotations);
    }

    // Función para generar PDF desde guardadas
    window.generatePdfFromSaved = function(quotationId) {
        window.open(`/api/quotation/generate_pdf/${quotationId}`, '_blank');
    }
}

async function loadSavedQuotations() {
    try {
        const response = await fetch('/api/quotations');
        const quotations = await response.json();
        const tbody = document.getElementById('saved-quotations-tbody');
        if (tbody) {
            tbody.innerHTML = '';
            quotations.forEach(q => {
                const row = document.createElement('tr');
                const fecha = new Date(q.fecha).toLocaleDateString();
                row.innerHTML = `
                    <td>${q._id}</td>
                    <td>${q.cliente}</td>
                    <td>${fecha}</td>
                    <td>RD$ ${q.total.toFixed(2)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="generatePdfFromSaved('${q._id}')"><i class="bi bi-file-earmark-pdf"></i> PDF</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading quotations:', error);
    }
}

// Limpiar cotización
window.clearQuotation = function() {
    quotationItems = {};
    selectedClient = null;
    if (typeof updateUI === 'function') {
        updateUI();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    console.log('Quotation JS loaded');
    initSaveQuotation();
    initLoadSavedQuotations();
});
