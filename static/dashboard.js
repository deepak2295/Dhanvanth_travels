const main = document.getElementById('main-content');
    const sidebar = document.getElementById('sidebar');
    let revenueChart = null; // To store the Chart.js instance

   // Assuming your Flask app runs on http://127.0.0.1:5000

    // --- Custom Modal Functions (replaces alert/confirm) ---
    const customModal = document.getElementById('customModal');
    const modalMessage = document.getElementById('modalMessage');
    const modalConfirmBtn = document.getElementById('modalConfirmBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');
    const modalOkBtn = document.getElementById('modalOkBtn');
    let modalResolve = null; // To store the resolve function for promises

    function showModal(message, type = 'alert') { 
        modalMessage.textContent = message;
        customModal.style.display = 'flex';

        modalConfirmBtn.style.display = 'none';
        modalCancelBtn.style.display = 'none';
        modalOkBtn.style.display = 'none';

        if (type === 'confirm') {
            modalConfirmBtn.style.display = 'inline-block';
            modalCancelBtn.style.display = 'inline-block';
            modalConfirmBtn.onclick = () => { hideModal(); modalResolve(true); };
            modalCancelBtn.onclick = () => { hideModal(); modalResolve(false); };
        } else if (type === 'alert') {
            modalOkBtn.style.display = 'inline-block';
            modalOkBtn.onclick = () => { hideModal(); modalResolve(true); };
        } else if (type === 'toast') {
            // For toast, we'll auto-hide it after a few seconds
            modalOkBtn.style.display = 'inline-block'; // Still show OK button for consistency, but it will auto-hide
            modalOkBtn.onclick = () => { hideModal(); modalResolve(true); };
            setTimeout(() => {
                if (customModal.style.display === 'block' && modalMessage.textContent === message) {
                    hideModal();
                    if (modalResolve) resolve(true); // Resolve the promise for toast
                }
            }, 3000); // Auto-hide after 3 seconds
        }

        return new Promise(resolve => {
            modalResolve = resolve;
        });
    }

    function hideModal() {
        customModal.style.display = 'none';
    }

    // Close modal if user clicks outside of it
    window.onclick = function(event) {
        if (event.target == customModal) {
            hideModal();
            if (modalResolve) modalResolve(false); // Resolve confirm as false if clicked outside
        }
    }
    // --- End Custom Modal Functions ---

    // --- NEW: Loading Indicator Functions ---
    function showLoading() {
        main.insertAdjacentHTML('beforeend', `<div id="loading-overlay" class="loading-overlay">
            <div class="spinner"></div>
            <p>Loading...</p>
        </div>`);
    }

    function hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }
    // --- End Loading Indicator Functions ---


    function toggleSidebar() {
      sidebar.classList.toggle('active');
    }

    async function selectSection(section) {
      await loadSection(section); // Ensure section content is loaded before removing sidebar
      if (window.innerWidth <= 768) sidebar.classList.remove('active');
    }

    // --- NEW: Filter/Search Logic ---
    let currentTableData = []; // Store the full data for client-side filtering
    let currentSection = ''; // Keep track of the current section for filtering/pagination

    function toggleFilterInput() {
      const input = document.getElementById('filterInput');
      input.style.display = input.style.display === 'none' ? 'inline-block' : 'none';
      if (input.style.display === 'inline-block') input.focus();
    }

    function filterTable() {
        const filterInput = document.getElementById('filterInput');
        const filterText = filterInput.value.toLowerCase();
        const tbody = document.getElementById(`${currentSection}-table`);
        const config = sectionsConfig[currentSection];

        if (!tbody || !config) return;

        tbody.innerHTML = ''; // Clear current table

        const filteredData = currentTableData.filter(row => {
            return config.columns.some(col => {
                const value = String(row[col.db_name]).toLowerCase();
                return value.includes(filterText);
            });
        });

        renderTableRows(filteredData, currentSection); // Render filtered data
        updatePagination(filteredData.length); // Update pagination for filtered data
    }

    // --- NEW: Client-side Sorting ---
    let sortColumn = null;
    let sortDirection = 'asc'; // 'asc' or 'desc'

    function sortTable(columnName, section) {
        const config = sectionsConfig[section];
        const columnConfig = config.columns.find(col => col.db_name === columnName);

        if (!columnConfig) return; // Cannot sort if column config not found

        // Toggle sort direction
        if (sortColumn === columnName) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortColumn = columnName;
            sortDirection = 'asc';
        }

        // Sort the currentTableData
        currentTableData.sort((a, b) => {
            let valA = a[columnName];
            let valB = b[columnName];

            // Handle numeric sorting
            if (typeof valA === 'number' && typeof valB === 'number') {
                return sortDirection === 'asc' ? valA - valB : valB - valA;
            }
            // Handle string sorting (case-insensitive)
            valA = String(valA).toLowerCase();
            valB = String(valB).toLowerCase();
            if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        renderTableRows(currentTableData, section); // Re-render sorted data
        updatePagination(currentTableData.length); // Re-render pagination
    }

    // --- NEW: Client-side Pagination ---
    const ROWS_PER_PAGE = 10;
    let currentPage = 1;

    function setupPagination(totalRows) {
        const paginationContainer = document.getElementById('pagination-controls');
        if (!paginationContainer) return;

        paginationContainer.innerHTML = '';
        const totalPages = Math.ceil(totalRows / ROWS_PER_PAGE);

        if (totalPages <= 1) return; // No pagination needed for 1 or less pages

        // Previous button
        const prevButton = document.createElement('button');
        prevButton.textContent = 'Previous';
        prevButton.disabled = currentPage === 1;
        prevButton.onclick = () => {
            if (currentPage > 1) {
                currentPage--;
                renderTableRows(currentTableData, currentSection);
                updatePagination(totalRows);
            }
            // Ensure filter is reapplied if active
            filterTable();
        };
        paginationContainer.appendChild(prevButton);

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            const pageButton = document.createElement('button');
            pageButton.textContent = i;
            pageButton.classList.add('page-button');
            if (i === currentPage) {
                pageButton.classList.add('active');
            }
            pageButton.onclick = () => {
                currentPage = i;
                renderTableRows(currentTableData, currentSection);
                updatePagination(totalRows);
                // Ensure filter is reapplied if active
                filterTable();
            };
            paginationContainer.appendChild(pageButton);
        }

        // Next button
        const nextButton = document.createElement('button');
        nextButton.textContent = 'Next';
        nextButton.disabled = currentPage === totalPages;
        nextButton.onclick = () => {
            if (currentPage < totalPages) {
                currentPage++;
                renderTableRows(currentTableData, currentSection);
                updatePagination(totalRows);
            }
            // Ensure filter is reapplied if active
            filterTable();
        };
        paginationContainer.appendChild(nextButton);
    }

    function updatePagination(totalRows) {
        setupPagination(totalRows);
        renderTableRows(currentTableData, currentSection); // Re-render current page
    }

    // Function to fetch data from API
    async function fetchTableData(section) {
        const config = sectionsConfig[section];
        if (!config || !config.api_endpoint) {
            console.warn(`No API endpoint configured for section: ${section}`);
            return [];
        }
        try {
            const data = await makeApiCall('GET', config.api_endpoint);
            // Always update currentTableData with the fresh data
            currentTableData = data;
            return data;
        } catch (error) {
            console.error(`Error fetching data for ${section}:`, error);
            return [];
        }
    }

 
// ... (keep the other existing sections like customers, drivers, etc.)
    const sectionsConfig = {
        // In the sectionsConfig object in index.html

// Add this new 'owners' object inside sectionsConfig
        owners: {
        api_endpoint: '/api/owners',
        id_key: 'id',
        columns: [
            { db_name: 'id', display_name: 'ID' },
            { db_name: 'name', display_name: 'Name' },
            { db_name: 'email', display_name: 'Email' },
            { db_name: 'phone', display_name: 'Phone' }
        ],
        input_fields: [
            { db_name: 'name', label: 'Owner Name', type: 'text', required: true },
            { db_name: 'email', label: 'Email', type: 'email', required: true },
            { db_name: 'phone', label: 'Phone', type: 'tel', required: true },
            { db_name: 'password', label: 'Password', type: 'password', required: true, exclude_from_edit: true }
        ]
        },

// ... (keep the other existing sections like customers, drivers, etc.)
      customers: {
        api_endpoint: '/api/customers',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'ID' },
          { db_name: 'name', display_name: 'Name' },
          { db_name: 'phone', display_name: 'Phone' }
        ],
        input_fields: [
          { db_name: 'name', label: 'Customer Name', type: 'text', required: true },
          { db_name: 'phone', label: 'Phone', type: 'text', required: true }
        ]
      },
      drivers: {
        api_endpoint: '/api/drivers',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'ID' },
          { db_name: 'name', display_name: 'Name' },
          { db_name: 'phone', display_name: 'Phone' },
          { db_name: 'car_model', display_name: 'Assigned Car' }, // Display only
          { db_name: 'status', display_name: 'Status' },
          { db_name: 'last_latitude', display_name: 'Last Lat' }, // New column
          { db_name: 'last_longitude', display_name: 'Last Lng' } // New column
        ],
        input_fields: [
          { db_name: 'name', label: 'Driver Name', type: 'text', required: true },
          { db_name: 'phone', label: 'Phone', type: 'text', required: true },
          { db_name: 'car_id', label: 'Car ID (Optional)', type: 'number', required: false }, // For linking to car
          { db_name: 'status', label: 'Status', type: 'select', options: ['free', 'busy'], required: true },
          { db_name: 'last_latitude', label: 'Last Latitude', type: 'number', step: 'any', required: false }, // New input
          { db_name: 'last_longitude', label: 'Last Longitude', type: 'number', step: 'any', required: false } // New input
        ]
      },
      vehicles: {
        api_endpoint: '/api/vehicles',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'ID' },
          { db_name: 'car_number', display_name: 'Car Number' },
          { db_name: 'model', display_name: 'Model' },
          { db_name: 'type', display_name: 'Type' },
          { db_name: 'rate', display_name: 'Rate/km' },
          { db_name: 'status', display_name: 'Status' }
        ],
        input_fields: [
          { db_name: 'car_number', label: 'Car Number', type: 'text', required: true },
          { db_name: 'model', label: 'Model', type: 'text', required: true },
          { db_name: 'type', label: 'Type', type: 'select', options: ['sedan', 'suv', 'compact', 'luxury'], required: true },
          { db_name: 'rate', label: 'Rate/km', type: 'number', step: '0.01', required: true },
          { db_name: 'status', label: 'Status', type: 'select', options: ['free', 'busy'], required: true }
        ]
      },
      bookings: {
        api_endpoint: '/api/bookings',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'Booking ID' },
          { db_name: 'customer_name', display_name: 'Customer' },
          { db_name: 'driver_name', display_name: 'Driver' },
          { db_name: 'pickup', display_name: 'Pickup' },
          { db_name: 'destination', display_name: 'Destination' },
          { db_name: 'fare', display_name: 'Fare' },
          { db_name: 'status', display_name: 'Status' },
          { db_name: 'payment_status', display_name: 'Payment Status' },
          { db_name: 'start_time', display_name: 'Start Time' },
          { db_name: 'end_time', display_name: 'End Time' },
          { db_name: 'invoice_action', display_name: 'Invoice' } // New column for invoice download
        ],
        input_fields: [
          { db_name: 'user_phone', label: 'Customer Phone', type: 'text', required: true }, // Use phone to link to user
          { db_name: 'pickup', label: 'Pickup Location', type: 'text', required: true },
          { db_name: 'destination', label: 'Destination', type: 'text', required: true },
          { db_name: 'distance', label: 'Distance (e.g., 10 km)', type: 'text', required: false },
          { db_name: 'duration', label: 'Duration (e.g., 20 min)', type: 'text', required: false },
          { db_name: 'fare', label: 'Fare', type: 'number', step: '0.01', required: true },
          { db_name: 'car_id', label: 'Car ID', type: 'number', required: false },
          { db_name: 'driver_id', label: 'Driver ID', type: 'number', required: false },
          { db_name: 'status', label: 'Status', type: 'select', options: ['pending', 'ongoing', 'completed', 'cancelled', 'prebooked'], required: true },
          { db_name: 'payment_status', label: 'Payment Status', type: 'select', options: ['pending', 'paid', 'cash'], required: true },
          { db_name: 'start_time', label: 'Start Time (YYYY-MM-DD HH:MM:SS)', type: 'text', required: false },
          { db_name: 'end_time', label: 'End Time (YYYY-MM-DD HH:MM:SS)', type: 'text', required: false }
        ]
      },
      assigned: { // Read-only for now, as it's a filtered view of bookings
        api_endpoint: '/api/assigned_bookings',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'Booking ID' },
          { db_name: 'customer_name', display_name: 'Customer' },
          { db_name: 'driver_name', display_name: 'Driver' },
          { db_name: 'pickup', display_name: 'Pickup' },
          { db_name: 'destination', display_name: 'Destination' },
          { db_name: 'status', display_name: 'Status' },
          { db_name: 'start_time', display_name: 'Start Time' }
        ],
        input_fields: [] // No add/edit for this filtered view
      },
      manualBooking: { // New section for manual bookings
        api_endpoint: '/api/manual_booking',
        id_key: 'id', // Not directly used for display, but good practice
        columns: [], // No table display for this section, just a form
        input_fields: [
            { db_name: 'user_phone', label: 'Customer Phone', type: 'text', required: true },
            { db_name: 'pickup', label: 'Pickup Location', type: 'text', required: true },
            { db_name: 'destination', label: 'Destination', type: 'text', required: true },
            { db_name: 'car_type', label: 'Car Type', type: 'select', options: ['sedan', 'suv', 'compact', 'luxury'], required: true },
            { db_name: 'booking_date', label: 'Booking Date (YYYY-MM-DD)', type: 'date', required: true },
            { db_name: 'booking_time', label: 'Booking Time (HH:MM)', type: 'time', required: true }
        ]
      },
      pricing: {
        api_endpoint: '/api/pricing',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'ID' },
          { db_name: 'vehicle_type', display_name: 'Vehicle Type' },
          { db_name: 'model', display_name: 'Model' },
          { db_name: 'price_per_km', display_name: 'Price/km' }
        ],
        input_fields: [
          { db_name: 'vehicle_type', label: 'Vehicle Type', type: 'text', required: true },
          { db_name: 'model', label: 'Model', type: 'text', required: true },
          { db_name: 'price_per_km', label: 'Price/km', type: 'number', step: '0.01', required: true }
        ]
      },
      coupons: {
        api_endpoint: '/api/coupons',
        id_key: 'code', // Coupon code is the ID
        columns: [
          { db_name: 'code', display_name: 'Coupon Code' },
          { db_name: 'discount', display_name: 'Discount (%)' },
          { db_name: 'used', display_name: 'Used' }
        ],
        input_fields: [
          { db_name: 'code', label: 'Coupon Code', type: 'text', required: true },
          { db_name: 'discount', label: 'Discount (%)', type: 'number', step: '0.01', required: true },
          { db_name: 'used', label: 'Used', type: 'select', options: ['0', '1'], required: true } // 0 for No, 1 for Yes
        ]
      },
      locations: {
        api_endpoint: '/api/locations',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'ID' },
          { db_name: 'name', display_name: 'Location Name' }
        ],
        input_fields: [
          { db_name: 'name', label: 'Location Name', type: 'text', required: true }
        ]
      },
      about: { api_endpoint: null, columns: [], input_fields: [] },
      support: { api_endpoint: null, columns: [], input_fields: [] }
    };

    // Generic API call function
    async function makeApiCall(method, endpoint, data = null) {
        showLoading(); // Show loading indicator
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(endpoint, options);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            return result;
        } catch (error) {
            console.error(`API Call Error (${method} ${endpoint}):`, error);
            showModal(`Error: ${error.message}`, 'alert');
            throw error; // Re-throw to allow calling functions to handle
        } finally {
            hideLoading(); // Hide loading indicator
        }
    }

    // Function to fetch and update dashboard stats
    async function fetchDashboardStats() {
        showLoading();
        try {
            const stats = await makeApiCall('GET', '/api/dashboard_stats');
            document.getElementById('total_customers').textContent = stats.total_customers;
            document.getElementById('total_drivers').textContent = stats.total_drivers;
            document.getElementById('total_vehicles').textContent = stats.total_vehicles;
            document.getElementById('ongoing_rides').textContent = stats.ongoing_rides;
            document.getElementById('vehicles_on_ride').textContent = stats.vehicles_on_ride;
            document.getElementById('drivers_on_ride').textContent = stats.drivers_on_ride;
            document.getElementById('total_bookings').textContent = stats.total_bookings;
            document.getElementById('pre_bookings').textContent = stats.pre_bookings;
            document.getElementById('revenue').textContent = `₹${stats.revenue.toFixed(2)}`;
            document.getElementById('payment_pendings').textContent = stats.payment_pendings;
        } catch (error) {
            console.error('Error fetching dashboard stats:', error);
            document.getElementById('total_customers').textContent = '-';
            document.getElementById('total_drivers').textContent = '-';
            document.getElementById('total_vehicles').textContent = '-';
            document.getElementById('ongoing_rides').textContent = '-';
            document.getElementById('vehicles_on_ride').textContent = '-';
            document.getElementById('drivers_on_ride').textContent = '-';
            document.getElementById('total_bookings').textContent = '-';
            document.getElementById('pre_bookings').textContent = '-';
            document.getElementById('revenue').textContent = '₹0.00';
            document.getElementById('payment_pendings').textContent = '-';
        } finally {
            hideLoading();
        }
    }

    // Function to fetch and render the revenue chart based on period
    async function fetchAndRenderRevenueChart(period = 'monthly') { // NEW: period parameter
        showLoading();
        try {
            // UPDATED API endpoint for revenue trend
            const data = await makeApiCall('GET', `/api/revenue_trend?period=${period}`);

            const labels = data.map(item => item.period_label);
            const revenues = data.map(item => item.revenue);

            const ctx = document.getElementById('revenueChart').getContext('2d');

            if (revenueChart) {
                revenueChart.destroy();
            }

            revenueChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: `Revenue (${period.charAt(0).toUpperCase() + period.slice(1)}) (₹)`, // Dynamic label
                        data: revenues,
                        backgroundColor: 'rgba(0, 119, 255, 0.4)',
                        borderColor: 'rgba(0, 119, 255, 1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(0, 119, 255, 1)',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 1,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Revenue (₹)',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                callback: function(value) {
                                    return '₹' + value;
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: `${period.charAt(0).toUpperCase() + period.slice(1)}`, // Dynamic X-axis label
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                font: {
                                    size: 14
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: `Revenue Trend (${period.charAt(0).toUpperCase() + period.slice(1)})`, // Dynamic chart title
                            font: {
                                size: 18,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        }
                    }
                }
            });
            // Set active class on the selected filter button
            document.querySelectorAll('.chart-filter-button').forEach(button => {
                button.classList.remove('active');
            });
            document.getElementById(`filter-${period}`).classList.add('active');

        } catch (error) {
            console.error('Error fetching or rendering revenue chart:', error);
            const ctx = document.getElementById('revenueChart').getContext('2d');
            if (revenueChart) {
                revenueChart.destroy();
            }
            ctx.font = "16px Arial";
            ctx.fillStyle = "red";
            ctx.textAlign = "center";
            ctx.fillText("Failed to load chart data.", ctx.canvas.width / 2, ctx.canvas.height / 2);
        } finally {
            hideLoading();
        }
    }

    async function loadSection(section) {
      // Destroy chart if navigating away from dashboard
      if (revenueChart) {
          revenueChart.destroy();
          revenueChart = null;
      }

      currentSection = section; // Set current section
      currentPage = 1; // Reset pagination

      if (section === 'dashboard') {
        main.innerHTML = `
          <div class="header">
            <h1>Dashboard</h1>
            <div class="filter-toggle">
              <button class="filter-icon" onclick="toggleFilterInput()">🔍</button>
              <input type="text" id="filterInput" placeholder="Search..." onkeyup="filterTable()" style="display: none;" />
            </div>
          </div>
          <section class="grid">
            <div class="card"><h3>Total Customers</h3><p id="total_customers">-</p></div>
            <div class="card"><h3>Total Drivers</h3><p id="total_drivers">-</p></div>
            <div class="card"><h3>Total Vehicles</h3><p id="total_vehicles">-</p></div>
            <div class="card"><h3>Ongoing rides</h3><p id="ongoing_rides">-</p></div>
            <div class="card"><h3>Vehicles on ride</h3><p id="vehicles_on_ride">-</p></div>
            <div class="card"><h3>Drivers on ride</h3><p id="drivers_on_ride">-</p></div>
            <div class="card"><h3>Total Bookings</h3><p id="total_bookings">-</p></div>
            <div class="card"><h3>Pre Bookings</h3><p id="pre_bookings">-</p></div>
            <div class="card"><h3>Revenue</h3><p id="revenue">₹0.00</p></div>
            <div class="card"><h3>Payment Pendings</h3><p id="payment_pendings">-</p></div>
          </section>
          <div class="chart-container">
            <div class="chart-filters"> <!-- NEW: Chart filter buttons -->
                <button id="filter-weekly" class="chart-filter-button" onclick="fetchAndRenderRevenueChart('weekly')">Weekly</button>
                <button id="filter-monthly" class="chart-filter-button active" onclick="fetchAndRenderRevenueChart('monthly')">Monthly</button>
                <button id="filter-yearly" class="chart-filter-button" onclick="fetchAndRenderRevenueChart('yearly')">Yearly</button>
            </div>
            <canvas id="revenueChart"></canvas>
          </div>
        `;
        await fetchDashboardStats();
        await fetchAndRenderRevenueChart('monthly'); // Initial render with monthly
        return;
      }

      if (section === 'sendMessage') {
      main.innerHTML = `
          <div class="header"><h1>Send Bulk Message</h1></div>
          <div class="content-box">
              <h3>Compose Message</h3>
              <textarea id="bulkMessage" rows="5" placeholder="Type your promotional message here..."></textarea>
              <div class="modal-buttons" style="text-align: left; margin-top: 10px;">
                  <button onclick="sendMessage('whatsapp')">Send via WhatsApp</button>
                  <button onclick="sendMessage('sms')" style="background: #f39c12;">Send via SMS (Simulated)</button>
              </div>
          </div>
          <div class="content-box" style="margin-top: 20px;">
              <h3>Select Recipients</h3>
              <div class="filter-toggle" style="justify-content: flex-end; margin-bottom: 10px;">
                  <input type="text" id="userFilterInput" placeholder="Filter users..." onkeyup="filterUserList()">
              </div>
              <table id="user-selection-table">
                  <thead>
                      <tr>
                          <th style="width: 50px;"><input type="checkbox" onclick="toggleSelectAll(this)"></th>
                          <th>Name</th>
                          <th>Phone</th>
                      </tr>
                  </thead>
                  <tbody id="user-list-tbody">
                      </tbody>
              </table>
          </div>
      `;
      // After setting the HTML, call a function to fetch and display the users
      loadSendMessageSection();
      return;
  }

      const config = sectionsConfig[section];
      if (!config) {
        main.innerHTML = `<div class='header'><h1>Coming Soon</h1></div>`;
        return;
      }

      // Handle manualBooking section separately as it's a form, not a table
      if (section === 'manualBooking') {
        const formInputsHtml = config.input_fields.map(field => {
          const validationClass = field.required ? 'required-field' : '';
          if (field.type === 'select') {
            const optionsHtml = field.options.map(option => `<option value="${option}">${option}</option>`).join('');
            return `<label>${field.label}:</label><select id="manual-${field.db_name}" data-db-name="${field.db_name}" class="${validationClass}" ${field.required ? 'required' : ''}>${optionsHtml}</select>`;
          } else {
            return `<label>${field.label}:</label><input type="${field.type}" id="manual-${field.db_name}" data-db-name="${field.db_name}" placeholder="${field.label}" class="${validationClass}" ${field.required ? 'required' : ''} ${field.step ? `step="${field.step}"` : ''}>`;
          }
        }).join('');

        main.innerHTML = `
          <div class='header'>
              <h1>Manual Ride Booking</h1>
          </div>
          <div class='content-box'>
            <div id='manual-booking-form' class='add-form'>
              <h3>Book a New Ride Manually</h3>
              ${formInputsHtml}
              <button onclick="addManualBooking()">Book Ride</button>
            </div>
          </div>
        `;
        return; // Exit after rendering manual booking form
      }


      // For table-based sections
      // Generate table headers with sorting
      const headersHtml = config.columns.map(col => `
        <th onclick="sortTable('${col.db_name}', '${section}')">
            ${col.display_name}
            <span class="sort-icon">${sortColumn === col.db_name ? (sortDirection === 'asc' ? '▲' : '▼') : ''}</span>
        </th>
      `).join('');

      // Generate input fields for the "Add" form (for regular CRUD sections)
      let addFormInputsHtml = '';
      if (config.input_fields && config.input_fields.length > 0) {
        addFormInputsHtml = config.input_fields.map(field => {
          // NEW: Add validation classes and required attribute
          const validationClass = field.required ? 'required-field' : '';
          if (field.type === 'select') {
            const optionsHtml = field.options.map(option => `<option value="${option}">${option}</option>`).join('');
            return `<label>${field.label}:</label><select data-db-name="${field.db_name}" class="${validationClass}" ${field.required ? 'required' : ''}>${optionsHtml}</select>`;
          } else {
            return `<label>${field.label}:</label><input type="${field.type}" data-db-name="${field.db_name}" placeholder="${field.label}" class="${validationClass}" ${field.required ? 'required' : ''} ${field.step ? `step="${field.step}"` : ''}>`;
          }
        }).join('');
      }

      main.innerHTML = `
        <div class='header'>
            <h1>${section.charAt(0).toUpperCase() + section.slice(1).replace(/([A-Z])/g, ' $1')}</h1>
            <div class="filter-toggle">
                <button class="filter-icon" onclick="toggleFilterInput()">🔍</button>
                <input type="text" id="filterInput" placeholder="Search..." onkeyup="filterTable()" style="display: none;" />
            </div>
        </div>
        <div class='content-box'>
          <div id='add-form' class='add-form'>
            <h3>Add New ${section.slice(0, -1).replace(/([A-Z])/g, ' $1')}</h3>
            ${addFormInputsHtml}
            <button onclick="addRow('${section}')">+ Add</button>
          </div>
          <div class="table-controls">
            <button onclick="exportTableToCSV('${section}')">Export to CSV</button>
          </div>
          <table>
            <thead><tr>${headersHtml}<th>Actions</th></tr></thead>
            <tbody id='${section}-table'></tbody>
          </table>
          <div id="pagination-controls" class="pagination-controls"></div>
        </div>`;

      // Fetch data and render table after HTML structure is in place
      const data = await fetchTableData(section);
      currentTableData = data; // Store fetched data for filtering/pagination
      renderTableRows(data, section); // Initial render
      setupPagination(data.length); // Setup pagination
    }

    // Add these new functions to the <script> block in index.html

async function loadSendMessageSection() {
    showLoading();
    try {
        const users = await makeApiCall('GET', '/api/customers');
        const userListTbody = document.getElementById('user-list-tbody');
        userListTbody.innerHTML = ''; // Clear previous list
        users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="checkbox" class="recipient-checkbox" value="${user.phone}"></td>
                <td>${user.name}</td>
                <td>${user.phone}</td>
            `;
            userListTbody.appendChild(row);
        });
    } catch (error) {
        console.error("Could not load user list:", error);
        showModal("Failed to load the user list.", 'alert');
    } finally {
        hideLoading();
    }
}

function filterUserList() {
    const filterText = document.getElementById('userFilterInput').value.toLowerCase();
    const rows = document.querySelectorAll('#user-list-tbody tr');
    rows.forEach(row => {
        const name = row.cells[1].textContent.toLowerCase();
        const phone = row.cells[2].textContent.toLowerCase();
        if (name.includes(filterText) || phone.includes(filterText)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.recipient-checkbox');
    checkboxes.forEach(cb => {
        const row = cb.closest('tr');
        // Only check visible checkboxes
        if (row.style.display !== 'none') {
            cb.checked = checkbox.checked;
        }
    });
}

async function sendMessage(method) {
    const message = document.getElementById('bulkMessage').value;
    if (!message.trim()) {
        showModal('Please type a message before sending.', 'alert');
        return;
    }

    const recipients = Array.from(document.querySelectorAll('.recipient-checkbox:checked')).map(cb => cb.value);
    if (recipients.length === 0) {
        showModal('Please select at least one recipient.', 'alert');
        return;
    }

    const confirmSend = await showModal(`You are about to send this message to ${recipients.length} user(s) via ${method}. Do you want to proceed?`, 'confirm');
    if (!confirmSend) {
        return;
    }

    try {
        const result = await makeApiCall('POST', '/api/send_bulk_message', {
            message,
            recipients,
            method
        });
        showModal(result.message, 'alert');
    } catch (error) {
        // Error is already handled by makeApiCall, but we can log it again if needed
        console.error("Failed to send bulk message:", error);
    }
}

    // Function to render table rows based on current page and filtered data
    function renderTableRows(data, section) {
        const tbody = document.getElementById(`${section}-table`);
        tbody.innerHTML = ''; // Clear current table rows
        const config = sectionsConfig[section];

        if (!data || data.length === 0) {
            const colspan = config.columns.length + 1; // +1 for actions column
            tbody.innerHTML = `<tr><td colspan="${colspan}">No data available.</td></tr>`;
            return;
        }

        const startIndex = (currentPage - 1) * ROWS_PER_PAGE;
        const endIndex = startIndex + ROWS_PER_PAGE;
        const paginatedData = data.slice(startIndex, endIndex);

        paginatedData.forEach(entry => {
            const row = document.createElement('tr');
            // Store the ID key on the row for easy access
            row.dataset.id = entry[config.id_key];

            // Map database fields to display columns
            row.innerHTML = config.columns.map(col => {
                let value = entry[col.db_name];
                // Special formatting for currency or boolean
                if (col.db_name === 'fare' || col.db_name === 'rate' || col.db_name === 'price_per_km') {
                    value = `₹${parseFloat(value).toFixed(2)}`;
                } else if (col.db_name === 'used') {
                    value = value === 1 ? 'Yes' : 'No';
                } else if (col.db_name === 'start_time' || col.db_name === 'end_time') {
                    value = value ? new Date(value).toLocaleString() : '-';
                } else if (col.db_name === 'last_latitude' || col.db_name === 'last_longitude') {
                    value = value !== undefined && value !== null ? parseFloat(value).toFixed(6) : '-';
                } else if (col.db_name === 'invoice_action') { // Handle invoice column
                    return `<td><button onclick="downloadInvoice(${entry.id})">Download Invoice</button></td>`;
                }
                return `<td data-label="${col.display_name}" data-db-name="${col.db_name}"><span>${value !== undefined && value !== null ? value : '-'}</span></td>`;
            }).join('');

            // Add action buttons
            row.innerHTML += `
            <td>
                <button class="edit-button" onclick="editRow(this, '${section}')">Edit</button>
                <button class="save-button" style="display:none;" onclick="saveRow(this, '${section}')">Save</button>
                <button class="delete-button" onclick="deleteRow(this, '${section}')">Delete</button>
            </td>`;
            tbody.appendChild(row);
        });
    }

    // Function to download invoice
    async function downloadInvoice(rideId) {
        showLoading();
        try {
            const response = await fetch(`/api/rides/${rideId}/invoice`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to download invoice: ${response.status} ${response.statusText} - ${errorText}`);
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `invoice_${rideId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showModal('Invoice downloaded successfully!', 'toast');
        } catch (error) {
            console.error('Error downloading invoice:', error);
            showModal(`Error downloading invoice: ${error.message}`, 'alert');
        } finally {
            hideLoading();
        }
    }


    async function addRow(section) {
      const config = sectionsConfig[section];
      const formInputs = document.querySelectorAll(`#add-form [data-db-name]`);
      const newData = {};
      let isValid = true;

      formInputs.forEach(input => {
        // NEW: Visual validation feedback
        if (input.hasAttribute('required') && input.value.trim() === '') {
          input.classList.add('input-error');
          isValid = false;
        } else {
          input.classList.remove('input-error');
        }

        let value = input.value.trim();
        if (input.type === 'number') {
            value = parseFloat(value);
            if (isNaN(value)) value = null; // Handle empty or invalid number input
        }
        newData[input.dataset.dbName] = value;
      });

      if (!isValid) {
        showModal('Please fill all required fields.', 'alert');
        return;
      }

      try {
        const result = await makeApiCall('POST', config.api_endpoint, newData);
        if (result.message) {
          showModal(result.message, 'toast'); // Show as toast
          loadSection(section); // Reload table to show new data
          // Clear form fields
          formInputs.forEach(input => {
              if (input.type === 'select') {
                  input.value = input.options[0].value; // Reset to first option
              } else {
                  input.value = '';
              }
              input.classList.remove('input-error'); // Clear error class
          });
        }
      } catch (error) {
        // Error handled by makeApiCall
      }
    }

    // Function for manual booking submission
    async function addManualBooking() {
        const formInputs = document.querySelectorAll(`#manual-booking-form [data-db-name]`);
        const bookingData = {};
        let isValid = true;

        formInputs.forEach(input => {
            if (input.hasAttribute('required') && input.value.trim() === '') {
                input.classList.add('input-error');
                isValid = false;
            } else {
                input.classList.remove('input-error');
            }
            bookingData[input.dataset.dbName] = input.value.trim();
        });

        if (!isValid) {
            showModal('Please fill all required fields for manual booking.', 'alert');
            return;
        }

        try {
            const result = await makeApiCall('POST', '/api/manual_booking', bookingData);
            if (result.message) {
                showModal(result.message, 'toast');
                // Optionally clear form or redirect after successful booking
                formInputs.forEach(input => {
                    if (input.type === 'select') {
                        input.value = input.options[0].value;
                    } else {
                        input.value = '';
                    }
                    input.classList.remove('input-error');
                });
            }
        } catch (error) {
            // Error handled by makeApiCall
        }
    }


    function editRow(button, section) {
      const row = button.closest('tr');
      const config = sectionsConfig[section];
      const cells = row.querySelectorAll('td[data-db-name]');

      cells.forEach(cell => {
        const dbName = cell.dataset.dbName;
        const columnConfig = config.input_fields.find(field => field.db_name === dbName);

        if (columnConfig && !columnConfig.exclude_from_edit) { // Only make editable if it's an input field
          const currentValueSpan = cell.querySelector('span');
          const currentValue = currentValueSpan ? currentValueSpan.textContent : ''; // Get current value from span
          let inputHtml = '';

          if (columnConfig.type === 'select') {
            const optionsHtml = columnConfig.options.map(option =>
              // Handle 'used' as 0/1 for value but 'No'/'Yes' for display
              `<option value="${option}" ${
                  (columnConfig.db_name === 'used' && ((currentValue === 'Yes' && option === '1') || (currentValue === 'No' && option === '0'))) ||
                  (currentValue.toLowerCase() === option.toLowerCase())
                  ? 'selected' : ''
              }>${option}</option>`
            ).join('');
            inputHtml = `<select data-db-name="${dbName}" class="${columnConfig.required ? 'required-field' : ''}">${optionsHtml}</select>`;
          } else {
            // Remove currency symbol for editing numbers
            const cleanValue = (columnConfig.type === 'number') ? currentValue.replace('₹', '').trim() : currentValue;
            inputHtml = `<input type="${columnConfig.type}" data-db-name="${dbName}" value="${cleanValue}" ${columnConfig.step ? `step="${columnConfig.step}"` : ''} class="${columnConfig.required ? 'required-field' : ''}">`;
          }
          cell.innerHTML = inputHtml;
        }
      });

      button.style.display = 'none';
      row.querySelector('.save-button').style.display = 'inline-block';
    }

    async function saveRow(button, section) {
      const row = button.closest('tr');
      const config = sectionsConfig[section];
      const id = row.dataset.id;
      const cells = row.querySelectorAll('td[data-db-name]');
      const updatedData = {};
      let isValid = true;

      cells.forEach(cell => {
        const input = cell.querySelector('input, select');
        if (input) {
            const dbName = input.dataset.dbName;
            const fieldConfig = config.input_fields.find(field => field.db_name === dbName);

            // NEW: Visual validation feedback
            if (fieldConfig && fieldConfig.required && input.value.trim() === '') {
                input.classList.add('input-error');
                isValid = false;
            } else {
                input.classList.remove('input-error');
            }

            let value = input.value.trim();
            if (input.type === 'number') {
                value = parseFloat(value);
                if (isNaN(value)) value = null;
            }
            updatedData[dbName] = value;
        }
      });

      if (!isValid) {
        showModal('Please fill all required fields.', 'alert');
        return;
      }

      try {
        const result = await makeApiCall('PUT', `${config.api_endpoint}/${id}`, updatedData);
        if (result.message) {
          showModal(result.message, 'toast'); // Show as toast
          loadSection(section); // Reload table to show updated data
        }
      } catch (error) {
        // Error handled by makeApiCall
      }
    }

    async function deleteRow(button, section) {
      const row = button.closest('tr');
      const config = sectionsConfig[section];
      const id = row.dataset.id;

      const confirmDelete = await showModal('Are you sure you want to delete this item?', 'confirm');
      if (!confirmDelete) {
          return;
      }

      try {
        const result = await makeApiCall('DELETE', `${config.api_endpoint}/${id}`);
        if (result.message) {
          showModal(result.message, 'toast'); // Show as toast
          loadSection(section); // Reload table to reflect deletion
        }
      } catch (error) {
        // Error handled by makeApiCall
      }
    }

    // --- NEW: Export to CSV Function ---
    function exportTableToCSV(section) {
        const config = sectionsConfig[section];
        if (!currentTableData || currentTableData.length === 0) {
            showModal('No data to export.', 'alert');
            return;
        }

        const headers = config.columns.map(col => col.display_name).join(',');
        const rows = currentTableData.map(row => {
            return config.columns.map(col => {
                let value = row[col.db_name];
                // Format values for CSV if needed
                if (col.db_name === 'fare' || col.db_name === 'rate' || col.db_name === 'price_per_km') {
                    value = parseFloat(value).toFixed(2);
                } else if (col.db_name === 'used') {
                    value = value === 1 ? 'Yes' : 'No';
                } else if (col.db_name === 'start_time' || col.db_name === 'end_time') {
                    value = value ? new Date(value).toLocaleString() : '';
                }
                return `"${String(value).replace(/"/g, '""')}"`; // Handle commas and quotes
            }).join(',');
        }).join('\n');

        const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(headers + '\n' + rows);
        const link = document.createElement('a');
        link.setAttribute('href', csvContent);
        link.setAttribute('download', `${section}_data.csv`);
        document.body.appendChild(link); // Required for Firefox
        link.click();
        document.body.removeChild(link); // Clean up
        showModal('Data exported successfully!', 'toast');
    }
    // In your user_portal.js or dashboard.js
    function initAutocomplete() {
    const pickupInput = document.getElementById('book-pickup');
    const autocomplete = new google.maps.places.Autocomplete(pickupInput, {
        componentRestrictions: { 'country': 'in' } // Bias to India
    });
    }
    // Call initAutocomplete() when the page/section loads.

    window.onload = () => loadSection('dashboard');
