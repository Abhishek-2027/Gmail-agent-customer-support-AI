// Initialize History on load
document.addEventListener('DOMContentLoaded', () => {
    updateHistoryUI();
});

document.getElementById('analyze-btn').addEventListener('click', async () => {
    const emailText = document.getElementById('email-input').value.trim();
    if (!emailText) {
        showError("Please enter an email to analyze.");
        return;
    }

    // UI States
    const btn = document.getElementById('analyze-btn');
    const spinner = document.getElementById('loading-spinner');
    const btnText = document.getElementById('btn-text');
    const errorMsg = document.getElementById('error-message');
    const outputSection = document.getElementById('output-section');

    btn.disabled = true;
    spinner.classList.remove('hidden');
    errorMsg.classList.add('hidden');
    outputSection.classList.add('hidden');

    // Animate status messages so user knows it's working
    const steps = ['Detecting language...', 'Classifying intent...', 'Retrieving policies...', 'Generating reply...'];
    let stepIdx = 0;
    btnText.textContent = steps[0];
    const stepTimer = setInterval(() => {
        stepIdx = (stepIdx + 1) % steps.length;
        btnText.textContent = steps[stepIdx];
    }, 2500);

    // 90 second timeout (free LLMs can be slow)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90000);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: emailText }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Something went wrong on the server.');
        }

        const data = await response.json();
        
        // Save to History
        saveToHistory(emailText, data);
        
        displayResults(data);

    } catch (error) {
        if (error.name === 'AbortError') {
            showError('Request timed out (90s). The AI server may be overloaded — please try again in a moment.');
        } else {
            showError(error.message);
        }
    } finally {
        clearInterval(stepTimer);
        btn.disabled = false;
        spinner.classList.add('hidden');
        btnText.textContent = 'Analyze Email';
    }
});


function displayResults(data) {
    const outputSection = document.getElementById('output-section');
    outputSection.classList.remove('hidden');

    // Intent
    const intentEl = document.getElementById('out-intent');
    intentEl.textContent = data.intent.replace('_', ' ');
    intentEl.className = 'badge'; // reset
    if (data.intent === 'unknown') {
        intentEl.classList.add('bg-unknown');
    } else {
        intentEl.classList.add('bg-intent');
    }

    // Urgency
    const urgencyEl = document.getElementById('out-urgency');
    urgencyEl.textContent = data.urgency;
    urgencyEl.className = 'badge'; // reset
    urgencyEl.classList.add(`bg-${data.urgency}`);

    // Confidence
    const confFill = document.getElementById('conf-fill');
    const confText = document.getElementById('out-conf-text');
    const confPercentage = Math.round(data.confidence * 100);
    confFill.style.width = `${confPercentage}%`;
    
    // Change color based on confidence
    if (data.confidence < 0.5) {
        confFill.style.backgroundColor = 'var(--urgency-high)';
    } else if (data.confidence < 0.8) {
        confFill.style.backgroundColor = 'var(--urgency-medium)';
    } else {
        confFill.style.backgroundColor = 'var(--urgency-low)';
    }
    
    confText.textContent = `${confPercentage}% Confident`;

    // Visual Order Card
    const orderContainer = document.getElementById('order-card-container');
    if (data.order_details) {
        const order = data.order_details;
        const statusClass = order.status.toLowerCase().includes('delivered') ? 'status-delivered' : 
                          order.status.toLowerCase().includes('transit') ? 'status-transit' : 'status-processing';
        
        orderContainer.innerHTML = `
            <div class="order-card">
                <div class="order-header">
                    <span class="order-id">Order ${order.order_id}</span>
                    <span class="order-status-pill ${statusClass}">${order.status}</span>
                </div>
                <div class="order-details-grid">
                    <div>
                        <div class="detail-label">Items</div>
                        <div>${order.items.join(', ')}</div>
                    </div>
                    <div>
                        <div class="detail-label">Tracking</div>
                        <div>${order.tracking_number}</div>
                    </div>
                    <div>
                        <div class="detail-label">Customer</div>
                        <div>${order.customer_email}</div>
                    </div>
                    <div>
                        <div class="detail-label">Update</div>
                        <div>${order.delivery_date || order.estimated_delivery || 'N/A'}</div>
                    </div>
                </div>
            </div>
        `;
        orderContainer.classList.remove('hidden');
    } else {
        orderContainer.classList.add('hidden');
    }

    // Text areas
    document.getElementById('out-reasoning').textContent = data.reasoning;
    
    const replyEl = document.getElementById('out-reply');
    replyEl.textContent = data.suggested_reply;
    
    // Simple check for Arabic to set text direction
    const arabicRegex = /[\u0600-\u06FF]/;
    if (arabicRegex.test(data.suggested_reply)) {
        replyEl.style.direction = 'rtl';
    } else {
        replyEl.style.direction = 'ltr';
    }
}

// Copy to Clipboard
document.getElementById('copy-btn').addEventListener('click', () => {
    const text = document.getElementById('out-reply').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy Reply', 2000);
    });
});

// History Logic
function saveToHistory(text, data) {
    const history = JSON.parse(localStorage.getItem('cs_history') || '[]');
    const newItem = {
        id: Date.now(),
        preview: text.substring(0, 40) + '...',
        intent: data.intent,
        urgency: data.urgency,
        fullText: text,
        results: data,
        timestamp: new Date().toLocaleTimeString()
    };
    history.unshift(newItem);
    localStorage.setItem('cs_history', JSON.stringify(history.slice(0, 10))); // keep 10
    updateHistoryUI();
}

function updateHistoryUI() {
    const history = JSON.parse(localStorage.getItem('cs_history') || '[]');
    const list = document.getElementById('history-list');
    
    if (history.length === 0) return;

    list.innerHTML = history.map(item => `
        <div class="history-item" onclick="loadFromHistory(${item.id})">
            <div>${item.preview}</div>
            <div class="history-meta">
                <span>${item.intent}</span>
                <span>${item.timestamp}</span>
            </div>
        </div>
    `).join('');
}

window.loadFromHistory = (id) => {
    const history = JSON.parse(localStorage.getItem('cs_history') || '[]');
    const item = history.find(i => i.id === id);
    if (item) {
        document.getElementById('email-input').value = item.fullText;
        displayResults(item.results);
    }
};

function showError(message) {
    const errorMsg = document.getElementById('error-message');
    errorMsg.textContent = message;
    errorMsg.classList.remove('hidden');
}
