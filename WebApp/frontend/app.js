let mediaRecorder;
let audioChunks = [];
let recordedBlob = null;
let chartInstance = null;
const API_BASE = document.querySelector('meta[name="api-base"]')?.getAttribute('content') || 'http://localhost:8000';

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('public/sw.js');
}

window.onload = () => {
  document.getElementById('timeVal').innerText = new Date().toLocaleTimeString();
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        window.userCoords = { lat: pos.coords.latitude, lng: pos.coords.longitude, acc: pos.coords.accuracy };
        document.getElementById('gpsVal').innerText = `${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
      },
      () => { document.getElementById('gpsVal').innerText = 'Location Unavailable'; }
    );
  }
};

const recordBtn = document.getElementById('recordBtn');
const timerEl = document.getElementById('timer');
const recordingStatus = document.getElementById('recordingStatus');
const analyzeBtn = document.getElementById('analyzeBtn');
const processingCard = document.getElementById('processingCard');
const resultCard = document.getElementById('resultCard');
const printBtn = document.getElementById('printBtn');
const llmInsight = document.getElementById('llmInsight');
let recordingTimer = null;

function showProcessingState() {
  processingCard.classList.remove('hidden');
  resultCard.classList.add('hidden');
  analyzeBtn.disabled = true;
  analyzeBtn.innerText = 'Analyzing...';
}

function hideProcessingState() {
  processingCard.classList.add('hidden');
  resultCard.classList.remove('hidden');
  analyzeBtn.disabled = false;
  analyzeBtn.innerText = 'Analyze Acoustic Data';
}

async function generateAIInsight(predictions) {
  const values = {
    anopheles: Number(predictions?.anopheles || 0),
    non_anopheles: Number(predictions?.non_anopheles || 0),
    other_insects_or_noise: Number(predictions?.other_insects_or_noise || 0)
  };

  const dominant = Math.max(...Object.values(values));
  const highestType = Object.entries(values).sort((a, b) => b[1] - a[1])[0];

  const localFallback = dominant >= 70
    ? `High ${highestType[0] === 'anopheles' ? 'mosquito concentration' : highestType[0] === 'non_anopheles' ? 'vector activity' : 'ambient insect noise'} detected in this area. The concentration is elevated, and the location may not be safe for people who are at risk of mosquito bites. Please avoid long exposure, wear protective clothing, and consider reducing outdoor activity in this zone.`
    : dominant >= 45
      ? 'Moderate mosquito activity has been detected. The area is not entirely risk-free, but the concentration is manageable. Continue basic protection and monitor the site if it is frequently visited.'
      : 'The current acoustic signal suggests low mosquito presence in this location. Conditions appear relatively safer, though routine prevention remains advisable.';

  try {
    const res = await fetch(`${API_BASE}/api/v1/llm-insight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ predictions: values, summary: localFallback })
    });

    if (!res.ok) throw new Error('LLM endpoint unavailable');

    const data = await res.json();
    if (data && data.insight) return data.insight;
  } catch (err) {
  }

  return localFallback;
}

function validateAudioInput(file) {
  if (!file) {
    return 'Please record 30 seconds of audio or upload an audio file first.';
  }

  if (!(file instanceof Blob)) {
    return 'The selected audio input is invalid.';
  }

  if (!file.type || !file.type.startsWith('audio/')) {
    return 'The selected file is not a valid audio file.';
  }

  if (file.size <= 0) {
    return 'The selected audio file is empty.';
  }

  if (file.size > 25 * 1024 * 1024) {
    return 'The selected audio file is too large. Please use a file smaller than 25MB.';
  }

  return null;
}

function validateEnvironment() {
  const selected = document.querySelector('input[name="env"]:checked');
  if (!selected) {
    return 'Please select the environment before analysis.';
  }

  return null;
}

recordBtn.onclick = async () => {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('This browser does not support microphone access. Please use a modern browser.');
    return;
  }

  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = () => {
        recordedBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
      };

      mediaRecorder.start();
      recordBtn.innerText = 'Stop Recording';
      recordBtn.classList.add('recording');
      timerEl.classList.remove('hidden');
      recordingStatus.classList.remove('hidden');
      startCountdown(30);
    } catch (err) {
      alert('Unable to access microphone. Please allow audio permissions.');
    }
  } else {
    stopRecording();
  }
};

function startCountdown(duration) {
  let sec = duration;
  timerEl.innerText = formatTime(sec);
  recordingTimer = setInterval(() => {
    sec -= 1;
    timerEl.innerText = formatTime(sec);
    if (sec <= 0) {
      stopRecording();
    }
  }, 1000);
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
  }
  clearInterval(recordingTimer);
  recordBtn.innerText = 'Start 30s Recording';
  recordBtn.classList.remove('recording');
  timerEl.classList.add('hidden');
  recordingStatus.classList.add('hidden');
}

function formatTime(sec) {
  const mins = Math.floor(sec / 60);
  const secs = sec % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

document.getElementById('audioFileInput').onchange = (e) => {
  recordedBlob = e.target.files[0];
};

analyzeBtn.onclick = async () => {
  const audioValidationError = validateAudioInput(recordedBlob);
  if (audioValidationError) return alert(audioValidationError);

  const environmentValidationError = validateEnvironment();
  if (environmentValidationError) return alert(environmentValidationError);

  const formData = new FormData();
  const fileName = recordedBlob.name || `recording.${recordedBlob.type.includes('audio/wav') ? 'wav' : 'webm'}`;
  formData.append('audio', recordedBlob, fileName);

  const metadata = {
    location: window.userCoords || null,
    timestamp_iso: new Date().toISOString(),
    environment: document.querySelector('input[name="env"]:checked').value
  };
  formData.append('metadata', JSON.stringify(metadata));

  showProcessingState();

  try {
    const res = await fetch(`${API_BASE}/api/v1/detect`, { method: 'POST', body: formData });
    const responseText = await res.text();

    let data = {};
    if (responseText) {
      try {
        data = JSON.parse(responseText);
      } catch (err) {
        throw new Error('Backend returned an invalid response.');
      }
    }

    if (!res.ok) {
      throw new Error(data.detail || 'Backend analysis request failed.');
    }

    renderPieChart(data.predictions);
    updateResultMap(metadata);
    updateResultSummary(metadata);
    updateAccuracyIndicator(data.predictions);
    llmInsight.innerText = await generateAIInsight(data.predictions);
    hideProcessingState();
  } catch (err) {
    llmInsight.innerText = 'The system could not complete the analysis. Please try again or check the input audio.';
    hideProcessingState();
    alert(err.message || 'Failed to connect to backend API.');
  }
};

printBtn.onclick = () => {
  window.print();
};

function getMapUrl(coords) {
  if (!coords || typeof coords.lat !== 'number' || typeof coords.lng !== 'number') {
    return 'about:blank';
  }
  const lat = coords.lat;
  const lng = coords.lng;
  const delta = 0.05;
  const west = lng - delta;
  const south = lat - delta;
  const east = lng + delta;
  const north = lat + delta;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${west}%2C${south}%2C${east}%2C${north}&layer=mapnik&marker=${lat}%2C${lng}`;
}

function updateResultMap(metadata) {
  const mapFrame = document.getElementById('mapFrame');
  mapFrame.src = getMapUrl(metadata.location);
}

function updateResultSummary(metadata) {
  document.getElementById('mapCoords').innerText = metadata.location
    ? `${metadata.location.lat.toFixed(4)}, ${metadata.location.lng.toFixed(4)}`
    : 'Unavailable';
  document.getElementById('mapTime').innerText = new Date(metadata.timestamp_iso).toLocaleString();
  document.getElementById('mapEnv').innerText = metadata.environment || '--';
}

function updateAccuracyIndicator(pred) {
  const values = [pred.anopheles || 0, pred.non_anopheles || 0, pred.other_insects_or_noise || 0];
  const accuracy = Math.round(Math.max(...values));
  const fill = document.getElementById('accuracyFill');
  const label = document.getElementById('accuracyLabel');
  const text = document.getElementById('accuracyText');

  label.innerText = `${accuracy}%`;
  fill.style.width = `${accuracy}%`;

  if (accuracy <= 40) {
    fill.style.background = '#ff3b30';
    text.innerText = 'Low confidence';
  } else if (accuracy <= 70) {
    fill.style.background = '#ff9500';
    text.innerText = 'Moderate confidence';
  } else if (accuracy <= 90) {
    fill.style.background = '#ffd60a';
    text.innerText = 'High confidence';
  } else {
    fill.style.background = '#34c759';
    text.innerText = 'Very high confidence';
  }
}

function renderPieChart(pred) {
  document.getElementById('resultCard').style.display = 'block';
  const ctx = document.getElementById('pieChart').getContext('2d');
  
  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Anopheles', 'Non-Anopheles', 'Other Insects/Noise'],
      datasets: [{
        data: [pred.anopheles || 0, pred.non_anopheles || 0, pred.other_insects_or_noise || 0],
        backgroundColor: ['#ff3b30', '#ff9500', '#34c759']
      }]
    },
    options: {
      plugins: {
        legend: { labels: { color: '#330606' } }
      }
    }
  });
}
