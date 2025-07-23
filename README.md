
# 🔍 GitHub Issue Analyzer

An AI-powered web app that summarizes and classifies GitHub issues using OpenAI's GPT model.

---

## 🚀 How to Run

### 1. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file
Paste the following and fill in your keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
GITHUB_TOKEN=your_github_token_here     # Optional but recommended
FLASK_ENV=development
PORT=5000
```

- Get your OpenAI API key from: https://platform.openai.com/api-keys  
- Generate a GitHub token (scope: `public_repo`) from: https://github.com/settings/tokens

### 4. Run the App
```bash
python Backend/app.py
```

Then open your browser and go to: [http://localhost:5000](http://localhost:5000)

---

## ✅ Features

- 🔗 Input any **public GitHub repo + issue number**
- 🤖 Uses **OpenAI GPT** to analyze the issue
- 📄 Returns a structured JSON with:
  - `summary` – one-line summary of the issue
  - `type` – bug, feature_request, documentation, question, other
  - `priority_score` – rated 1 to 5 with justification
  - `suggested_labels` – 2–3 recommended labels
  - `potential_impact` – how it affects users
- ⚠️ Handles missing descriptions, empty comments, and long inputs
- 🧠 Falls back to heuristic analysis if OpenAI quota is exceeded
- 💡 Clean frontend with:
  - JSON copy button
  - Auto-generated placeholders
  - Error messages and retry support

---
