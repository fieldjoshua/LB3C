/* 
Production JavaScript for Real-Time LED Controls

TODOs:
  - Fetch /api/files for uploaded assets
  - Connect to Socket.IO for play/stop/parameter events
  - Render preview grid so settings can be tuned before sending to device
  - Bind GUI controls to API/WebSocket endpoints
*/

// Global state
const state = {
    socket: null,
    connected: false,
    currentFile: null,
    isPlaying: false,
    files: [],
    playlist: [],
    previewCanvas: null,
    previewCtx: null,
    automations: {},
    currentAutomation: null
};

// Initialize Socket.IO connection
function initializeSocket() {
    state.socket = io();
    
    state.socket.on('connect', () => {
        console.log('Connected to server');
        state.connected = true;
        updateConnectionStatus(true);
        loadFileList();
        loadAutomations();
        loadStatus();
    });
    
    state.socket.on('disconnect', () => {
        console.log('Disconnected from server');
        state.connected = false;
        updateConnectionStatus(false);
    });
    
    state.socket.on('error', (data) => {
        showError(data.message);
    });
    
    state.socket.on('playing', (data) => {
        state.isPlaying = true;
        if (data.type === 'file') {
            state.currentFile = data.filename;
        } else if (data.type === 'automation') {
            state.currentAutomation = data.automation;
        }
        updatePlaybackControls();
    });
    
    state.socket.on('stopped', () => {
        state.isPlaying = false;
        updatePlaybackControls();
    });
    
    state.socket.on('frame_info', (data) => {
        updateFrameInfo(data.current_frame, data.total_frames);
    });
    
    state.socket.on('parameter_updated', (data) => {
        console.log(`Parameter updated: ${data.parameter} = ${data.value}`);
    });
    
    state.socket.on('device_switched', (data) => {
        showSuccess(`Switched to ${data.device_type}`);
        loadStatus();
    });
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.className = 'badge bg-success me-3';
        statusEl.innerHTML = '<i class="fas fa-circle"></i> Connected';
    } else {
        statusEl.className = 'badge bg-danger me-3';
        statusEl.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
    }
}

// Show/hide HUB75 settings based on device type
function updateDeviceSettings(deviceType) {
    const hub75Settings = document.getElementById('hub75-settings');
    if (deviceType === 'HUB75') {
        hub75Settings.style.display = 'block';
    } else {
        hub75Settings.style.display = 'none';
    }
}

// Load file list from server
async function loadFileList() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        state.files = data.files;
        renderFileList();
    } catch (error) {
        console.error('Failed to load files:', error);
    }
}

// Load available automations
async function loadAutomations() {
    try {
        const response = await fetch('/api/automations');
        const data = await response.json();
        state.automations = data;
        renderAutomationList();
    } catch (error) {
        console.error('Failed to load automations:', error);
    }
}

// Load current status
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Update device selector
        if (data.device_type) {
            document.getElementById('device-selector').value = data.device_type;
            updateDeviceSettings(data.device_type);
        }
        
        // Update parameters
        if (data.parameters) {
            document.getElementById('brightness-slider').value = data.parameters.brightness;
            document.getElementById('speed-slider').value = data.parameters.speed;
            document.getElementById('gamma-slider').value = data.parameters.gamma;
            
            updateSliderValues();
        }
        
        // Update playback state
        state.isPlaying = data.is_playing;
        state.currentFile = data.current_file;
        updatePlaybackControls();
        
    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

// Render file list
function renderFileList() {
    const listEl = document.getElementById('file-list');
    listEl.innerHTML = '';
    
    state.files.forEach(file => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        if (file.name === state.currentFile) {
            item.classList.add('active');
        }
        
        item.innerHTML = `
            <div>
                <i class="fas fa-file-video me-2"></i>
                ${file.name}
            </div>
            <div>
                <button class="btn btn-sm btn-primary play-btn" data-file="${file.name}">
                    <i class="fas fa-play"></i>
                </button>
                <button class="btn btn-sm btn-secondary add-playlist-btn" data-file="${file.name}">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
        `;
        
        listEl.appendChild(item);
    });
    
    // Bind click handlers
    document.querySelectorAll('.play-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            playFile(btn.dataset.file);
        });
    });
    
    document.querySelectorAll('.add-playlist-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            addToPlaylist(btn.dataset.file);
        });
    });
}

// Render automation list
function renderAutomationList() {
    const selectEl = document.getElementById('automation-select');
    selectEl.innerHTML = '<option value="">-- Choose Automation --</option>';
    
    Object.entries(state.automations).forEach(([key, info]) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = info.description || info.class;
        selectEl.appendChild(option);
    });
    
    selectEl.addEventListener('change', onAutomationSelected);
}

// Handle automation selection
function onAutomationSelected(e) {
    const automationName = e.target.value;
    const paramsEl = document.getElementById('automation-params');
    const playBtn = document.getElementById('btn-play-automation');
    
    if (!automationName) {
        paramsEl.innerHTML = '';
        playBtn.disabled = true;
        return;
    }
    
    const automation = state.automations[automationName];
    paramsEl.innerHTML = '';
    
    // Render parameter controls
    Object.entries(automation.parameters).forEach(([paramName, paramInfo]) => {
        const div = document.createElement('div');
        div.className = 'mb-2';
        
        const label = document.createElement('label');
        label.className = 'form-label text-capitalize';
        label.textContent = paramName.replace(/_/g, ' ');
        div.appendChild(label);
        
        if (paramInfo.type === 'float') {
            const input = document.createElement('input');
            input.type = 'range';
            input.className = 'form-range';
            input.id = `auto-param-${paramName}`;
            input.step = '0.1';
            input.min = '0';
            input.max = '10';
            input.value = paramInfo.default || '1';
            
            const valueSpan = document.createElement('span');
            valueSpan.className = 'ms-2';
            valueSpan.textContent = input.value;
            
            input.addEventListener('input', () => {
                valueSpan.textContent = input.value;
            });
            
            div.appendChild(input);
            div.appendChild(valueSpan);
            
        } else if (paramInfo.type === 'bool') {
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.className = 'form-check-input';
            input.id = `auto-param-${paramName}`;
            input.checked = paramInfo.default || false;
            
            const checkDiv = document.createElement('div');
            checkDiv.className = 'form-check';
            checkDiv.appendChild(input);
            
            const checkLabel = document.createElement('label');
            checkLabel.className = 'form-check-label';
            checkLabel.htmlFor = input.id;
            checkLabel.textContent = paramName.replace(/_/g, ' ');
            checkDiv.appendChild(checkLabel);
            
            div.innerHTML = '';
            div.appendChild(checkDiv);
            
        } else if (paramInfo.type === 'int') {
            const input = document.createElement('input');
            input.type = 'number';
            input.className = 'form-control';
            input.id = `auto-param-${paramName}`;
            input.value = paramInfo.default || '1';
            div.appendChild(input);
        }
        
        paramsEl.appendChild(div);
    });
    
    playBtn.disabled = false;
}

// Play automation
function playAutomation() {
    const automationName = document.getElementById('automation-select').value;
    if (!automationName || !state.connected) return;
    
    const automation = state.automations[automationName];
    const params = {};
    
    // Collect parameter values
    Object.keys(automation.parameters).forEach(paramName => {
        const input = document.getElementById(`auto-param-${paramName}`);
        if (input) {
            if (input.type === 'checkbox') {
                params[paramName] = input.checked;
            } else if (input.type === 'number') {
                params[paramName] = parseInt(input.value);
            } else {
                params[paramName] = parseFloat(input.value);
            }
        }
    });
    
    state.socket.emit('play', {
        type: 'automation',
        automation: automationName,
        params: params
    });
}

// Play file
function playFile(filename) {
    if (!state.connected) {
        showError('Not connected to server');
        return;
    }
    
    state.socket.emit('play', { type: 'file', filename: filename });
}

// Apply HUB75 hardware settings
function applyHardwareSettings() {
    if (!state.connected) {
        showError('Not connected to server');
        return;
    }
    
    const settings = {
        gpio_slowdown: parseInt(document.getElementById('gpio-slowdown').value),
        pwm_bits: parseInt(document.getElementById('pwm-bits').value),
        pwm_lsb_nanoseconds: parseInt(document.getElementById('pwm-lsb-ns').value),
        limit_refresh_rate_hz: parseInt(document.getElementById('refresh-rate-limit').value),
        show_refresh_rate: document.getElementById('show-refresh-rate').checked,
        dithering: document.getElementById('dithering').checked ? 1 : 0,
        scan_mode: parseInt(document.getElementById('scan-mode').value),
        disable_hardware_pulsing: document.getElementById('disable-hw-pulsing').checked
    };
    
    state.socket.emit('update_hardware_settings', settings);
    showInfo('Applying hardware settings...');
}

// Stop playback
function stopPlayback() {
    if (!state.connected) return;
    state.socket.emit('stop');
}

// Add to playlist
function addToPlaylist(filename) {
    if (!state.playlist.includes(filename)) {
        state.playlist.push(filename);
        renderPlaylist();
    }
}

// Render playlist
function renderPlaylist() {
    const playlistEl = document.getElementById('playlist');
    playlistEl.innerHTML = '';
    
    state.playlist.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-center';
        item.innerHTML = `
            <span>${index + 1}. ${file}</span>
            <button class="btn btn-sm btn-danger remove-playlist-btn" data-index="${index}">
                <i class="fas fa-times"></i>
            </button>
        `;
        playlistEl.appendChild(item);
    });
    
    // Bind remove handlers
    document.querySelectorAll('.remove-playlist-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            state.playlist.splice(parseInt(btn.dataset.index), 1);
            renderPlaylist();
        });
    });
}

// Update playback controls
function updatePlaybackControls() {
    const playBtn = document.getElementById('btn-play');
    const stopBtn = document.getElementById('btn-stop');
    
    if (state.isPlaying) {
        playBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        playBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

// Update frame info
function updateFrameInfo(current, total) {
    const infoEl = document.getElementById('frame-info');
    infoEl.textContent = `Frame ${current + 1} / ${total}`;
}

// Update slider values
function updateSliderValues() {
    document.getElementById('brightness-value').textContent = 
        Math.round(parseFloat(document.getElementById('brightness-slider').value) * 100) + '%';
    
    document.getElementById('speed-value').textContent = 
        parseFloat(document.getElementById('speed-slider').value).toFixed(1) + 'x';
    
    document.getElementById('gamma-value').textContent = 
        parseFloat(document.getElementById('gamma-slider').value).toFixed(1);
    
    document.getElementById('red-value').textContent = 
        parseFloat(document.getElementById('red-balance').value).toFixed(2);
    
    document.getElementById('green-value').textContent = 
        parseFloat(document.getElementById('green-balance').value).toFixed(2);
    
    document.getElementById('blue-value').textContent = 
        parseFloat(document.getElementById('blue-balance').value).toFixed(2);
}

// Send parameter update
function sendParameter(parameter, value) {
    if (!state.connected) return;
    
    state.socket.emit('set_parameter', {
        parameter: parameter,
        value: value
    });
}

// Handle file upload
function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const progressBar = document.querySelector('#upload-progress .progress-bar');
    const progressContainer = document.getElementById('upload-progress');
    
    progressContainer.classList.remove('d-none');
    
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBar.style.width = percentComplete + '%';
        }
    });
    
    xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.success) {
                showSuccess(`Uploaded: ${response.filename}`);
                loadFileList();
            } else {
                showError(response.error || 'Upload failed');
            }
        } else {
            showError('Upload failed');
        }
        progressContainer.classList.add('d-none');
        progressBar.style.width = '0%';
    });
    
    xhr.addEventListener('error', () => {
        showError('Upload failed');
        progressContainer.classList.add('d-none');
        progressBar.style.width = '0%';
    });
    
    xhr.open('POST', '/api/upload');
    xhr.send(formData);
}

// Show error message
function showError(message) {
    console.error(message);
    const alertHtml = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    const alertContainer = document.getElementById('alert-container') || createAlertContainer();
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const alert = alertContainer.lastElementChild;
        if (alert) alert.remove();
    }, 5000);
}

// Show success message
function showSuccess(message) {
    console.log(message);
    const alertHtml = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="fas fa-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    const alertContainer = document.getElementById('alert-container') || createAlertContainer();
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto dismiss after 3 seconds
    setTimeout(() => {
        const alert = alertContainer.lastElementChild;
        if (alert) alert.remove();
    }, 3000);
}

// Create alert container if it doesn't exist
function createAlertContainer() {
    const container = document.createElement('div');
    container.id = 'alert-container';
    container.style.position = 'fixed';
    container.style.top = '20px';
    container.style.right = '20px';
    container.style.zIndex = '9999';
    container.style.minWidth = '300px';
    document.body.appendChild(container);
    return container;
}

// Initialize preview canvas
function initializePreview() {
    state.previewCanvas = document.getElementById('preview-canvas');
    state.previewCtx = state.previewCanvas.getContext('2d');
    state.previewCtx.imageSmoothingEnabled = false;
}

// Initialize event handlers
function initializeEventHandlers() {
    // Playback controls
    document.getElementById('btn-play').addEventListener('click', () => {
        if (state.currentFile) {
            playFile(state.currentFile);
        } else if (state.files.length > 0) {
            playFile(state.files[0].name);
        }
    });
    
    document.getElementById('btn-stop').addEventListener('click', stopPlayback);
    
    // File upload
    document.getElementById('file-upload').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
    
    // Device selector
    document.getElementById('device-selector').addEventListener('change', (e) => {
        if (!state.connected) return;
        state.socket.emit('switch_device', { device_type: e.target.value });
    });
    
    // Parameter sliders
    document.getElementById('brightness-slider').addEventListener('input', (e) => {
        updateSliderValues();
        sendParameter('brightness', parseFloat(e.target.value));
    });
    
    document.getElementById('speed-slider').addEventListener('input', (e) => {
        updateSliderValues();
        sendParameter('speed', parseFloat(e.target.value));
    });
    
    document.getElementById('gamma-slider').addEventListener('input', (e) => {
        updateSliderValues();
        sendParameter('gamma', parseFloat(e.target.value));
    });
    
    // RGB balance sliders
    ['red', 'green', 'blue'].forEach((color, index) => {
        document.getElementById(`${color}-balance`).addEventListener('input', (e) => {
            updateSliderValues();
            const rgbBalance = [
                parseFloat(document.getElementById('red-balance').value),
                parseFloat(document.getElementById('green-balance').value),
                parseFloat(document.getElementById('blue-balance').value)
            ];
            sendParameter('rgb_balance', rgbBalance);
        });
    });
    
    // Playlist controls
    document.getElementById('btn-clear-playlist').addEventListener('click', () => {
        state.playlist = [];
        renderPlaylist();
    });
    
    // Automation controls
    document.getElementById('btn-play-automation').addEventListener('click', playAutomation);
    
    // HUB75 Hardware controls
    document.getElementById('gpio-slowdown').addEventListener('input', (e) => {
        document.getElementById('gpio-slowdown-value').textContent = e.target.value;
    });
    
    document.getElementById('pwm-bits').addEventListener('input', (e) => {
        document.getElementById('pwm-bits-value').textContent = e.target.value + ' bits';
    });
    
    document.getElementById('pwm-lsb-ns').addEventListener('input', (e) => {
        document.getElementById('pwm-lsb-value').textContent = e.target.value + ' ns';
    });
    
    document.getElementById('refresh-rate-limit').addEventListener('input', (e) => {
        document.getElementById('refresh-rate-value').textContent = e.target.value + ' Hz';
    });
    
    document.getElementById('btn-apply-hardware').addEventListener('click', applyHardwareSettings);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSocket();
    initializePreview();
    initializeEventHandlers();
    updateSliderValues();
});