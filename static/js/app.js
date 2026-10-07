// Global State
let currentTxData = null;
let selectedVerifyRef = null;

document.addEventListener('DOMContentLoaded', () => {
    generateRandomRef();
    loadTransactions();
    loadSystemStatus();
    loadStats();
});

function generateRandomRef() {
    const num = Math.floor(10000 + Math.random() * 90000);
    document.getElementById('txRef').value = `TXN-${num}`;
}

function updateHourDisplay(val) {
    const formatted = String(val).padStart(2, '0');
    document.getElementById('hourLabel').textContent = `${formatted}:00 HRS`;
}

function applyPreset(presetType) {
    generateRandomRef();
    if (presetType === 'legit') {
        document.getElementById('txAmount').value = 450;
        document.getElementById('txType').value = 'PAYMENT';
        document.getElementById('txOrigBalance').value = 18500;
        document.getElementById('txDestBalance').value = 0;
        document.getElementById('txHour').value = 11;
        updateHourDisplay(11);
        document.getElementById('flagLocation').checked = false;
        document.getElementById('flagVelocity').checked = false;
    } else if (presetType === 'drain') {
        document.getElementById('txAmount').value = 92000;
        document.getElementById('txType').value = 'TRANSFER';
        document.getElementById('txOrigBalance').value = 92500;
        document.getElementById('txDestBalance').value = 1200;
        document.getElementById('txHour').value = 3;
        updateHourDisplay(3);
        document.getElementById('flagLocation').checked = true;
        document.getElementById('flagVelocity').checked = true;
    } else if (presetType === 'suspicious') {
        document.getElementById('txAmount').value = 28500;
        document.getElementById('txType').value = 'CASH_OUT';
        document.getElementById('txOrigBalance').value = 32000;
        document.getElementById('txDestBalance').value = 250;
        document.getElementById('txHour').value = 23;
        updateHourDisplay(23);
        document.getElementById('flagLocation').checked = true;
        document.getElementById('flagVelocity').checked = false;
    }
}

async function handleTransactionSubmit(event) {
    event.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const spinner = document.getElementById('submitSpinner');
    submitBtn.disabled = true;
    spinner.classList.remove('d-none');

    const payload = {
        transaction_ref: document.getElementById('txRef').value,
        amount: parseFloat(document.getElementById('txAmount').value),
        transaction_type: document.getElementById('txType').value,
        orig_balance: parseFloat(document.getElementById('txOrigBalance').value),
        dest_balance: parseFloat(document.getElementById('txDestBalance').value),
        hour_of_day: parseInt(document.getElementById('txHour').value),
        risk_flag_unusual_location: document.getElementById('flagLocation').checked ? 1 : 0,
        risk_flag_high_velocity: document.getElementById('flagVelocity').checked ? 1 : 0
    };

    try {
        const response = await fetch('/api/predict-and-audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Failed to analyze and audit transaction');
            return;
        }

        currentTxData = data;
        displayAuditResults(data);
        loadTransactions();
        loadStats();
    } catch (err) {
        console.error(err);
        alert('Network or server error occurred while processing transaction.');
    } finally {
        submitBtn.disabled = false;
        spinner.classList.add('d-none');
    }
}

function displayAuditResults(data) {
    document.getElementById('resultsPlaceholder').classList.add('d-none');
    const content = document.getElementById('resultsContent');
    content.classList.remove('d-none');

    const riskPercent = data.prediction.risk_percentage;
    const category = data.prediction.risk_category;

    // 1. Animate Circular SVG Gauge
    const circle = document.getElementById('gaugeCircle');
    const percentText = document.getElementById('gaugePercentText');
    const circumference = 440; // 2 * pi * 70
    const offset = circumference - (circumference * (riskPercent / 100));

    circle.style.strokeDashoffset = offset;
    percentText.textContent = `${riskPercent.toFixed(1)}%`;

    // 2. Set Gauge Color & Classification Badge
    const badge = document.getElementById('riskBadgeElement');
    const icon = document.getElementById('riskBadgeIcon');
    const categoryText = document.getElementById('riskCategoryText');

    badge.className = 'badge-risk';
    if (category === 'High Risk') {
        circle.style.stroke = '#f43f5e';
        badge.classList.add('high');
        icon.className = 'fa-solid fa-triangle-exclamation';
        categoryText.textContent = 'HIGH RISK (FRAUDULENT)';
    } else if (category === 'Medium Risk') {
        circle.style.stroke = '#f59e0b';
        badge.classList.add('medium');
        icon.className = 'fa-solid fa-flag';
        categoryText.textContent = 'MEDIUM RISK (SUSPICIOUS)';
    } else {
        circle.style.stroke = '#10b981';
        badge.classList.add('low');
        icon.className = 'fa-solid fa-shield-check';
        categoryText.textContent = 'LOW RISK (LEGITIMATE)';
    }

    // 3. Contributing Risk Factors
    const factorContainer = document.getElementById('factorListContainer');
    factorContainer.innerHTML = '';
    data.prediction.contributing_factors.forEach(factor => {
        const div = document.createElement('div');
        div.className = 'p-2 rounded font-mono text-white-50 bg-black bg-opacity-25 border border-secondary border-opacity-25 small d-flex align-items-center gap-2';
        div.style.fontSize = '0.75rem';
        div.innerHTML = `<i class="fa-solid fa-angle-right text-cyan"></i> <span>${factor}</span>`;
        factorContainer.appendChild(div);
    });

    // 4. SHA-256 Digest
    document.getElementById('resultHashBox').textContent = data.audit.audit_hash;

    // 5. Blockchain Receipt
    const txHash = data.blockchain.tx_hash || '';
    document.getElementById('receiptTxHash').textContent = txHash ? `${txHash.substring(0, 16)}...${txHash.substring(56)}` : '0x...';
    document.getElementById('receiptNetwork').textContent = data.blockchain.network || 'Simulated EVM';
    document.getElementById('receiptContract').textContent = data.blockchain.contract_address || '-';
}

function copyResultHash() {
    const hash = document.getElementById('resultHashBox').textContent.trim();
    if (hash && hash !== '-') {
        navigator.clipboard.writeText(hash).then(() => {
            alert('SHA-256 hash copied to clipboard!');
        });
    }
}

function switchToVerifyTab() {
    if (!currentTxData) return;
    const tabBtn = document.getElementById('tab-verify');
    bootstrap.Tab.getInstance(tabBtn)?.show() || new bootstrap.Tab(tabBtn).show();
    
    const select = document.getElementById('verifyRefSelect');
    select.value = currentTxData.transaction.transaction_ref;
    loadVerificationDetails(currentTxData.transaction.transaction_ref);
}

async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions');
        const transactions = await response.json();

        const tbody = document.getElementById('ledgerTableBody');
        const select = document.getElementById('verifyRefSelect');
        const currentSelected = select.value;

        tbody.innerHTML = '';
        select.innerHTML = '<option value="">-- Choose Transaction --</option>';

        if (transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center py-5 text-secondary">No transactions recorded yet. Submit one from the New Transaction tab!</td></tr>';
            return;
        }

        transactions.forEach(tx => {
            // Add to dropdown
            const opt = document.createElement('option');
            opt.value = tx.transaction_ref;
            opt.textContent = `${tx.transaction_ref} (₹${parseFloat(tx.amount).toLocaleString('en-IN')}) - ${tx.prediction}`;
            select.appendChild(opt);

            // Add to table
            const tr = document.createElement('tr');
            
            // Risk pill styling
            let riskPill = '';
            if (tx.risk_category === 'High Risk' || tx.prediction === 'Fraudulent') {
                riskPill = `<span class="badge bg-danger-subtle text-danger border border-danger-subtle font-mono">HIGH RISK (${(tx.risk_score * 100).toFixed(0)}%)</span>`;
            } else if (tx.risk_category === 'Medium Risk') {
                riskPill = `<span class="badge bg-warning-subtle text-warning border border-warning-subtle font-mono">MED RISK (${(tx.risk_score * 100).toFixed(0)}%)</span>`;
            } else {
                riskPill = `<span class="badge bg-success-subtle text-success border border-success-subtle font-mono">LOW RISK (${(tx.risk_score * 100).toFixed(0)}%)</span>`;
            }

            // Tamper status
            const integrityPill = tx.is_tampered 
                ? '<span class="badge bg-danger text-white border border-danger font-mono"><i class="fa-solid fa-triangle-exclamation me-1"></i>TAMPERED</span>' 
                : '<span class="badge bg-success-subtle text-success border border-success-subtle font-mono"><i class="fa-solid fa-check me-1"></i>INTACT</span>';

            tr.innerHTML = `
                <td class="font-mono fw-bold text-cyan">${tx.transaction_ref}</td>
                <td class="font-mono fw-semibold">₹${parseFloat(tx.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                <td><span class="badge bg-dark border border-secondary text-secondary font-mono">${tx.transaction_type}</span></td>
                <td>${riskPill}</td>
                <td class="font-mono text-secondary small" title="${tx.audit_hash}">
                    ${tx.audit_hash.substring(0, 10)}...${tx.audit_hash.substring(54)}
                </td>
                <td class="font-mono small text-secondary">
                    ${tx.blockchain_tx_hash ? tx.blockchain_tx_hash.substring(0, 10) + '...' : '-'}
                </td>
                <td>${integrityPill}</td>
                <td class="text-end">
                    <button class="btn btn-outline-info btn-sm rounded-pill font-mono px-3 py-1" onclick="inspectInLab('${tx.transaction_ref}')">
                        <i class="fa-solid fa-microscope me-1"></i> Verify
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (currentSelected) {
            select.value = currentSelected;
        }
    } catch (err) {
        console.error('Failed to load transactions:', err);
    }
}

function inspectInLab(ref) {
    const tabBtn = document.getElementById('tab-verify');
    bootstrap.Tab.getInstance(tabBtn)?.show() || new bootstrap.Tab(tabBtn).show();
    document.getElementById('verifyRefSelect').value = ref;
    loadVerificationDetails(ref);
}

async function loadVerificationDetails(ref) {
    selectedVerifyRef = ref;
    if (!ref) {
        clearVerificationLab();
        return;
    }

    try {
        const response = await fetch(`/api/transactions/${ref}`);
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Failed to load details');
            return;
        }

        const tx = data.transaction;
        const chain = data.blockchain_record;

        // Populate Local DB Card
        document.getElementById('labTxRef').textContent = tx.transaction_ref;
        document.getElementById('labAmount').textContent = `₹${parseFloat(tx.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('labType').textContent = tx.transaction_type;
        document.getElementById('labPrediction').textContent = tx.prediction;
        document.getElementById('labCategory').textContent = tx.risk_category;
        document.getElementById('labScore').textContent = `${(tx.risk_score * 100).toFixed(1)}%`;
        document.getElementById('labTime').textContent = tx.timestamp;
        document.getElementById('labCurrentHash').textContent = data.current_calculated_hash;

        // DB Tamper badge & button state
        const dbBadge = document.getElementById('dbTamperBadge');
        const restoreBtn = document.getElementById('restoreBtn');
        if (tx.is_tampered) {
            dbBadge.className = 'badge bg-danger text-white border border-danger font-mono';
            dbBadge.innerHTML = '<i class="fa-solid fa-triangle-exclamation me-1"></i>ALTERED (TAMPERED)';
            restoreBtn.classList.remove('d-none');
        } else {
            dbBadge.className = 'badge bg-success-subtle text-success border border-success-subtle font-mono';
            dbBadge.innerHTML = '<i class="fa-solid fa-circle-check me-1"></i>UNMODIFIED';
            restoreBtn.classList.add('d-none');
        }

        // Populate Blockchain Card
        document.getElementById('chainNetwork').textContent = chain?.network || 'Simulated Ethereum Sepolia Ledger';
        document.getElementById('chainContract').textContent = chain?.contract_address || '-';
        document.getElementById('chainTxHash').textContent = chain?.tx_hash || tx.blockchain_tx_hash || '-';
        document.getElementById('chainTime').textContent = chain?.timestamp ? new Date(chain.timestamp * 1000).toLocaleString() : tx.timestamp;
        document.getElementById('labChainHash').textContent = chain?.audit_hash || tx.audit_hash;

        // Execute verification immediately for live status banner
        triggerVerify();
    } catch (err) {
        console.error(err);
    }
}

async function triggerVerify() {
    if (!selectedVerifyRef) {
        alert('Please select a transaction reference first');
        return;
    }

    try {
        const response = await fetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transaction_ref: selectedVerifyRef })
        });

        const data = await response.json();
        const banner = document.getElementById('verificationBanner');
        const icon = document.getElementById('verifyBannerIcon');
        const title = document.getElementById('verifyBannerTitle');
        const msg = document.getElementById('verifyBannerMsg');

        banner.classList.remove('d-none');
        banner.className = 'audit-banner mb-4';

        if (data.verified) {
            banner.classList.add('verified');
            icon.innerHTML = '<i class="fa-solid fa-circle-check text-success"></i>';
            title.textContent = 'CRYPTOGRAPHIC VERIFICATION PASSED (INTEGRITY CONFIRMED)';
            msg.textContent = `The SHA-256 fingerprint generated from local database records precisely matches the immutable on-chain hash (${data.stored_hash.substring(0, 16)}...). Zero record tampering detected.`;
        } else {
            banner.classList.add('tampered');
            icon.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-danger"></i>';
            title.textContent = 'INTEGRITY VIOLATION DETECTED: CRYPTOGRAPHIC MISMATCH!';
            msg.textContent = `Calculated local hash (${data.calculated_hash ? data.calculated_hash.substring(0, 16) : ''}...) does NOT match immutable blockchain hash (${data.stored_hash ? data.stored_hash.substring(0, 16) : ''}...). Unauthorized tampering has occurred in the database!`;
        }
    } catch (err) {
        console.error(err);
    }
}

async function triggerTamper() {
    if (!selectedVerifyRef) {
        alert('Please select a transaction reference first');
        return;
    }

    try {
        const response = await fetch('/api/tamper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transaction_ref: selectedVerifyRef })
        });

        const data = await response.json();
        if (response.ok) {
            loadVerificationDetails(selectedVerifyRef);
            loadTransactions();
            loadStats();
        } else {
            alert(data.error || 'Failed to tamper record');
        }
    } catch (err) {
        console.error(err);
    }
}

async function triggerRestore() {
    if (!selectedVerifyRef) return;

    try {
        const response = await fetch('/api/reset-tamper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transaction_ref: selectedVerifyRef })
        });

        const data = await response.json();
        if (response.ok) {
            loadVerificationDetails(selectedVerifyRef);
            loadTransactions();
            loadStats();
        } else {
            alert(data.error || 'Failed to restore record');
        }
    } catch (err) {
        console.error(err);
    }
}

function clearVerificationLab() {
    document.getElementById('labTxRef').textContent = '-';
    document.getElementById('labAmount').textContent = '-';
    document.getElementById('labType').textContent = '-';
    document.getElementById('labPrediction').textContent = '-';
    document.getElementById('labCategory').textContent = '-';
    document.getElementById('labScore').textContent = '-';
    document.getElementById('labTime').textContent = '-';
    document.getElementById('labCurrentHash').textContent = '-';
    document.getElementById('chainNetwork').textContent = '-';
    document.getElementById('chainContract').textContent = '-';
    document.getElementById('chainTxHash').textContent = '-';
    document.getElementById('chainTime').textContent = '-';
    document.getElementById('labChainHash').textContent = '-';
    document.getElementById('verificationBanner').classList.add('d-none');
    document.getElementById('restoreBtn').classList.add('d-none');
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-total').textContent = data.total_transactions;
        document.getElementById('stat-legit').textContent = data.legitimate_count;
        document.getElementById('stat-fraud').textContent = data.fraudulent_count;
        document.getElementById('stat-tampered').textContent = data.tampered_count;
    } catch (err) {
        console.error(err);
    }
}

async function loadSystemStatus() {
    try {
        const res = await fetch('/api/system-status');
        const data = await res.json();
        document.getElementById('headerNetworkLabel').textContent = data.blockchain.mode;
    } catch (err) {
        console.error(err);
    }
}
