document.addEventListener('DOMContentLoaded', function() {
    const scannedItems = {}; // Objeto para almacenar productos escaneados { productId: {data, quantity} }
    let isScannerActive = false;
    let allProducts = []; // Caché de productos para la búsqueda

        // --- Elementos del DOM ---
    const loader = document.getElementById('loader');
    const toast = document.getElementById('toast');
    const searchInput = document.getElementById('search-input');

    // --- Sonidos ---
    const successSound = new Audio("data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU"+Array(1e3).join("121213131414151516161717181819191a1a1b1b1c1c1d1d1e1e1f1f20202121222223232424252526262727282829292a2a2b2b2c2c2d2d2e2e2f2f30303131323233333434353536363737383839393a3a3b3b3c3c3d3d3e3e3f3f40404141424243434444454546464747484849494a4a4b4b4c4c4d4d4e4e4f4f50505151525253535454555556565757585859595a5a5b5b5c5c5d5d5e5e5f5f60606161626263636464656566666767686869696a6a6b6b6c6c6d6d6e6e6f6f70707171727273737474757576767777787879797a7a7b7b7c7c7d7d7e7e7f7f80808181828283838484858586868787888889898a8a8b8b8c8c8d8d8e8e8f8f90909191929293939494959596969797989899999a9a9b9b9c9c9d9d9e9e9f9fa0a0a1a1a2a2a3a3a4a4a5a5a6a6a7a7a8a8a9a9aaabacacadaeaeafacecfcfdfdfeff"));
    const errorSound = new Audio("data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU"+Array(1e3).join("9898979796969595949493939292919190908f8f8e8e8d8d8c8c8b8b8a8a89898888878786868585848483838282818180807f7f7e7e7d7d7c7c7b7b7a7a79797878777776767575747473737272717170706f6f6e6e6d6d6c6c6b6b6a6a69696868676766666565646463636262616160605f5f5e5e5d5d5c5c5b5b5a5a59595858575756565555545453535252515150504f4f4e4e4d4d4c4c4b4b4a4a49494848474746464545444443434242414140403f3f3e3e3d3d3c3c3b3b3a3a39393838373736363535343433333232313130302f2f2e2e2d2d2c2c2b2b2a2a29292828272726262525242423232222212120201f1f1e1e1d1d1c1c1b1b1a1a19191818171716161515141413131212111110100f0f0e0e0d0d0c0c0b0b0a0a09090808070706060505040403030202010100"));

    // --- Funciones de UI ---
    function showLoader(show) {
        loader.style.display = show ? 'flex' : 'none';
    }

    function showToast(message, isError = false) {
        toast.textContent = message;
        toast.style.backgroundColor = isError ? 'var(--error-color)' : 'var(--success-color)';
        toast.className = "show";
        setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
    }

    function initScanner() {
        if (isScannerActive) {
            Quagga.stop();
            isScannerActive = false;
        }

        Quagga.init({
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: document.querySelector('#interactive'),
                constraints: {
                    width: { min: 640 },
                    height: { min: 480 },
                    facingMode: "environment" // Usa la cámara trasera del celular
                },
            },
            decoder: {
                readers: [
                    "code_128_reader",
                    "ean_reader",
                    "ean_8_reader",
                    "code_39_reader",
                    "code_39_vin_reader",
                    "codabar_reader",
                    "upc_reader",
                    "upc_e_reader",
                    "i2of5_reader"
                
                    
                ]
            },
        }, function(err) {
            if (err) {
                console.error(err);
                alert("Error al iniciar el escáner. Asegúrate de dar permisos a la cámara.");
                return;
            }
            console.log("Escáner iniciado correctamente.");
            Quagga.start();
            isScannerActive = true;
        });
    }

    Quagga.onDetected(function(result) {
        const code = result.codeResult.code;
        Quagga.stop(); // Pausar para evitar múltiples escaneos
        isScannerActive = false;
        handleBarcode(code);
    });

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
                successSound.play();
                showToast(`Producto "${result.product.nombre}" encontrado.`);
                addProductToList(result.product);
            } else {
                errorSound.play();
                showToast(`Producto no encontrado: ${result.error}`, true);
            }
        } catch (error) {
            console.error('Error al buscar producto:', error);
            showToast('Error de red al buscar el producto.', true);
        } finally {
            showLoader(false);
            // Reanudar el escáner después de un breve momento
            setTimeout(() => {
                Quagga.start();
                isScannerActive = true;
            }, 1000);
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

    window.addProductFromSearch = addProductToList;
    function renderProductList() {
        const productListDiv = document.getElementById('product-list');
        productListDiv.innerHTML = '<h2>Productos a Ingresar:</h2>'; // Limpiar y poner el título

        for (const productId in scannedItems) {
            const item = scannedItems[productId];
            const itemDiv = document.createElement('div');
            itemDiv.className = 'product-item';
            itemDiv.dataset.productId = productId;
            itemDiv.innerHTML = `
            <div class="info">
                    <span class="product-name">${item.data.nombre}</span>
                    <span class="product-stock">Stock actual: ${item.data.stock}</span>
                </div>
                <input type="number" value="${item.quantity}" min="1" onchange="updateQuantity(${productId}, this.value)">
                <button class="remove-btn" onclick="removeItem(${productId})">X</button>
            `;
            productListDiv.appendChild(itemDiv);
        }
    }
    
    window.removeItem = function(productId) {
        delete scannedItems[productId];
        renderProductList();
        showToast("Producto eliminado de la lista.");

    }
    window.updateQuantity = function(productId, newQuantity) {
        if (scannedItems[productId]) {
            scannedItems[productId].quantity = parseInt(newQuantity, 10);
        }
    }

    document.getElementById('confirm-stock').addEventListener('click', async function() {
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

        // --- Lógica de Búsqueda Manual ---
    document.getElementById('search-button').addEventListener('click', async function() {
        const searchTerm = searchInput.value;
        if (searchTerm.length < 3) {
            showToast("La búsqueda requiere al menos 3 caracteres.", true);
            return;
        }

        showLoader(true);
        try {
            const response = await fetch('/api/search_products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ term: searchTerm })
            });
            const result = await response.json();
            if (result.success) {
                renderSearchResults(result.products);
            } else {
                showToast(result.error, true);
            }
        } catch (error) {
            showToast("Error de red al buscar.", true);
        } finally {
            showLoader(false);
        }
    });

    function renderSearchResults(products) {
        const resultsDiv = document.getElementById('search-results');
        resultsDiv.innerHTML = '';
        if (products.length === 0) {
            resultsDiv.innerHTML = '<p>No se encontraron productos.</p>';
            return;
        }

        products.forEach(product => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'search-result-item';
            // Usamos JSON.stringify para pasar el objeto completo del producto al hacer clic
            itemDiv.innerHTML = `
                <span>${product.nombre}</span>
                <button onclick='addProductFromSearch(${JSON.stringify(product)})'>Añadir</button>
            `;
            resultsDiv.appendChild(itemDiv);
        });
    }

    // Iniciar el escáner al cargar la página
    initScanner();
});

