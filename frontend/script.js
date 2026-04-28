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
        const response = await fetch('http://localhost:8000/analyze', {
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

function showError(message) {
    const errorMsg = document.getElementById('error-message');
    errorMsg.textContent = message;
    errorMsg.classList.remove('hidden');
}
