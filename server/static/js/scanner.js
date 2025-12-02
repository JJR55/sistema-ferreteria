document.addEventListener('DOMContentLoaded', function() {
    // --- ESTADO DE LA APLICACIÓN ---
    const scannedItems = {}; // { productId: {data, quantity} }
    let isScannerActive = false;
    let quaggaInitialized = false;

    // --- ELEMENTOS DEL DOM ---
    const loader = document.getElementById('loader');
    const searchInput = document.getElementById('search-input');
    const searchResultsDiv = document.getElementById('search-results');
    const productListDiv = document.getElementById('product-list');
    const confirmStockBtn = document.getElementById('confirm-stock');
    const interactiveDiv = document.getElementById('interactive');
    const scannerStatus = document.getElementById('scanner-status');
    const productsCount = document.getElementById('products-count');
    const cameraOverlay = document.getElementById('camera-overlay');
    const activateCameraBtn = document.getElementById('activate-camera-btn');

    // --- SONIDOS (Feedback Auditivo) ---
    // Beep de éxito - tono más audible y profesional
    const successSound = new Audio();
    successSound.src = "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PrqJI/ME6T6ty+hSwTKYDf7bOFYBtGhOSfjGRBQkpMqejlmpVkXFhHo9bKoJcJaVpGpqOgm2lYXVBMn+bGmWpGRFlEfqlFh2xhVUVXquLHlpxdZVlGkaLRl5NjXEpBE6tNnWVhVUpPWubs6JqEYjxIoe7s6Z+AbjtGmejbhWZeT1RFldPcnKKHbDpGoOHYkGJeRlVFVdHWoGODejpGn+rWkWNgUkxRW9rY5KWHcDpEneDPjGRhXVNMjGLGlWJjRE9HY9uBfotxeDpC6+7jnJ1wQkhRXNrKoZiFXFw/nujgmp9lX1hFpdXNpZiHX22BrebjlGRhXF9GV9jJl5diX1pFWdzNmpuEfzqB0+vjnJ+EYEFAXd7JnJyFbTpBluLcnJxpRkdDUdzLmp6EdjqBjOLakkRhQkdDUdzLmp+EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyYZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCUd/KnZyFbDtBlEDcnpyQAAAA=";

    // Beep de error - tono descendente
    const errorSound = new Audio();
    errorSound.src = "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PrqJI/ME6T6ty+hSwTKYDf7bOFYBtGhOSfjGRBQkpMqejlmpVkXFhHo9bKoJcJaVpGpqOgm2lYXVBMn+bGmWpGRFlEfqlFh2xhVUVXquLHlpxdZVlGkaLRl5NjXEpBE6tNnWVhVUpPWubs6JqEYjxIoe7s6Z+AbjtGmejbhWZeT1RFldPcnKKHbDpGoOHYkGJeRlVFVdHWoGODejpGn+rWkWNgUkxRW9rY5KWHcDpEneDPjGRhXVNMjGLGlWJjRE9HY9uBfotxeDpC6+7jnJ1wQkhRXNrKoZiFXFw/nujgmp9lX1hFpdXNpZiHX22BrebjlGRhXF9GV9jJl5diX1pFWdzNmpuEfzqB0+vjnJ+EYEFAXd7JnJyFbTpBluLcnJxpRkdDUdzLmp6EdjqBjOLakkRhQkdDUdzLmp+EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyQZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyQZUdCUbr8npmEeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyQZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyQZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQEFCXd/KnZyFbDtBl+LcnpyQZUdCUdzLmp2EeTKAg+vjnJ+EYEFAUd7JnJyFbTpBl+LcnJxpRkdCUdzLmp6EdjqBjOPalyRhQ==";

    // --- FUNCIONES DE UI ---
    function showLoader(show) {
        loader.style.display = show ? 'flex' : 'none';
    }

    function showToast(message, isError = false) {
        toast.textContent = message;
        toast.className = "show " + (isError ? 'error' : 'success');
        toast.className = "show";
        setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
    }

    // --- LÓGICA DEL ESCÁNER (QUAGGA.JS) ---
    async function initScanner() {
        if (quaggaInitialized) return; // Evitar reinicializar si ya está listo

        // Primero solicitar permisos de cámara
        const hasPermissions = await requestCameraPermissions();
        if (!hasPermissions) {
            return; // No continuar si no hay permisos
        }

        updateScannerStatus('Inicializando escáner...', 'warning');

        Quagga.init({
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: interactiveDiv,
                constraints: {
                    width: { min: 640 },
                    height: { min: 480 },
                    facingMode: "environment" // Usa la cámara trasera del celular
                },
            },
            decoder: { readers: ["ean_reader", "code_128_reader", "upc_reader"] },
            locate: true,
            locator: { patchSize: "medium", halfSample: true },
            numOfWorkers: navigator.hardwareConcurrency || 4,
        }, function(err) {
            if (err) {
                console.error(err);
                updateScannerStatus('Error al iniciar escáner', 'danger');
                showToast("Error al iniciar escáner.", true);
                return;
            }
            console.log("Escáner inicializado correctamente.");
            quaggaInitialized = true;
            updateScannerStatus('Escáner listo', 'success');

            // Iniciar automáticamente después de 1 segundo
            setTimeout(() => {
                startScanner();
            }, 1000);
        });

        Quagga.onDetected(handleDetection);
        Quagga.onProcessed(frame => {
            const drawingCtx = Quagga.canvas.ctx.overlay;
            const drawingCanvas = Quagga.canvas.dom.overlay;
            drawingCtx.clearRect(0, 0, parseInt(drawingCanvas.getAttribute("width")), parseInt(drawingCanvas.getAttribute("height")));
            if (frame) {
                if (frame.boxes) {
                    frame.boxes.filter(box => box !== frame.box).forEach(box => {
                        Quagga.ImageDebug.drawPath(box, { x: 0, y: 1 }, drawingCtx, { color: "green", lineWidth: 2 });
                    });
                }
                if (frame.box) {
                    Quagga.ImageDebug.drawPath(frame.box, { x: 0, y: 1 }, drawingCtx, { color: "#00F", lineWidth: 2 });
                }
            }
        });
    }

    function startScanner() {
        if (quaggaInitialized && !isScannerActive) {
            Quagga.start();
            isScannerActive = true;
            interactiveDiv.style.display = 'block';
            interactiveDiv.classList.add('active'); // Agregar clase para estilos
            hideCameraOverlay(); // Ocultar overlay cuando la cámara inicia
            updateScannerStatus('Escáner activo - enfocando código', 'primary');
        }
    }

    function hideCameraOverlay() {
        if (cameraOverlay) {
            cameraOverlay.style.display = 'none';
        }
    }

    function showCameraOverlay() {
        if (cameraOverlay && !isScannerActive) {
            cameraOverlay.style.display = 'flex';
        }
    }

    function stopScanner() {
        if (isScannerActive) {
            Quagga.stop();
            isScannerActive = false;
            interactiveDiv.style.display = 'none';
            updateScannerStatus('Escáner pausado', 'warning');
        }
    }

    const handleDetection = (result) => {
        if (!isScannerActive) return; // Evitar detecciones mientras está pausado
        const code = result.codeResult.code;

        // Pausar temporalmente el escáner para evitar múltiples detecciones
        Quagga.stop();
        isScannerActive = false;
        updateScannerStatus('Código detectado - procesando...', 'info');

        handleBarcode(code);
    };

    // --- LÓGICA DE MANEJO DE DATOS ---
    async function handleBarcode(barcode) {
        showLoader(true);
        try {
            const response = await fetch('/api/scan_product', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ barcode: barcode })
            });

            const result = await response.json();

            if (result.success) {
                successSound.play().catch(e => console.error("Error al reproducir sonido:", e));
                showToast(`Producto "${result.product.nombre}" encontrado.`);
                addProductToList(result.product);
            } else {
                errorSound.play().catch(e => console.error("Error al reproducir sonido:", e));
                showToast(`Producto no encontrado: ${result.error}`, true);
            }
        } catch (error) {
            console.error('Error al buscar producto:', error);
            showToast('Error de red al buscar el producto.', true);
        } finally {
            showLoader(false);
            // Reanudar el escáner después de un breve momento para permitir al usuario ver el resultado
            setTimeout(() => {
                if (!isScannerActive) { // Solo si no está ya activo
                    startScanner();
                }
            }, 1500);
        }
    }

    function addProductToList(product) {
        if (scannedItems[product.id]) {
            scannedItems[product.id].quantity++;
        } else {
            scannedItems[product.id] = {
                data: product,
                quantity: 1
            };
        }
        renderProductList();
    }

    function renderProductList() {
        const totalProductos = Object.keys(scannedItems).length;
        productsCount.textContent = totalProductos + ' productos';

        if (totalProductos === 0) {
            productListDiv.innerHTML = `
                <div class="text-center text-muted mt-5">
                    <i class="bi bi-upc-scan display-4"></i>
                    <p class="mt-2">Escanee productos para comenzar...</p>
                </div>
            `;
            return;
        }

        productListDiv.innerHTML = '';

        for (const productId in scannedItems) {
            const item = scannedItems[productId];
            const itemDiv = document.createElement('div');
            itemDiv.className = 'card mb-2 shadow-sm';
            itemDiv.innerHTML = `
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${item.data.nombre}</h6>
                            <small class="text-muted">Stock actual: ${item.data.stock}</small>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <input type="number" class="form-control form-control-sm text-center"
                                   value="${item.quantity}" min="1" style="width: 70px;"
                                   data-product-id="${productId}">
                            <button class="btn btn-sm btn-outline-danger" data-product-id="${productId}" title="Eliminar">
                                <i class="bi bi-x-circle"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            productListDiv.appendChild(itemDiv);
        }
    }

    function showToast(message, isError = false) {
        // Usar Bootstrap toast si está disponible
        const toastElement = document.getElementById('toast-element');
        const toastMessage = document.getElementById('toast-message');

        if (toastElement && toastMessage) {
            toastMessage.textContent = message;
            toastElement.className = `toast align-items-center text-white border-0 ${isError ? 'bg-danger' : 'bg-success'}`;

            const bsToast = new bootstrap.Toast(toastElement);
            bsToast.show();
        } else {
            // Fallback básico
            alert(message);
        }
    }

    function updateScannerStatus(message, type = 'secondary') {
        if (scannerStatus) {
            scannerStatus.innerHTML = `<i class="bi bi-circle-fill text-${type}"></i> ${message}`;
        }
    }

    // Solicitar permisos de cámara antes de inicializar
    async function requestCameraPermissions() {
        try {
            updateScannerStatus('Solicitando permisos de cámara...', 'warning');
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "environment",
                    width: { min: 640, ideal: 1280 },
                    height: { min: 480, ideal: 720 }
                }
            });

            // Detener el stream después de obtener permisos
            stream.getTracks().forEach(track => track.stop());

            updateScannerStatus('Permisos de cámara concedidos', 'success');
            return true;
        } catch (error) {
            console.error('Error al solicitar permisos de cámara:', error);
            updateScannerStatus('Error: Permisos de cámara denegados', 'danger');
            showToast('Haz clic en "Activar Cámara" para permitir el acceso a la cámara.', true);
            showCameraOverlay(); // Mostrar overlay si no hay permisos
            return false;
        }
    }

    // --- EVENT LISTENERS ---

    // Botón de activación de cámara
    if (activateCameraBtn) {
        activateCameraBtn.addEventListener('click', async function() {
            initScanner(); // Intentar inicializar cuando se hace clic
        });
    }

    // Overlay también puede activar la cámara al hacer clic
    if (cameraOverlay) {
        cameraOverlay.addEventListener('click', function(e) {
            // No hacerlo si se hizo clic en el botón específicamente
            if (e.target !== activateCameraBtn) {
                initScanner();
            }
        });
    }

    // Activar cámara cuando se hace foco en campos de escaneo
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            // Solo activar si no está ya activo
            if (!quaggaInitialized && !isScannerActive) {
                setTimeout(() => initScanner(), 100); // Pequeño delay para UX
            }
        });
    });

    // Delegación de eventos para la lista de productos
    productListDiv.addEventListener('click', handleProductListActions);
    productListDiv.addEventListener('change', handleProductListActions);

    confirmStockBtn.addEventListener('click', async function() {
        const items = Object.values(scannedItems).map(item => ({
            product_id: item.data.id,
            quantity: item.quantity
        }));

        if (items.length === 0) {
            showToast("No hay productos en la lista.", true);
            return;
        }

        showLoader(true);
        try {
            const response = await fetch('/api/add_scanned_stock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: items })
            });
            const result = await response.json();
            showToast(result.message || result.error, !result.success);
            if (result.success) {
                Object.keys(scannedItems).forEach(key => delete scannedItems[key]); // Limpiar el objeto
                renderProductList();
            }
        } catch (error) {
            console.error('Error al confirmar stock:', error);
            showToast('Error de red al confirmar el ingreso de stock.', true);
        } finally {
            showLoader(false);        }
    });

    // Búsqueda manual mientras se escribe
    searchInput.addEventListener('keyup', async function(e) {
        const term = e.target.value;
        if (term.length < 3) {
            searchResultsDiv.innerHTML = '';
            return;
        }
        showLoader(true);
        try {
            const response = await fetch('/api/search_products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ term: term })
            });
            const result = await response.json();
            if (result.success) {
                renderSearchResults(result.products);
            } else {
                searchResultsDiv.innerHTML = '';
            }
        } catch (error) {
            showToast("Error de red al buscar.", true);
        } finally {
            showLoader(false);
        }
    });    

    // Delegación de eventos para los resultados de búsqueda
    searchResultsDiv.addEventListener('click', function(e) {
        if (e.target && e.target.matches('button.add-search-result')) {
            const productData = JSON.parse(e.target.dataset.product);
            addProductToList(productData);
            searchInput.value = '';
            searchResultsDiv.innerHTML = '';
        }
    });



    function renderSearchResults(products) {
        searchResultsDiv.innerHTML = products.length === 0 ? '<p class="no-results">No se encontraron productos.</p>' : '';
        products.forEach(product => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'search-result-item';
            // Usamos un atributo data-* para almacenar el objeto del producto de forma segura
            itemDiv.innerHTML = `
                <span>${product.nombre}</span>
                <button class="add-search-result" data-product='${JSON.stringify(product)}'>Añadir</button>
            `;
            searchResultsDiv.appendChild(itemDiv);
        });
    }

    function handleProductListActions(e) {
        const target = e.target;
        const productId = target.dataset.productId;

        if (target.matches('.remove-btn')) {
            delete scannedItems[productId];
            renderProductList();
            showToast("Producto eliminado de la lista.");
        }

        if (target.matches('.quantity-input')) {
            const newQuantity = parseInt(target.value, 10);
            if (scannedItems[productId] && newQuantity > 0) {
                scannedItems[productId].quantity = newQuantity;
            }
        }
    }

    // --- INICIO DE LA APLICACIÓN ---
    // Iniciar automáticamente al cargar la página
    document.addEventListener('DOMContentLoaded', function() {
        initScanner();

        // Listener global para inputs de escáner
        document.addEventListener('focusin', function(e) {
            const target = e.target;
            if (target.classList.contains('barcode-input-auto')) {
                // Esperar un poco antes de intentar activar para evitar conflictos
                setTimeout(() => {
                    if (!quaggaInitialized && !isScannerActive) {
                        initScanner();
                    }
                }, 100);
            }
        });

        // También iniciar si se hace clic en cualquier lugar de la página
        document.addEventListener('click', function() {
            if (!quaggaInitialized && !isScannerActive) {
                initScanner();
            }
        });
    });
});
