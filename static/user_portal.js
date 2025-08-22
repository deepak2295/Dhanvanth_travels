
let siteContent = null;
document.addEventListener('DOMContentLoaded', function() {
    setupTabListeners();
    setupFormListeners();
    addSuggestionButtons();
    fetchSiteContent();
    fetchUserDetails(); 
    populateCarTypes();
});



function setupTabListeners() {
    document.getElementById('booking-tab').addEventListener('click', () => switchTab('booking'));
    document.getElementById('history-tab').addEventListener('click', () => switchTab('history'));
    document.getElementById('about-tab').addEventListener('click', () => switchTab('about'));
    document.getElementById('contact-tab').addEventListener('click', () => switchTab('contact'));
}


function setupFormListeners() {
    document.getElementById('userBookingForm').addEventListener('submit', handleUserBooking);
    document.getElementById('name-form').addEventListener('submit', handleNameUpdate);
}


async function fetchUserDetails() {
    try {
        const response = await fetch('/api/user/details');
        const user = await response.json();
        if (!response.ok) throw new Error(user.error);

        document.getElementById('user-welcome').textContent = `Welcome, ${user.name}!`;

        if (user.requires_name_update) {
            document.getElementById('name-modal').style.display = 'flex';
        } else {
            switchTab('booking');
        }
    } catch (error) {
        console.error('Error fetching user details:', error);
    }
}

async function handleNameUpdate(event) {
    event.preventDefault();
    const name = document.getElementById('new-name').value;
    try {
        const response = await fetch('/api/user/update_name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!response.ok) throw new Error('Failed to update name');

        document.getElementById('name-modal').style.display = 'none';
        document.getElementById('user-welcome').textContent = `Welcome, ${name}!`;
        switchTab('booking'); 
    } catch (error) {
        console.error('Error updating name:', error);
        alert('Failed to update name. Please try again.');
    }
}


async function handleUserBooking(event) {
    event.preventDefault();
    const messageArea = document.getElementById('booking-message');
    const paymentOptions = document.getElementById('payment-options');

    const bookingData = {
        pickup: document.getElementById('book-pickup').value,
        destination: document.getElementById('book-destination').value,
        booking_date: document.getElementById('book-date').value,
        booking_time: document.getElementById('book-time').value,
        car_type: document.getElementById('book-car-type').value,
    };

    messageArea.textContent = 'Booking your ride...';
    messageArea.style.color = '#333';
    paymentOptions.style.display = 'none';

    try {
        const result = await makeUserPortalApiCall('POST', '/api/user/book_ride', bookingData);

        messageArea.textContent = result.message;
        messageArea.style.color = 'green';
        event.target.reset();
        paymentOptions.style.display = 'block';

        document.getElementById('pay-online-btn').onclick = () => {
            if (result.payment_link) window.open(result.payment_link, '_blank');
        };
        document.getElementById('pay-cash-btn').onclick = () => {
            setPaymentToCash(result.ride_id);
            paymentOptions.style.display = 'none';
            messageArea.textContent = 'Great! You can pay the driver with cash.';
            messageArea.style.color = '#3498db';
        };
    } catch (error) {
        messageArea.textContent = `Error: ${error.message}`;
        messageArea.style.color = 'red';
    }
}


 
async function switchTab(tabName) {
    document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    document.getElementById(`${tabName}-tab`).classList.add('active');
    document.getElementById(`${tabName}-section`).classList.add('active');

    if (tabName === 'history') {
        fetchRideHistory();
    } 
    else if (tabName === 'about' || tabName === 'contact') {
        const content = await fetchSiteContent();
        const aboutSection = document.getElementById('about-section');
        const contactSection = document.getElementById('contact-section');
        
        if (tabName === 'about' && !aboutSection.dataset.loaded) {
            aboutSection.innerHTML = `<h2>About Us</h2><p>${content.about_us.replace(/\n/g, '<br>')}</p>`;
            aboutSection.dataset.loaded = 'true';
        }

        if (tabName === 'contact' && !contactSection.dataset.loaded) {
            contactSection.innerHTML = `<h2>Contact Us</h2><p>${content.contact_us.replace(/\n/g, '<br>')}</p>`;
            contactSection.dataset.loaded = 'true';
        }
    }
}

async function fetchRideHistory() {
    const historyBody = document.getElementById('ride-history-body');
    try {
        const response = await fetch('/api/user/rides');
        const rides = await response.json();
        if (!response.ok) throw new Error('Failed to fetch rides');

        historyBody.innerHTML = '';
        if (rides.length === 0) {
            historyBody.innerHTML = '<tr><td colspan="6">You have no past rides.</td></tr>';
            return;
        }
        rides.forEach(ride => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${ride.id}</td>
                <td>${ride.pickup}</td>
                <td>${ride.destination}</td>
                <td>₹${ride.fare ? ride.fare.toFixed(2) : '0.00'}</td>
                <td>${ride.status}</td>
                <td>${ride.start_time ? new Date(ride.start_time).toLocaleString() : 'N/A'}</td>
            `;
            historyBody.appendChild(row);
        });
    } catch (error) {
        historyBody.innerHTML = `<tr><td colspan="6">Could not load ride history.</td></tr>`;
    }
}


async function fetchSiteContent() {
    if (siteContent) return siteContent;
    try {
        const response = await fetch('/api/public/site_content');
        if (!response.ok) throw new Error('Failed to fetch site content');
        siteContent = await response.json();
        return siteContent;
    } catch (error) {
        console.error(error);
        return { about_us: 'Could not load content.', contact_us: 'Could not load content.' };
    }
}

// --- Utility Functions ---

async function setPaymentToCash(rideId) {
    try {
        await fetch(`/api/user/rides/${rideId}/set_cash`, { method: 'POST' });
    } catch (error) {
        console.error('Failed to set payment method to cash:', error);
    }
}

function logout() {
    fetch('/api/user/logout', { method: 'POST' })
        .then(() => window.location.href = '/login')
        .catch(error => console.error('Error during logout:', error));
}

let suggestionAdded = false;
function addSuggestionButtons() {
    if (suggestionAdded) return;
    suggestionAdded = true;

    const pickupInput = document.getElementById('book-pickup');
    const destinationInput = document.getElementById('book-destination');
    const suggestions = ['Majestic Bus Stand', 'Bangalore Airport', 'Koramangala'];

    const createSuggestionHtml = (targetInputId) => {
        return suggestions.map(s => 
            `<button type="button" class="suggestion-btn" onclick="document.getElementById('${targetInputId}').value='${s}';">${s}</button>`
        ).join('');
    };

    let pickupSuggestionDiv = pickupInput.parentElement.querySelector('.suggestion-container');
    if (!pickupSuggestionDiv) {
        pickupSuggestionDiv = document.createElement('div');
        pickupSuggestionDiv.className = 'suggestion-container';
        pickupInput.parentElement.appendChild(pickupSuggestionDiv);
    }
    pickupSuggestionDiv.innerHTML = createSuggestionHtml('book-pickup');

    let destSuggestionDiv = destinationInput.parentElement.querySelector('.suggestion-container');
    if (!destSuggestionDiv) {
        destSuggestionDiv = document.createElement('div');
        destSuggestionDiv.className = 'suggestion-container';
        destinationInput.parentElement.appendChild(destSuggestionDiv);
    }
    destSuggestionDiv.innerHTML = createSuggestionHtml('book-destination');
}

function initAutocomplete() {
    const pickupInput = document.getElementById('book-pickup');
    const destinationInput = document.getElementById('book-destination');

    const karnatakaBounds = new google.maps.LatLngBounds(
        new google.maps.LatLng(11.5, 74.0),
        new google.maps.LatLng(18.5, 78.5)
    );
    const options = {
        bounds: karnatakaBounds,
        strictBounds: true,
        componentRestrictions: { country: 'in' },
        types: ['geocode']
    };

    new google.maps.places.Autocomplete(pickupInput, options);
    new google.maps.places.Autocomplete(destinationInput, options);
}

async function populateCarTypes() {
    const carTypeSelect = document.getElementById('book-car-type');
    if (!carTypeSelect) return;

    try {
        const response = await fetch('/api/public/car_types');
        const carTypes = await response.json();
        if (!response.ok) throw new Error('API Error');

        carTypeSelect.innerHTML = '';

        if (carTypes.length === 0) {
            carTypeSelect.innerHTML = '<option value="">No cars available</option>';
        } else {
            carTypes.forEach(type => {
                const option = document.createElement('option');
                option.value = type.toLowerCase();
                option.textContent = type.charAt(0).toUpperCase() + type.slice(1);
                carTypeSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error populating car types:', error);
        carTypeSelect.innerHTML = '<option value="">Error loading types</option>';
    }
}


async function makeUserPortalApiCall(method, endpoint, body) {
    const options = {
        method: method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(endpoint, options);

    if (response.redirected) {
        alert("Your session has expired. Please log in again.");
        window.location.href = response.url;
        throw new Error("Session expired"); 
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
        throw new Error("Received non-JSON response from server. Check for server errors.");
    }

    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.error || 'An unknown API error occurred.');
    }

    return result;
}