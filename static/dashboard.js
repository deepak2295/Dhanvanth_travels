const main = document.getElementById('main-content');
    const sidebar = document.getElementById('sidebar');
    let revenueChart = null; 


    const customModal = document.getElementById('customModal');
    const modalMessage = document.getElementById('modalMessage');
    const modalConfirmBtn = document.getElementById('modalConfirmBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');
    const modalOkBtn = document.getElementById('modalOkBtn');
    let modalResolve = null; 

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
            modalOkBtn.style.display = 'inline-block'; 
            modalOkBtn.onclick = () => { hideModal(); modalResolve(true); };
            setTimeout(() => {
                if (customModal.style.display === 'block' && modalMessage.textContent === message) {
                    hideModal();
                    if (modalResolve) resolve(true); 
                }
            }, 3000); 
        }

        return new Promise(resolve => {
            modalResolve = resolve;
        });
    }

    function hideModal() {
        customModal.style.display = 'none';
    }

    window.onclick = function(event) {
        if (event.target == customModal) {
            hideModal();
            if (modalResolve) modalResolve(false); 
        }
    }

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


    function toggleSidebar() {
      sidebar.classList.toggle('active');
    }

    async function selectSection(section) {
      await loadSection(section); 
      if (window.innerWidth <= 768) sidebar.classList.remove('active');
    }

    let currentTableData = []; 
    let currentSection = ''; 

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

        tbody.innerHTML = ''; 

        const filteredData = currentTableData.filter(row => {
            return config.columns.some(col => {
                const value = String(row[col.db_name]).toLowerCase();
                return value.includes(filterText);
            });
        });

        renderTableRows(filteredData, currentSection); 
        updatePagination(filteredData.length); 
    }

    let sortColumn = null;
    let sortDirection = 'asc'; 

    function sortTable(columnName, section) {
        const config = sectionsConfig[section];
        const columnConfig = config.columns.find(col => col.db_name === columnName);

        if (!columnConfig) return; 

        if (sortColumn === columnName) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortColumn = columnName;
            sortDirection = 'asc';
        }

        currentTableData.sort((a, b) => {
            let valA = a[columnName];
            let valB = b[columnName];

            if (typeof valA === 'number' && typeof valB === 'number') {
                return sortDirection === 'asc' ? valA - valB : valB - valA;
            }
            valA = String(valA).toLowerCase();
            valB = String(valB).toLowerCase();
            if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        renderTableRows(currentTableData, section); 
        updatePagination(currentTableData.length); 
    }

    const ROWS_PER_PAGE = 10;
    let currentPage = 1;

    function setupPagination(totalRows) {
        const paginationContainer = document.getElementById('pagination-controls');
        if (!paginationContainer) return;

        paginationContainer.innerHTML = '';
        const totalPages = Math.ceil(totalRows / ROWS_PER_PAGE);

        if (totalPages <= 1) return; 

        const prevButton = document.createElement('button');
        prevButton.textContent = 'Previous';
        prevButton.disabled = currentPage === 1;
        prevButton.onclick = () => {
            if (currentPage > 1) {
                currentPage--;
                renderTableRows(currentTableData, currentSection);
                updatePagination(totalRows);
            }
            filterTable();
        };
        paginationContainer.appendChild(prevButton);

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
                filterTable();
            };
            paginationContainer.appendChild(pageButton);
        }

        const nextButton = document.createElement('button');
        nextButton.textContent = 'Next';
        nextButton.disabled = currentPage === totalPages;
        nextButton.onclick = () => {
            if (currentPage < totalPages) {
                currentPage++;
                renderTableRows(currentTableData, currentSection);
                updatePagination(totalRows);
            }
    
            filterTable();
        };
        paginationContainer.appendChild(nextButton);
    }

    function updatePagination(totalRows) {
        setupPagination(totalRows);
        renderTableRows(currentTableData, currentSection); 
    }

    async function fetchTableData(section) {
        const config = sectionsConfig[section];
        if (!config || !config.api_endpoint) {
            console.warn(`No API endpoint configured for section: ${section}`);
            return [];
        }
        try {
            const data = await makeApiCall('GET', config.api_endpoint);
            currentTableData = data;
            return data;
        } catch (error) {
            console.error(`Error fetching data for ${section}:`, error);
            return [];
        }
    }

 


const sectionsConfig = {
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
    customers: {
        api_endpoint: '/api/customers',
        id_key: 'id',
        columns: [
          { db_name: 'id', display_name: 'ID' },
          { db_name: 'name', display_name: 'Name' },
          { db_name: 'email', display_name: 'Email' },
          { db_name: 'phone', display_name: 'Phone' }
        ],
         input_fields: [
            { db_name: 'name', label: 'Name', type: 'text', required: true },
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
          { db_name: 'car_number', display_name: 'Assigned Car Number' },
          { db_name: 'status', display_name: 'Status' },
          { db_name: 'last_latitude', display_name: 'Last Lat' },
          { db_name: 'last_longitude', display_name: 'Last Lng' }
        ],
        input_fields: [
          { db_name: 'name', label: 'Driver Name', type: 'text', required: true },
          { db_name: 'phone', label: 'Phone', type: 'text', required: true },
          { db_name: 'status', label: 'Status', type: 'select', options: ['free', 'busy'], required: true },
          { db_name: 'last_latitude', label: 'Last Latitude', type: 'number', step: 'any', required: false },
          { db_name: 'last_longitude', label: 'Last Longitude', type: 'number', step: 'any', required: false },
          {
            db_name: 'car_id',
            label: 'Assigned Car',
            type: 'dynamic-select',
            required: false,
            options_endpoint: '/api/vehicles',
            option_value: 'id',
            option_text: 'car_number'
            }
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
     pricing: {
        api_endpoint: '/api/pricing',
        id_key: 'id',
        columns: [
            { db_name: 'id', display_name: 'ID' },
            { db_name: 'vehicle_type', display_name: 'Vehicle Type' },
            { db_name: 'price_per_km', display_name: 'Price / km (₹)' }
        ],
        input_fields: [
            { db_name: 'vehicle_type', label: 'Vehicle Type', type: 'select', options: ['sedan', 'suv', 'compact', 'luxury', 'auto'], required: true },
            { db_name: 'price_per_km', label: 'Price per km (₹)', type: 'number', step: '0.01', required: true }
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
          { db_name: 'invoice_action', display_name: 'Invoice' }
        ],
        input_fields: [
          { db_name: 'user_phone', label: 'Customer Phone', type: 'text', required: true },
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
    assigned: {
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
        input_fields: []
    },
    coupons: {
        api_endpoint: '/api/coupons',
        id_key: 'code',
        columns: [
          { db_name: 'code', display_name: 'Coupon Code' },
          { db_name: 'discount', display_name: 'Discount (%)' },
          { db_name: 'used', display_name: 'Used' }
        ],
        input_fields: [
          { db_name: 'code', label: 'Coupon Code', type: 'text', required: true },
          { db_name: 'discount', label: 'Discount (%)', type: 'number', step: '0.01', required: true },
          { db_name: 'used', label: 'Used', type: 'select', options: ['0', '1'], required: true }
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

     async function makeApiCall(method, endpoint, data = null) {
    showLoading(); 
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin' 
    };
    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, options);

        if (response.redirected) {
            window.location.href = response.url;
            return;
        }
        
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || `HTTP error! status: ${response.status}`);
        }
        return result;
    } catch (error) {
        console.error(`API Call Error (${method} ${endpoint}):`, error);
        showModal(`Error: ${error.message}`, 'alert');
        throw error; 
    } finally {
        hideLoading(); 
    }
}
    

async function fetchDashboardStats() {
    console.log("Attempting to fetch dashboard stats...");
    showLoading();
    try {
        const stats = await makeApiCall('GET', '/api/dashboard_stats');
        console.log("Successfully received stats:", stats);

        
        const revenueValue = parseFloat(stats.revenue || 0);

        document.getElementById('total_customers').textContent = stats.total_customers;
        document.getElementById('total_drivers').textContent = stats.total_drivers;
        document.getElementById('total_vehicles').textContent = stats.total_vehicles;
        document.getElementById('ongoing_rides').textContent = stats.ongoing_rides;
        document.getElementById('vehicles_on_ride').textContent = stats.vehicles_on_ride;
        document.getElementById('drivers_on_ride').textContent = stats.drivers_on_ride;
        document.getElementById('total_bookings').textContent = stats.total_bookings;
        document.getElementById('pre_bookings').textContent = stats.pre_bookings;
        
        document.getElementById('revenue').textContent = `₹${revenueValue.toFixed(2)}`;
        
        document.getElementById('payment_pendings').textContent = stats.payment_pendings;

    } catch (error) {
        console.error('CRITICAL: Error fetching dashboard stats inside the catch block.');
        console.error(error); 

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
    async function fetchAndRenderRevenueChart(period = 'monthly') { 
        showLoading();
        try {
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
      if (revenueChart) {
          revenueChart.destroy();
          revenueChart = null;
      }

      currentSection = section; 
      currentPage = 1; 

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
        await fetchAndRenderRevenueChart('monthly'); 
        return;
      }
      if (section === 'assignment') {
        main.innerHTML = `
            <div class="header">
                <h1>Ride Assignments</h1>
                <div class="filter-toggle">
                    <span>Auto-Assignment</span>
                    <label class="switch">
                        <input type="checkbox" id="auto-assign-toggle">
                        <span class="slider round"></span>
                    </label>
                </div>
            </div>
            <div id="assignment-list" class="content-box">
                <!-- Unassigned rides will be loaded here -->
            </div>
        `;
        const style = document.createElement('style');
        style.innerHTML = `.switch{position:relative;display:inline-block;width:60px;height:34px;margin-left:10px}.switch input{opacity:0;width:0;height:0}.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:#ccc;transition:.4s}.slider:before{position:absolute;content:"";height:26px;width:26px;left:4px;bottom:4px;background-color:white;transition:.4s}input:checked+.slider{background-color:var(--primary)}input:checked+.slider:before{transform:translateX(26px)}.slider.round{border-radius:34px}.slider.round:before{border-radius:50%}`;
        document.head.appendChild(style);

        loadAssignmentSection();
        fetch('/get_assignment_mode')
            .then(res => res.json())
            .then(data => {
                document.getElementById('auto-assign-toggle').checked = (data.mode === 'auto');
            });

            document.getElementById('auto-assign-toggle').addEventListener('change', function() {
            const mode = this.checked ? 'auto' : 'manual';
            fetch('/set_assignment_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            })
            .then(res => res.json())
            .then(data => {
                alert(`Assignment mode changed to: ${data.mode}`);
            });
        });
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
      loadSendMessageSection();
      return;
  }

      const config = sectionsConfig[section];
      if (!config) {
        main.innerHTML = `<div class='header'><h1>Coming Soon</h1></div>`;
        return;
      }

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
        return; 
      }


     
      const headersHtml = config.columns.map(col => `
        <th onclick="sortTable('${col.db_name}', '${section}')">
            ${col.display_name}
            <span class="sort-icon">${sortColumn === col.db_name ? (sortDirection === 'asc' ? '▲' : '▼') : ''}</span>
        </th>
      `).join('');

      let addFormInputsHtml = '';
      if (config.input_fields && config.input_fields.length > 0) {
        addFormInputsHtml = config.input_fields.map(field => {
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

      const data = await fetchTableData(section);
      currentTableData = data; 
      renderTableRows(data, section); 
      setupPagination(data.length); 
    }


async function loadSendMessageSection() {
    showLoading();
    try {
        const users = await makeApiCall('GET', '/api/customers');
        const userListTbody = document.getElementById('user-list-tbody');
        userListTbody.innerHTML = ''; 
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
        console.error("Failed to send bulk message:", error);
    }
}

    function renderTableRows(data, section) {
    const tbody = document.getElementById(`${section}-table`);
    tbody.innerHTML = ''; // Clear any existing rows
    const config = sectionsConfig[section];

    if (!data || data.length === 0) {
        const colspan = config.columns.length + 1; 
        tbody.innerHTML = `<tr><td colspan="${colspan}">No data available.</td></tr>`;
        return;
    }

    const startIndex = (currentPage - 1) * ROWS_PER_PAGE;
    const endIndex = startIndex + ROWS_PER_PAGE;
    const paginatedData = data.slice(startIndex, endIndex);

    paginatedData.forEach(entry => {
        const row = document.createElement('tr');
        row.dataset.id = entry[config.id_key]; 

        const cellsHtml = config.columns.map(col => {
            const dbName = col.db_name;
            let value = entry[dbName];
            let cellContent = '';

            switch (dbName) {
                case 'fare':
                case 'rate':
                case 'price_per_km':
                    cellContent = `₹${parseFloat(value).toFixed(2)}`;
                    break;
                case 'used':
                    cellContent = value === 1 ? 'Yes' : 'No';
                    break;
                case 'start_time':
                case 'end_time':
                    cellContent = value ? new Date(value).toLocaleString() : '-';
                    break;
                case 'invoice_action':
                    return `<td><button onclick="downloadInvoice(${entry.id})">Download Invoice</button></td>`;
                default:
                    cellContent = value != null ? value : '-';
                    break;
            }
            return `<td data-label="${col.display_name}" data-db-name="${dbName}"><span>${cellContent}</span></td>`;
        }).join('');

        const actionsHtml = `
            <td>
                <button class="edit-button" onclick="editRow(this, '${section}')">Edit</button>
                <button class="save-button" style="display:none;" onclick="saveRow(this, '${section}')">Save</button>
                <button class="delete-button" onclick="deleteRow(this, '${section}')">Delete</button>
            </td>`;

        row.innerHTML = cellsHtml + actionsHtml;
        tbody.appendChild(row);
    });
}


    async function addRow(section) {
      const config = sectionsConfig[section];
      const formInputs = document.querySelectorAll(`#add-form [data-db-name]`);
      const newData = {};
      let isValid = true;

      formInputs.forEach(input => {
        if (input.hasAttribute('required') && input.value.trim() === '') {
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
        newData[input.dataset.dbName] = value;
      });

      if (!isValid) {
        showModal('Please fill all required fields.', 'alert');
        return;
      }

      try {
        const result = await makeApiCall('POST', config.api_endpoint, newData);
        if (result.message) {
          showModal(result.message, 'toast'); 
          loadSection(section); 
         
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
        
      }
    }

  
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
        }
    }



async function editRow(button, section) {
    const row = button.closest('tr');
    const config = sectionsConfig[section];
    const cells = row.querySelectorAll('td[data-db-name]');
    const originalData = currentTableData.find(item => String(item[config.id_key]) === String(row.dataset.id));

    row.style.opacity = '0.5';

    for (const cell of cells) {
        const dbName = cell.dataset.dbName;

      
        const effectiveDbName = (dbName === 'car_number') ? 'car_id' : dbName;
        const columnConfig = config.input_fields.find(field => field.db_name === effectiveDbName);
       
        
        if (columnConfig && !columnConfig.exclude_from_edit) {
            const currentValue = originalData[effectiveDbName]; 
            let inputHtml = '';

            if (columnConfig.type === 'dynamic-select') {
                try {
                    const optionsData = await makeApiCall('GET', columnConfig.options_endpoint);
                    inputHtml = `<select data-db-name="${effectiveDbName}">`;
                    inputHtml += `<option value="">-- Unassigned --</option>`;

                    optionsData.forEach(option => {
                        const value = option[columnConfig.option_value];
                        const text = option[columnConfig.option_text];
                        const isSelected = value == currentValue ? 'selected' : '';
                        inputHtml += `<option value="${value}" ${isSelected}>${text}</option>`;
                    });
                    inputHtml += `</select>`;
                } catch (error) {
                    console.error(`Failed to load options for ${dbName}:`, error);
                    inputHtml = '<span>Error loading options.</span>';
                }
            } else if (columnConfig.type === 'select') {
                const optionsHtml = columnConfig.options.map(option =>
                    `<option value="${option}" ${String(currentValue).toLowerCase() === String(option).toLowerCase() ? 'selected' : ''}>${option}</option>`
                ).join('');
                inputHtml = `<select data-db-name="${effectiveDbName}">${optionsHtml}</select>`;
            } else {
                const cleanValue = (columnConfig.type === 'number' && currentValue !== null) ? String(currentValue).replace('₹', '').trim() : (currentValue || '');
                inputHtml = `<input type="${columnConfig.type}" data-db-name="${effectiveDbName}" value="${cleanValue}" ${columnConfig.step ? `step="${columnConfig.step}"` : ''}>`;
            }
            cell.innerHTML = inputHtml;
        }
    }

    row.style.opacity = '1';
    button.style.display = 'none';
    row.querySelector('.save-button').style.display = 'inline-block';
}


async function saveRow(button, section) {
    const row = button.closest('tr');
    const config = sectionsConfig[section];
    const id = row.dataset.id;
    let isValid = true;

  
    const originalData = currentTableData.find(item => String(item[config.id_key]) === String(id));
    

    const updatedData = { ...originalData };
 

    const cells = row.querySelectorAll('td[data-db-name]');

    cells.forEach(cell => {
        const input = cell.querySelector('input, select');
        if (input) { 
            const dbName = input.dataset.dbName;
            const fieldConfig = config.input_fields.find(field => field.db_name === dbName);

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
            showModal(result.message, 'toast');
            loadSection(section); 
        }
    } catch (error) {
       
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
          showModal(result.message, 'toast'); 
          loadSection(section);
        }
      } catch (error) {
        
      }
    }

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
    async function safeFetchJson(url, options = {}) {
    const res = await fetch(url, options);
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
        throw new Error("Not logged in or received HTML instead of JSON");
    }
    return await res.json();
}

async function makeApiCall(method, url, data = null) {
    const options = { 
        method, 
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
    };
    if (data) options.body = JSON.stringify(data);

    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
        showModal("Session expired. Please log in again.", "alert");
        window.location.href = "/login";
        return null; 
    }
    
    const result = await response.json();
    if (!response.ok) {
        showModal(result.error || `HTTP error! status: ${response.status}`, 'alert');
        throw new Error(result.error);
    }
    return result;
}

async function loadAssignmentSection() {
    showLoading();
    try {
        const statusRes = await makeApiCall('GET', '/api/assignment/status');
        const toggle = document.getElementById('auto-assign-toggle');
        toggle.checked = statusRes.auto_assignment_enabled;
        toggle.onchange = toggleAutoAssignment; 

        const [rides, drivers, cars] = await Promise.all([
            makeApiCall('GET', '/api/unassigned_rides'),
            makeApiCall('GET', '/api/available_drivers'),
            makeApiCall('GET', '/api/available_cars')
        ]);

        renderAssignmentList(rides, drivers, cars);

    } catch (error) {
        console.error("Failed to load assignment section:", error);
        document.getElementById('assignment-list').innerHTML = `<p style="color:red;">Error loading assignments.</p>`;
    } finally {
        hideLoading();
    }
}

async function toggleAutoAssignment() {
    const toggle = document.getElementById('auto-assign-toggle');
    try {
        const result = await makeApiCall('POST', '/api/assignment/toggle', { enabled: toggle.checked });
        showModal(result.message, 'toast');
    } catch (error) {
        console.error("Failed to toggle auto-assignment:", error);
        toggle.checked = !toggle.checked; 
    }
}



function renderAssignmentList(rides, drivers, cars) {
    const container = document.getElementById('assignment-list');
    if (rides.length === 0) {
        container.innerHTML = '<p>No rides are currently waiting for assignment.</p>';
        return;
    }

    container.innerHTML = rides.map(ride => {
        const requiredCarType = ride.car_type || 'any';
        const userRequestedModel = ride.car_model; 

        let carRequirementText = '';
        if (userRequestedModel) {
            carRequirementText = `${requiredCarType.toUpperCase()} (User Requested: <b>${userRequestedModel}</b>)`;
        } else {
            carRequirementText = requiredCarType.toUpperCase();
        }

        const filteredCars = cars.filter(car => car.type.toLowerCase() === requiredCarType.toLowerCase());

        const driverOptions = drivers.map(d => `<option value="${d.id}">${d.name} (${d.phone})</option>`).join('');
        const carOptions = filteredCars.map(c => `<option value="${c.id}">${c.model} (${c.car_number})</option>`).join('');

        return `
            <div class="assignment-card" style="border:1px solid #ddd; border-radius:8px; padding:15px; margin-bottom:15px;">
                <h4>Ride ID: ${ride.id} (For: ${ride.customer_name || ride.user_phone})</h4>
                <p><strong>Route:</strong> ${ride.pickup} to ${ride.destination}</p>
                <p><strong>Time:</strong> ${new Date(ride.start_time).toLocaleString()}</p>
                <p><strong>Required Car:</strong> ${carRequirementText}</p>
                <div style="display:flex; gap:10px; margin-top:10px;">
                    <select id="driver-for-${ride.id}" style="width:50%;">
                        <option value="">Select a Driver...</option>
                        ${driverOptions}
                    </select>
                    <select id="car-for-${ride.id}" style="width:50%;">
                        <option value="">Select a Car...</option>
                        ${carOptions}
                    </select>
                    <button onclick="confirmManualAssignment(${ride.id})">Confirm</button>
                </div>
            </div>
        `;
    }).join('');
}

async function confirmManualAssignment(rideId) {
    const driverId = document.getElementById(`driver-for-${rideId}`).value;
    const carId = document.getElementById(`car-for-${rideId}`).value;

    if (!driverId || !carId) {
        showModal('You must select both a driver and a car.', 'alert');
        return;
    }

    try {
        const result = await makeApiCall('POST', '/api/assign_ride_manually', {
            ride_id: rideId,
            driver_id: driverId,
            car_id: carId
        });
        showModal(result.message, 'toast');
        loadAssignmentSection(); // Refresh the list
    } catch (error) {
        console.error("Manual assignment failed:", error);
    }
}

fetch('/api/drivers')
  .then(res => res.json())
  .then(drivers => {
    const driverSelect = document.getElementById('driverSelect');
    drivers.forEach(driver => {
      const opt = document.createElement('option');
      opt.value = driver.id;
      opt.textContent = `${driver.name} (${driver.car_id ? "Car " + driver.car_id : "No Car"})`;
      if (driver.is_fixed === 1) {
        opt.textContent += " 🔒";
        opt.disabled = true;
      }
      driverSelect.appendChild(opt);
    });
  });

 
async function logout() {
    try {
        const response = await fetch('/api/user/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin' 
        });

        const result = await response.json();

        if (response.ok) {
            await showModal('You have been logged out successfully.', 'toast');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500); 
        } else {
            await showModal(result.error || 'Logout failed. Please try again.', 'alert');
        }
    } catch (error) {
        console.error('Error during logout:', error);
        await showModal('An error occurred during logout.', 'alert');
    }
}

async function saveSiteContent(key) {
    const content = document.getElementById('site-content-editor').value;
    try {
        const result = await makeApiCall('POST', '/api/site_content', { key: key, value: content });
        showModal(result.message, 'toast');
    } catch (error) {
        console.error('Failed to save site content:', error);
    }
}

async function loadSection(section) {
    if (revenueChart) {
        revenueChart.destroy();
        revenueChart = null;
    }

    currentSection = section; 
    currentPage = 1; 

    if (section === 'about' || section === 'support') {
        const contentKey = (section === 'about') ? 'about_us_content' : 'support_content';
        const title = (section === 'about') ? 'About Us' : 'Support / Contact Us';

        main.innerHTML = `
            <div class="header"><h1>Edit ${title} Content</h1></div>
            <div class="content-box">
                <p>Enter the content below. It will be displayed on the user portal. You can use multiple lines.</p>
                <textarea id="site-content-editor" rows="15" style="width: 100%; font-size: 16px; padding: 10px; margin-top: 10px;" placeholder="Enter content here..."></textarea>
                <div style="text-align: right; margin-top: 15px;">
                    <button onclick="saveSiteContent('${contentKey}')">Save Content</button>
                </div>
            </div>
        `;

        try {
            showLoading();
            const response = await makeApiCall('GET', `/api/site_content/${contentKey}`);
            document.getElementById('site-content-editor').value = response.value;
        } catch (error) {
            document.getElementById('site-content-editor').value = 'Could not load content.';
        } finally {
            hideLoading();
        }
        return; // Exit the function here
    }
    
    
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
            <div class="chart-filters"> <button id="filter-weekly" class="chart-filter-button" onclick="fetchAndRenderRevenueChart('weekly')">Weekly</button>
                <button id="filter-monthly" class="chart-filter-button active" onclick="fetchAndRenderRevenueChart('monthly')">Monthly</button>
                <button id="filter-yearly" class="chart-filter-button" onclick="fetchAndRenderRevenueChart('yearly')">Yearly</button>
            </div>
            <canvas id="revenueChart"></canvas>
          </div>
        `;
        await fetchDashboardStats();
        await fetchAndRenderRevenueChart('monthly'); 
        return;
      }
      if (section === 'assignment') {
        main.innerHTML = `
            <div class="header">
                <h1>Ride Assignments</h1>
                <div class="filter-toggle">
                    <span>Auto-Assignment</span>
                    <label class="switch">
                        <input type="checkbox" id="auto-assign-toggle">
                        <span class="slider round"></span>
                    </label>
                </div>
            </div>
            <div id="assignment-list" class="content-box">
                </div>
        `;
        const style = document.createElement('style');
        style.innerHTML = `.switch{position:relative;display:inline-block;width:60px;height:34px;margin-left:10px}.switch input{opacity:0;width:0;height:0}.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background-color:#ccc;transition:.4s}.slider:before{position:absolute;content:"";height:26px;width:26px;left:4px;bottom:4px;background-color:white;transition:.4s}input:checked+.slider{background-color:var(--primary)}input:checked+.slider:before{transform:translateX(26px)}.slider.round{border-radius:34px}.slider.round:before{border-radius:50%}`;
        document.head.appendChild(style);

        loadAssignmentSection();
        fetch('/get_assignment_mode')
            .then(res => res.json())
            .then(data => {
                document.getElementById('auto-assign-toggle').checked = (data.mode === 'auto');
            });

            document.getElementById('auto-assign-toggle').addEventListener('change', function() {
            const mode = this.checked ? 'auto' : 'manual';
            fetch('/set_assignment_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            })
            .then(res => res.json())
            .then(data => {
                alert(`Assignment mode changed to: ${data.mode}`);
            });
        });
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
      
      loadSendMessageSection();
      return;
  }

      const config = sectionsConfig[section];
      if (!config) {
        main.innerHTML = `<div class='header'><h1>Coming Soon</h1></div>`;
        return;
      }

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
        return;
    }


      const headersHtml = config.columns.map(col => `
        <th onclick="sortTable('${col.db_name}', '${section}')">
            ${col.display_name}
            <span class="sort-icon">${sortColumn === col.db_name ? (sortDirection === 'asc' ? '▲' : '▼') : ''}</span>
        </th>
      `).join('');

      let addFormInputsHtml = '';
      if (config.input_fields && config.input_fields.length > 0) {
        addFormInputsHtml = config.input_fields.map(field => {
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

      const data = await fetchTableData(section);
      currentTableData = data; 
      renderTableRows(data, section);
      setupPagination(data.length);
}


function downloadInvoice(rideId) {
 
  window.open(`/api/rides/${rideId}/invoice`, '_blank');
}



   

window.onload = () => loadSection('dashboard');