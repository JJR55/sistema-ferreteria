document.addEventListener('DOMContentLoaded', function() {
    // --- ESTADO DE LA APLICACIÓN ---
    const scannedItems = {}; // { productId: {data, quantity} }
    let isScannerActive = false; // Estado del stream de Quagga
    let quaggaInitialized = false; // Si Quagga.init() ya fue llamado
    let currentMode = 'auto'; // 'auto' o 'mobile' (server-side)
    let currentFacingMode = 'environment'; // 'environment' (trasera) o 'user' (frontal)
    let lastScannedCode = null;
    let mobileStream = null; // Stream para el modo mobile
    let mobileContext = null;

    // --- ELEMENTOS DEL DOM ---
    const loader = document.getElementById('loader');
    const searchInput = document.getElementById('search-input');
    const searchResultsDiv = document.getElementById('search-results');
    const productListDiv = document.getElementById('product-list');
    const confirmStockBtn = document.getElementById('confirm-stock');
    const interactiveDiv = document.getElementById('interactive');
    const scannerStatus = document.getElementById('scanner-status');
    const productsCount = document.getElementById('products-count');
    const toggleCameraButton = document.getElementById('toggle-camera-btn');
    const cameraOverlay = document.getElementById('camera-overlay'); // Div que cubre el video
    const activateCameraBtn = document.getElementById('activate-camera-btn'); // Botón para activar


    // Modo scanner
    const scannerMode = document.getElementById('scanner-mode'); // Select para cambiar modo
    const modeDescription = document.getElementById('mode-description'); // Descripción del modo
    const scannerAuto = document.getElementById('scanner-auto'); // Contenedor para Quagga
    const scannerMobile = document.getElementById('scanner-mobile'); // Contenedor para modo móvil
    const mobileVideoElement = document.getElementById('mobile-video'); // Video para modo móvil
    const mobileCanvasElement = document.getElementById('mobile-canvas'); // Canvas para modo móvil
    const captureFrameBtn = document.getElementById('capture-frame-btn');
    const toggleFlashBtn = document.getElementById('toggle-flash-btn');

    // --- ELEMENTOS DEL MODAL DE EDICIÓN ---
    const editModalElement = document.getElementById('editNewProductModal');
    const editModal = editModalElement ? new bootstrap.Modal(editModalElement) : null;
    const editProductIdInput = document.getElementById('edit-product-id');
    const editProductNameInput = document.getElementById('edit-product-name');
    const editProductPriceInput = document.getElementById('edit-product-price');
    const saveProductChangesBtn = document.getElementById('save-product-changes-btn');
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

    // --- LÓGICA DEL ESCÁNER (QUAGGA.JS) ---
    async function initScanner() {
        if (quaggaInitialized) return; // Evitar reinicializar si ya está listo

        // Primero solicitar permisos de cámara
        // Esta función ahora maneja la UI de pedir permisos
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
                    facingMode: currentFacingMode // Usa la cámara seleccionada
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
            quaggaInitialized = true; // Marcar como inicializado
            updateScannerStatus('Escáner listo', 'success');
            if (toggleCameraButton) toggleCameraButton.style.display = 'inline-block';

            // Iniciar automáticamente después de 1 segundo
            setTimeout(() => {
                startScanner();
            }, 1000);
        });

        Quagga.onDetected(handleDetection);
        
        // Ocultar el overlay cuando Quagga inicia correctamente
        Quagga.onReady(function() {
            const cameraOverlay = document.getElementById('camera-overlay');
            if (cameraOverlay) {
                cameraOverlay.style.display = 'none';
            }
        });

        // Dibuja las cajas de detección sobre el video
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
            interactiveDiv.style.display = 'block'; // Mostrar el visor
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
            interactiveDiv.style.display = 'none'; // Ocultar el visor
            if (toggleCameraButton) toggleCameraButton.style.display = 'none';
            updateScannerStatus('Escáner pausado', 'warning');
        }
    }

    const handleDetection = (result) => {
        // Si el escáner no está activo (en cooldown), no hacer nada.
        if (!isScannerActive) return;

        const code = result.codeResult.code;

        // Pausar el escáner para procesar este código y evitar lecturas múltiples.
        isScannerActive = false;
        updateScannerStatus('Código detectado - procesando...', 'info');

        // Usamos una promesa para asegurarnos de que el procesamiento termine antes de reactivar.
        handleBarcode(code).finally(() => {
            // Reactivar el escáner después de un breve "cooldown" para evitar lecturas accidentales del mismo código.
            setTimeout(() => {
                isScannerActive = true;
                // Solo actualizar el estado si no hay otro proceso en curso.
                if (scannerStatus.textContent.includes('procesando')) {
                    updateScannerStatus('Escáner activo - enfocando código', 'primary');
                }
            }, 800); // 0.8 segundos de enfriamiento.
        });
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
                // Usar la función global definida en scanner.html
                if (typeof playSuccessBeep === 'function') {
                    playSuccessBeep();
                } else {
                    successSound.play().catch(e => console.error("Error al reproducir sonido:", e));
                }
                showToast(`Producto "${result.product.nombre}" encontrado.`);
                addProductToList(result.product, 1);
            } else {
                // Usar la función global definida en scanner.html
                if (typeof playErrorBeep === 'function') {
                    playErrorBeep();
                } else {
                    errorSound.play().catch(e => console.error("Error al reproducir sonido:", e));
                }
                showToast(`Producto no encontrado (${barcode}). Se agregará como nuevo.`, true);
                // Crear un producto placeholder si no se encuentra
                const newProductPlaceholder = {
                    id: 'new_' + barcode, // ID temporal
                    nombre: `Nuevo Producto (${barcode})`,
                    codigo_barras: barcode,
                    stock: 0,
                    precio: 0,
                    costo: 0,
                    is_new: true // Marcar como nuevo
                };
                addProductToList(newProductPlaceholder, 1);
            }
        } catch (error) {
            console.error('Error al buscar producto:', error);
            showToast('Error de red al buscar el producto.', true);
        } finally {
            showLoader(false); // Ocultar loader en cualquier caso
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
            itemDiv.className = 'card mb-2 shadow-sm product-item';
            itemDiv.dataset.productId = productId; // Añadir ID para facilitar la selección

            if (item.data.is_new) {
                itemDiv.classList.add('border-warning'); // Resaltar productos nuevos
                itemDiv.style.cursor = 'pointer'; // Indicar que es clickeable
                itemDiv.title = 'Haz clic para editar este nuevo producto';
            }
            itemDiv.innerHTML = `
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${item.data.nombre}</h6>
                            <small class="text-muted">Stock actual: ${item.data.stock} | Precio: ${formatCurrency(item.data.precio)}</small>
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

    function formatCurrency(value) {
        return new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(value || 0);
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
                    height: { min: 480, ideal: 720 },
                    torch: true // Solicitar control del flash si es posible
                }
            });

            // Detener el stream después de obtener permisos
            stream.getTracks().forEach(track => track.stop());

            updateScannerStatus('Permisos de cámara concedidos', 'success');
            return true;
        } catch (error) {
            console.error('Error al solicitar permisos de cámara:', error);
            updateScannerStatus('Error: Permisos de cámara denegados', 'danger');
             // Mensaje más informativo para el usuario
            const errorMessage = (window.isSecureContext)
                ? 'Permiso de cámara denegado. Revisa la configuración de permisos de tu navegador para este sitio.'
                : 'El acceso a la cámara requiere una conexión segura (HTTPS). Esta función podría no estar disponible en redes locales (HTTP).';
            showToast(errorMessage, true);
            showCameraOverlay(); // Mostrar overlay si no hay permisos
            return false;
        }
    }

    // --- EVENT LISTENERS ---

    // Botón de activación de cámara
    if (activateCameraBtn) {
        activateCameraBtn.addEventListener('click', initScanner);
    } 
    if(cameraOverlay) {
        cameraOverlay.addEventListener('click', initScanner);
    }

    if (toggleCameraButton) {
        toggleCameraButton.addEventListener('click', () => {
            if (!isScannerActive) return;
            // Cambiar modo
            currentFacingMode = (currentFacingMode === 'environment') ? 'user' : 'environment';
            // Detener y reiniciar el escáner con la nueva cámara
            stopScanner();
            quaggaInitialized = false; // Forzar reinicialización
            initScanner();
        });
    }

    // Delegación de eventos para la lista de productos
    if (productListDiv) {
        productListDiv.addEventListener('click', handleProductListActions);
        productListDiv.addEventListener('change', handleProductListActions);
    }

    if (confirmStockBtn) {
        confirmStockBtn.addEventListener('click', async function() {
            const allItems = Object.values(scannedItems);
            if (allItems.length === 0) {
                showToast("No hay productos en la lista.", true);
                return;
            }

            const existingItems = allItems
                .filter(item => !item.data.is_new)
                .map(item => ({ product_id: item.data.id, quantity: item.quantity }));

            const newItems = allItems
                .filter(item => item.data.is_new)
                .map(item => ({
                    nombre: item.data.nombre,
                    stock: item.quantity,
                    costo: item.data.costo || 0,
                    precio: item.data.precio || 0,
                    stock_minimo: item.data.stock_minimo || 1,
                    departamento: item.data.departamento || 'Sin Asignar'
                }));

            showLoader(true);
            try {
                // Primero, crear productos nuevos si los hay
                if (newItems.length > 0) {
                    const respNew = await fetch('/api/products/bulk_add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ products: newItems })
                    });
                    const resNew = await respNew.json();
                    if (!resNew.success) {
                        showToast('Error al crear productos nuevos: ' + (resNew.error || ''), true);
                        return;
                    }
                }

                // Luego, sumar stock a los productos existentes
                if (existingItems.length > 0) {
                    const resp = await fetch('/api/add_scanned_stock', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ items: existingItems })
                    });
                    const result = await resp.json();
                    if (!result.success) {
                        showToast('Error al actualizar stock: ' + (result.error || ''), true);
                        return;
                    }
                }

                showToast('Stock actualizado correctamente.');
                Object.keys(scannedItems).forEach(key => delete scannedItems[key]); // Limpiar el objeto
                renderProductList();
            } catch (error) {
                console.error('Error al confirmar stock:', error);
                showToast('Error de red al confirmar el ingreso de stock.', true);
            } finally {
                showLoader(false);
            }
        });
    }

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

    // Delegación de eventos para los resultados de búsqueda manual
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
            itemDiv.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            // Usamos un atributo data-* para almacenar el objeto del producto de forma segura
            itemDiv.innerHTML = `
                <span>${product.nombre}</span>
                <button class="add-search-result" data-product='${JSON.stringify(product)}'>Añadir</button>
            `;
            searchResultsDiv.appendChild(itemDiv);
        });
    }

    // --- FUNCIONES DEL ESCÁNER MÓVIL (Server-Side Processing) ---
    async function initMobileScanner() {
        try {
            // Solicitar acceso a la cámara
            updateScannerStatus('Accediendo a cámara...', 'warning');

            // Verificar soporte de getUserMedia
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                console.warn('navigator.mediaDevices.getUserMedia no está disponible');
                updateScannerStatus('Cámara no soportada en este navegador', 'warning');
                showToast("Tu dispositivo no soporta acceso a cámara.", true);
                return false;
            }

            mobileStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: 'environment' }, // Cámara trasera preferida
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });

            mobileVideoElement.srcObject = mobileStream;
            await mobileVideoElement.play();

            // Inicializar canvas
            mobileCanvasElement.width = mobileVideoElement.videoWidth;
            mobileCanvasElement.height = mobileVideoElement.videoHeight;
            mobileContext = mobileCanvasElement.getContext('2d');

            updateScannerStatus('Cámara lista - capturando frames...', 'success');
            captureFrameBtn.disabled = false;

            return true;
        } catch (error) {
            console.error('Error accediendo a cámara:', error);
            updateScannerStatus('Error: No se puede acceder a la cámara', 'danger');
            showToast("Error al acceder a la cámara. Verifica los permisos.", true);
            return false;
        }
    }

    function stopMobileScanner() {
        if (mobileStream) {
            mobileStream.getTracks().forEach(track => track.stop());
            mobileStream = null;
        }
        mobileVideoElement.srcObject = null;
        captureFrameBtn.disabled = true;
        updateScannerStatus('Cámara detenida', 'warning');
    }

    function captureMobileFrame() {
        if (!mobileContext || !isScannerActive) return;

        showLoader(true);
        updateScannerStatus('Procesando imagen...', 'info');

        try {
            // Capturar el frame actual
            mobileContext.drawImage(mobileVideoElement, 0, 0, mobileCanvasElement.width, mobileCanvasElement.height);

            // Convertir a imagen base64
            const imageData = mobileCanvasElement.toDataURL('image/jpeg', 0.8);

            // Enviar la imagen al servidor
            processImageOnServer(imageData);

        } catch (error) {
            console.error('Error capturando imagen:', error);
            showToast("Error al capturar imagen.", true);
            showLoader(false);
        }
    }

    async function processImageOnServer(imageData) {
        try {
            // Crear FormData con la imagen
            const formData = new FormData();
            const imageBlob = await fetch(imageData).then(r => r.blob());
            formData.append('image', imageBlob, 'capture.jpg');

            const response = await fetch('/api/scan_image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                // Usar la función global definida en scanner.html
                if (typeof playSuccessBeep === 'function') {
                    playSuccessBeep();
                } else {
                    successSound.play().catch(e => console.error("Error sonido:", e));
                }
                showToast(`Producto "${result.product.nombre}" encontrado.`);
                addProductToList(result.product);

                // Integración automática con POS si está en modo POS
                if (window.isPosMode) {
                    updatePosCart(result.product);
                }
            } else {
                // Usar la función global definida en scanner.html
                if (typeof playErrorBeep === 'function') {
                    playErrorBeep();
                } else {
                    errorSound.play().catch(e => console.error("Error sonido:", e));
                }
                if (result.barcode) {
                    showToast(`Código detectado: ${result.barcode}. ${result.error}`, true);
                } else {
                    showToast(`No se encontraron códigos. ${result.error}`, true);
                }
            }
        } catch (error) {
            console.error('Error procesando imagen en servidor:', error);
            showToast("Error procesando imagen.", true);
        } finally {
            showLoader(false);
            updateScannerStatus('Listo para capturar', 'success');
        }
    }

    // --- CAMBIO DE MODOS ---
    function changeScannerMode(mode) {
        currentMode = mode;

        // Ocultar todos los scanners primero
        scannerAuto.style.display = 'none';
        scannerMobile.style.display = 'none';

        // Detener cualquier scanner activo
        if (isScannerActive) {
            if (currentMode === 'auto') {
                stopMobileScanner();
            } else {
                stopScanner();
            }
        }

        // Mostrar el scanner seleccionado
        if (mode === 'auto') {
            scannerAuto.style.display = 'block';
            modeDescription.innerHTML = `
                <i class="bi bi-info-circle"></i>
                Escaneo automático con QuaggaJS.
                Ideal para códigos de barras estándar (EAN, UPC, Code 128) en buenas condiciones.
            `;
            // Solo inicializar si no se ha hecho antes
            if (!quaggaInitialized) {
                initScanner();
            }
        } else if (mode === 'mobile') {
            scannerMobile.style.display = 'block';
            modeDescription.innerHTML = `
                <i class="bi bi-info-circle"></i>
                Escaneo móvil avanzado con IA del servidor.
                Captura imágenes para procesamiento inteligente.
                Útil para códigos dañados, en ángulos difíciles o con poca luz.
            `;
            setTimeout(() => {
                initMobileScanner();
                isScannerActive = true;
            }, 500);
        }

        updateScannerStatus('Cambiando modo de escaneo...', 'warning');
    }

    // --- INTEGRACIÓN CON OTRAS PÁGINAS (EJ. POS) ---
    function updatePosCart(product) {
        // Si estamos en modo POS, agregar el producto automáticamente al carrito
        if (window.posCart && typeof window.posCart.addItem === 'function') {
            // Calcular cantidad predeterminada (1 por defecto, pero puede cambiarse)
            window.posCart.addItem({
                id: product.id,
                nombre: product.nombre,
                precio: product.precio,
                costo: product.costo,
                cantidad: 1,
                barcode: product.codigo_barras
            });
        }

        // Si se puede manejar desde el POS de manera automática
        if (window.triggerPosScan) {
            window.triggerPosScan(product);
        }
    }

    function handleProductListActions(e) {
        const target = e.target;
        const productId = target.dataset.productId;
        const productItemCard = target.closest('.product-item');

        // Si se hace clic en el botón de eliminar
        if (target.closest('.btn-outline-danger') && productId) {
            e.stopPropagation(); // Evitar que se dispare el clic en la tarjeta
            delete scannedItems[productId];
            renderProductList();
            showToast("Producto eliminado de la lista.");
        }
        // Si se cambia la cantidad en el input
        else if (target.matches('input[type="number"]') && productId) {
            e.stopPropagation();
            const newQuantity = parseInt(target.value, 10);
            if (scannedItems[productId] && newQuantity > 0) {
                scannedItems[productId].quantity = newQuantity;
            }
        }
        // Si se hace clic en una tarjeta de "Nuevo Producto"
        else if (productItemCard && productItemCard.classList.contains('border-warning')) {
            const clickedProductId = productItemCard.dataset.productId;
            const item = scannedItems[clickedProductId];
            if (item && item.data.is_new) {
                openEditModal(clickedProductId);
            }
        }
    }

    // --- EVENT LISTENERS PARA MODOS DE SCANNER ---
    // Cambio de modo de scanner
    if (scannerMode) {
        scannerMode.addEventListener('change', function(e) {
            changeScannerMode(e.target.value);
        });
    }

    // Botón de captura de frame móvil
    if (captureFrameBtn) {
        captureFrameBtn.addEventListener('click', function() {
            captureMobileFrame();
        });
    }

    // --- LÓGICA DEL MODAL DE EDICIÓN ---
    function openEditModal(productId) {
        const item = scannedItems[productId];
        if (!item || !editModal) return;

        editProductIdInput.value = productId;
        editProductNameInput.value = item.data.nombre;
        editProductPriceInput.value = item.data.precio;

        editModal.show();
    }

    if (saveProductChangesBtn) {
        saveProductChangesBtn.addEventListener('click', () => {
            const productId = editProductIdInput.value;
            const newName = editProductNameInput.value.trim();
            const newPrice = parseFloat(editProductPriceInput.value) || 0;

            if (scannedItems[productId] && newName) {
                scannedItems[productId].data.nombre = newName;
                scannedItems[productId].data.precio = newPrice;
                renderProductList();
                editModal.hide();
            }
        });
    }

    // Toggle de flash (si está disponible)
    if (toggleFlashBtn) {
        toggleFlashBtn.addEventListener('click', function() {
            // La lógica para el flash es compleja y depende del stream activo.
            // Se simplifica por ahora, se puede implementar si es un requisito fuerte.
            showToast("Funcionalidad de flash en desarrollo.", true);
        });
    }

    // --- INICIO DE LA APLICACIÓN ---
    // Inicializar en modo automático por defecto
    changeScannerMode('auto');

    // Detectar si estamos en página de POS
    const urlParams = new URLSearchParams(window.location.search);
    window.isPosMode = window.location.pathname.includes('/pos') || urlParams.get('pos') === 'true';

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

    // Quitar el inicio automático al hacer clic en cualquier lugar, es mejor que sea explícito.
    /*
        // También iniciar si se hace clic en cualquier lugar de la página
        document.addEventListener('click', function() {
            if (!quaggaInitialized && !isScannerActive) {
                initScanner();
            }
        });

    */

    // Exponer funciones globales para integración con POS
    window.scannerAddToCart = (product) => {
        if (product) {
            updatePosCart(product);
        }
    };

    // Función para cambiar modo desde fuera
    window.setScannerMode = (mode, autoStart = false) => {
        scannerMode.value = mode;
        changeScannerMode(mode);
        if (autoStart) {
            isScannerActive = true;
            if (mode === 'mobile') {
                initMobileScanner();
            } else {
                startScanner();
            }
        }
    };
});
