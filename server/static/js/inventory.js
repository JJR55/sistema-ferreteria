// Funciones para la página de inventario

// Nueva funcionalidad: Importar CSV
function initImportCSV() {
    const importBtn = document.getElementById('import-btn');
    if (importBtn) {
        importBtn.addEventListener('click', async () => {
            const fileInput = document.getElementById('csv-file');
            const file = fileInput.files[0];
            if (!file) {
                alert('Por favor seleccione un archivo CSV.');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            const importBtn = document.getElementById('import-btn');
            const progressDiv = document.getElementById('import-progress');
            const progressBar = progressDiv.querySelector('.progress-bar');

            importBtn.disabled = true;
            importBtn.textContent = 'Importando...';
            progressDiv.classList.remove('d-none');
            progressBar.style.width = '0%';

            try {
                const response = await fetch('/api/products/import/csv', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                if (result.success) {
                    alert(result.message);
                    // Cerrar modal
                    bootstrap.Modal.getInstance(document.getElementById('importModal')).hide();
                    fetchInventory();
                } else {
                    alert(`Error: ${result.error}`);
                }
            } catch (error) {
                alert('Ocurrió un error de red.');
                console.error(error);
            } finally {
                importBtn.disabled = false;
                importBtn.textContent = 'Importar';
                progressDiv.classList.add('d-none');
            }
        });
    }
}

// Nueva funcionalidad: Exportar CSV
function initExportCSV() {
    const exportCsvBtn = document.getElementById('export-csv-btn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            window.open('/api/products/export/csv', '_blank');
        });
    }
}

// Nueva funcionalidad: Exportar PDF
function initExportPDF() {
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            window.open('/api/products/export/pdf', '_blank');
        });
    }
}

// Nueva funcionalidad: Reporte Stock Bajo
function initLowStockReport() {
    const lowStockBtn = document.getElementById('low-stock-btn');
    if (lowStockBtn) {
        lowStockBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/api/reports/low_stock');
                const result = await response.json();

                if (result.success && result.products.length > 0) {
                    let message = 'Productos con stock bajo:\n\n';
                    result.products.forEach(p => {
                        message += `${p.nombre} (Código: ${p.codigo_barras}) - Stock: ${p.stock}\n`;
                    });
                    alert(message);
                } else {
                    alert('No hay productos con stock bajo.');
                }
            } catch (error) {
                alert('Ocurrió un error de red.');
                console.error(error);
            }
        });
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    console.log('Inventory JS loaded');
    initImportCSV();
    initExportCSV();
    initExportPDF();
    initLowStockReport();
});

// Función global para recargar inventario (debe estar definida en el HTML)
if (typeof fetchInventory === 'undefined') {
    async function fetchInventory() {
        const response = await fetch('/api/products');
        allProducts = await response.json();
        renderInventoryTable(allProducts);
    }
}
