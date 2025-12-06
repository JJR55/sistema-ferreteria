document.addEventListener('DOMContentLoaded', function() {
    const imageUploadInput = document.getElementById('invoice-image-upload');
    const processImageBtn = document.getElementById('process-image-btn');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const addToInventoryBtn = document.getElementById('add-to-inventory-btn');

    const initialStateDiv = document.getElementById('initial-state');
    const loadingStateDiv = document.getElementById('loading-state');
    const resultsTableContainer = document.getElementById('results-table-container');
    const resultsTableBody = document.getElementById('results-table-body');

    const toastElement = document.getElementById('toast-element');
    const toastMessage = document.getElementById('toast-message');
    const bsToast = new bootstrap.Toast(toastElement);

    let uploadedFile = null;

    function showToast(message, isError = false) {
        toastMessage.textContent = message;
        toastElement.className = `toast align-items-center text-white border-0 ${isError ? 'bg-danger' : 'bg-success'}`;
        bsToast.show();
    }

    imageUploadInput.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (file) {
            uploadedFile = file;
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                imagePreviewContainer.style.display = 'block';
            }
            reader.readAsDataURL(file);
            processImageBtn.disabled = false;
        }
    });

    processImageBtn.addEventListener('click', async function() {
        if (!uploadedFile) {
            showToast('Por favor, selecciona una imagen primero.', true);
            return;
        }

        initialStateDiv.style.display = 'none';
        resultsTableContainer.style.display = 'none';
        loadingStateDiv.style.display = 'block';
        processImageBtn.disabled = true;
        addToInventoryBtn.style.display = 'none';

        const formData = new FormData();
        formData.append('invoice_image', uploadedFile);

        try {
            const response = await fetch('/api/scan_invoice_image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                renderResults(result.items);
                showToast(`Se extrajeron ${result.items.length} posibles productos.`);
            } else {
                showToast(result.error, true);
                initialStateDiv.style.display = 'block';
            }
        } catch (error) {
            showToast('Error de red al procesar la imagen.', true);
            initialStateDiv.style.display = 'block';
        } finally {
            loadingStateDiv.style.display = 'none';
            processImageBtn.disabled = false;
        }
    });

    function renderResults(items) {
        resultsTableBody.innerHTML = '';
        if (items.length === 0) {
            initialStateDiv.style.display = 'block';
            showToast('No se pudieron identificar productos en la factura.', true);
            return;
        }

        items.forEach((item, index) => {
            const row = document.createElement('tr');
            row.dataset.index = index;
            row.innerHTML = `
                <td><input type="text" class="form-control form-control-sm" value="${item.nombre || ''}" data-field="nombre"></td>
                <td><input type="number" class="form-control form-control-sm" value="${item.cantidad || 1}" data-field="cantidad" min="0" step="any"></td>
                <td><input type="number" class="form-control form-control-sm" value="${item.costo || 0}" data-field="costo" min="0" step="0.01"></td>
                <td><input type="number" class="form-control form-control-sm" placeholder="0.00" data-field="precio" min="0" step="0.01" required></td>
                <td><button class="btn btn-sm btn-outline-danger remove-item-btn"><i class="bi bi-trash"></i></button></td>
            `;
            resultsTableBody.appendChild(row);
        });

        resultsTableContainer.style.display = 'block';
        addToInventoryBtn.style.display = 'block';
    }

    resultsTableBody.addEventListener('click', function(event) {
        if (event.target.closest('.remove-item-btn')) {
            event.target.closest('tr').remove();
        }
    });

    addToInventoryBtn.addEventListener('click', async function() {
        const productsToAdd = [];
        const rows = resultsTableBody.querySelectorAll('tr');
        let isValid = true;

        rows.forEach(row => {
            const nombre = row.querySelector('input[data-field="nombre"]').value.trim();
            const costo = parseFloat(row.querySelector('input[data-field="costo"]').value);
            const cantidad = parseFloat(row.querySelector('input[data-field="cantidad"]').value);
            const precio = parseFloat(row.querySelector('input[data-field="precio"]').value);

            if (!nombre || isNaN(precio) || precio <= 0) {
                isValid = false;
                row.querySelector('input[data-field="precio"]').classList.add('is-invalid');
                row.querySelector('input[data-field="nombre"]').classList.add('is-invalid');
            } else {
                row.querySelector('input[data-field="precio"]').classList.remove('is-invalid');
                row.querySelector('input[data-field="nombre"]').classList.remove('is-invalid');
                productsToAdd.push({
                    nombre: nombre,
                    costo: isNaN(costo) ? 0 : costo,
                    precio: precio,
                    stock: isNaN(cantidad) ? 1 : cantidad,
                    stock_minimo: 1,
                    departamento: 'Importado Factura'
                });
            }
        });

        if (!isValid) {
            showToast('Por favor, complete el nombre y precio de venta para todos los productos.', true);
            return;
        }

        if (productsToAdd.length === 0) {
            showToast('No hay productos para agregar.', true);
            return;
        }

        try {
            const response = await fetch('/api/products/bulk_add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ products: productsToAdd })
            });
            const result = await response.json();
            showToast(result.message, !result.success);
            if (result.success) {
                resultsTableBody.innerHTML = '';
                resultsTableContainer.style.display = 'none';
                initialStateDiv.style.display = 'block';
                addToInventoryBtn.style.display = 'none';
            }
        } catch (error) {
            showToast('Error de red al agregar los productos.', true);
        }
    });
});
