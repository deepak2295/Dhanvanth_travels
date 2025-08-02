// static/user_portal.js

document.addEventListener('DOMContentLoaded', function() {
    // This runs after the entire page has loaded
    fetchUserDetails();
    setupEventListeners();
    // Set the initial tab correctly
    switchTab('booking');
});

function setupEventListeners() {
    const bookingForm = document.getElementById('userBookingForm');
    if (bookingForm) {
        bookingForm.addEventListener('submit', handleUserBooking);
    }
}

async function fetchUserDetails() {
    try {
        const response = await fetch('/api/user/details');
        const user = await response.json();

        if (response.ok) {
            const welcomeArea = document.getElementById('user-welcome');
            if (welcomeArea) {
                welcomeArea.textContent = `Welcome, ${user.name}!`;
            }

            if (user.requires_name_update) {
                const nameModal = document.getElementById('name-modal');
                if (nameModal) nameModal.style.display = 'flex';
            }
        } else {
            console.error('Failed to fetch user details:', user.error);
        }
    } catch (error) {
        console.error('Error fetching user details:', error);
    }

    const nameForm = document.getElementById('name-form');
    if (nameForm) {
        nameForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const newNameInput = document.getElementById('new-name');
            if (!newNameInput) return;

            const name = newNameInput.value;
            const response = await fetch('/api/user/update_name', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });

            if (response.ok) {
                const nameModal = document.getElementById('name-modal');
                if (nameModal) nameModal.style.display = 'none';
                fetchUserDetails(); // Refresh user details to show new name
            } else {
                alert('Failed to update name. Please try again.');
            }
        });
    }
}

function switchTab(tabName) {
    // Deactivate all tabs and content first
    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Activate the selected tab and content
    const tabButton = document.getElementById(`${tabName}-tab`);
    const tabContent = document.getElementById(`${tabName}-section`);

    if (tabButton) {
        tabButton.classList.add('active');
    } else {
        console.error(`Tab button with id '${tabName}-tab' not found.`);
    }

    if (tabContent) {
        tabContent.classList.add('active');
    } else {
        console.error(`Tab content with id '${tabName}-section' not found.`);
    }

    // If switching to the 'history' tab, fetch the ride history
    if (tabName === 'history') {
        fetchRideHistory();
    }
}

async function fetchRideHistory() {
    try {
        const response = await fetch('/api/user/rides');
        const rides = await response.json();
        const historyBody = document.getElementById('ride-history-body');

        if (!historyBody) return;

        historyBody.innerHTML = ''; // Clear previous entries

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
                <td>₹${ride.fare.toFixed(2)}</td>
                <td>${ride.status}</td>
                <td>${new Date(ride.start_time).toLocaleString()}</td>
            `;
            historyBody.appendChild(row);
        });
    } catch (error) {
        console.error('Failed to fetch ride history:', error);
    }
}

// In static/user_portal.js

// REPLACE your old handleUserBooking function with this one
async function handleUserBooking(event) {
    event.preventDefault();
    const messageArea = document.getElementById('booking-message');
    const paymentOptions = document.getElementById('payment-options');
    if (!messageArea || !paymentOptions) return;

    const bookingData = {
        pickup: document.getElementById('book-pickup').value,
        destination: document.getElementById('book-destination').value,
        booking_date: document.getElementById('book-date').value,
        booking_time: document.getElementById('book-time').value,
        car_type: document.getElementById('book-car-type').value,
    };

    messageArea.textContent = 'Booking your ride...';
    messageArea.style.color = '#333';
    paymentOptions.style.display = 'none'; // Hide old options

    try {
        const response = await fetch('/api/user/book_ride', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bookingData)
        });

        const result = await response.json();

        if (response.ok) {
            // Booking was successful, now show payment options
            messageArea.textContent = result.message;
            messageArea.style.color = 'green';
            event.target.reset(); // Clear the form

            paymentOptions.style.display = 'block'; // Show the payment buttons

            const payOnlineBtn = document.getElementById('pay-online-btn');
            const payCashBtn = document.getElementById('pay-cash-btn');

            // Handle "Pay Online" click
            payOnlineBtn.onclick = () => {
                if (result.payment_link) {
                    window.open(result.payment_link, '_blank'); // Open Razorpay link in a new tab
                }
            };

            // Handle "Pay with Cash" click
            payCashBtn.onclick = () => {
                setPaymentToCash(result.ride_id);
                paymentOptions.style.display = 'none';
                messageArea.textContent = 'Great! You can pay the driver with cash at the end of your ride.';
                messageArea.style.color = '#3498db';
            };

        } else {
            // Booking failed (e.g., location outside Bengaluru)
            messageArea.textContent = `Error: ${result.error}`;
            messageArea.style.color = 'red';
        }
    } catch (error) {
        messageArea.textContent = 'A network error occurred. Please try again.';
        messageArea.style.color = 'red';
        console.error('Booking failed:', error);
    }
}

// ADD this new helper function to user_portal.js
async function setPaymentToCash(rideId) {
    try {
        await fetch(`/api/user/rides/${rideId}/set_cash`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Failed to set payment method to cash:', error);
    }
}
function logout() {
    fetch('/api/user/logout', { method: 'POST' })
        .then(response => {
            if (response.ok) {
                // Redirect to the login page after a successful logout
                window.location.href = '/login';
            } else {
                alert('Logout failed. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error during logout:', error);
            alert('An error occurred during logout.');
        });
}

function initAutocomplete() {
  const pickupInput = document.getElementById('book-pickup');
  const autocomplete = new google.maps.places.Autocomplete(pickupInput, {
    componentRestrictions: { 'country': 'in' } // Bias to India
  });
}
