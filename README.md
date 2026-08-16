# VectorGuard AI: Acoustic Mosquito Surveillance & Risk Assessment

VectorGuard AI is an intelligent acoustic surveillance platform designed for vector control and malaria monitoring. Developed as an Academic Bootcamp Project at Carnegie Mellon University Africa (CMU Africa), the system captures mosquito wingbeat audio hums, classifies vector presence using deep learning, and generates field-ready public health interpretations using LLM intelligence.

---

## Live Deployed Links

- Frontend Web Application: https://vectorguard-frontend.onrender.com
- Backend REST API: https://vectorguard-backend.onrender.com
- API Health Check Endpoint: https://vectorguard-backend.onrender.com/api/v1/health
- API Interactive Documentation: https://vectorguard-backend.onrender.com/docs

---

## System Architecture

VectorGuard AI consists of three integrated core components:

1. Acoustic Classification Engine (Version 6: MosquitoAttnNet)
   - Model Architecture: 2D-CNN + Bi-directional LSTM + Self-Attention Pooling
   - Input Features: 40 Mel-Frequency Cepstral Coefficients (MFCCs) derived from 64 Mel-spectrogram bins at 8,000 Hz sample rate
   - Target Classes: Anopheles (primary malaria vector) vs Non-Anopheles
   - Signal Preprocessing: Peak-energy sliding window detection and unit-amplitude normalization

2. Public Health LLM Engine
   - Framework: LangChain Groq integration (Qwen 3.6 27B model)
   - Functionality: Translates numerical acoustic detection percentages and environmental context (indoor/outdoor) into plain-language risk evaluations and actionable safety recommendations for field personnel

3. Interactive Dashboard & Web Application
   - Audio Capture: 30-second live audio recording via WebRTC MediaRecorder or file upload (.wav, .mp3, .m4a, .webm)
   - Spatial Context: Browser Geolocation API and embedded OpenStreetMap rendering
   - Visualization: Real-time audio waveform animation, Chart.js probability breakdown, and dynamic confidence indicators

---

## Repository Structure

```
mosquito_survaillance_ai/
├── WebApp/
│   ├── frontend/
│   │   ├── index.html            # Dashboard markup and UI cards
│   │   ├── app.js                # WebRTC audio recording, Geolocation, and API client logic
│   │   ├── styles.css            # Responsive layout, animations, and print stylesheets
│   │   └── public/               # Web app manifests and static assets
│   └── backend/backend/
│       ├── app/
│       │   ├── main.py           # FastAPI application and endpoint routing
│       │   ├── ml_engine.py      # PyTorch MosquitoAttnNet V6 model architecture and inference
│       │   ├── llm_engine.py     # Groq LLM integration and prompt template
│       │   └── utils.py          # Audio conversion utilities via Pydub and FFmpeg
│       ├── model/
│       │   ├── Malaria_detector_Net_V6.pth # V6 pre-trained PyTorch weights
│       │   └── Malaria_detector_Net_V4.pth # V4 pre-trained PyTorch weights
│       ├── Dockerfile            # Container definition for Render deployment
│       └── requirements.txt      # Python dependencies
├── model_training/               # Data preprocessing, training notebooks, and quantization experiments
├── report_and_proposal/          # Project proposal and documentation PDF
└── render.yaml                   # Infrastructure-as-Code blueprint for Render deployment
```

---

## Local Development Guide

### Prerequisites
- Python 3.10 or higher (or Conda environment)
- FFmpeg installed (`brew install ffmpeg` on macOS)
- Groq API Key (from https://console.groq.com/)

### Setup Instructions

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/TReV-89/mosquito_survaillance_ai.git
   cd mosquito_survaillance_ai
   ```

2. Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

3. Install backend dependencies:
   ```bash
   cd WebApp/backend/backend
   pip install -r requirements.txt
   ```

4. Start the backend server:
   ```bash
   python app/main.py
   ```
   The backend API will run on http://localhost:8000. Verify status at http://localhost:8000/api/v1/health.

5. Start the frontend web application:
   In a separate terminal window:
   ```bash
   cd WebApp/frontend
   python -m http.server 8080
   ```
   Open your browser and navigate to http://localhost:8080.

---

## Deployment Configuration (Render)

This repository includes a `render.yaml` Blueprint file for automatic deployment on Render:

- Backend Service: Containerized Docker service running Python 3.10 slim, FFmpeg, and CPU-optimized PyTorch.
- Frontend Service: Static web site serving dashboard HTML, CSS, and JS assets.

### Deploying to Render
1. Push all project code to GitHub.
2. Go to the Render Dashboard (https://dashboard.render.com/) -> New -> Blueprint.
3. Select this repository and supply the `GROQ_API_KEY` environment variable.
4. Render will automatically provision and launch both services.

---

## Authors & Acknowledgments

Developed as part of an Academic Bootcamp Project at Carnegie Mellon University Africa (CMU Africa).
Copyright 2026 VectorGuard AI. All rights reserved.
