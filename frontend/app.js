let mediaRecorder;
let audioChunks = [];
let recordedBlob = null;
let chartInstance = null;

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
recordBtn.onclick = async () => {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = () => {
      recordedBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
    };

    mediaRecorder.start();
    recordBtn.innerText = 'Stop Recording';
    document.getElementById('timer').style.display = 'block';

    let sec = 30;
    const interval = setInterval(() => {
      sec--;
      document.getElementById('timer').innerText = `00:${sec < 10 ? '0' : ''}${sec}`;
      if (sec <= 0 || mediaRecorder.state === 'inactive') {
        clearInterval(interval);
        if (mediaRecorder.state === 'recording') mediaRecorder.stop();
        recordBtn.innerText = 'Start 30s Recording';
        document.getElementById('timer').style.display = 'none';
      }
    }, 1000);
  } else {
    mediaRecorder.stop();
  }
};

document.getElementById('audioFileInput').onchange = (e) => {
  recordedBlob = e.target.files[0];
};

document.getElementById('analyzeBtn').onclick = async () => {
  if (!recordedBlob) return alert('Please record 30s audio or upload an audio file first.');

  const formData = new FormData();
  formData.append('audio', recordedBlob, 'recording.webm');

  const metadata = {
    location: window.userCoords || null,
    timestamp_iso: new Date().toISOString(),
    environment: document.querySelector('input[name="env"]:checked').value
  };
  formData.append('metadata', JSON.stringify(metadata));

  try {
    const res = await fetch('http://localhost:8000/api/v1/detect', { method: 'POST', body: formData });
    const data = await res.json();
    
    renderPieChart(data.predictions);
    updateResultMap(metadata);
    updateResultSummary(metadata);
    updateAccuracyIndicator(data.predictions);
  } catch (err) {
    alert('Failed to connect to backend API.');
  }
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
