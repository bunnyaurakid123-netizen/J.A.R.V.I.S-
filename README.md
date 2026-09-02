# J.A.R.V.I.S v3.1

Desktop AI assistant built with Python and PyQt6.

## Intelligence upgrades
- Lightweight agent planning for every request
- Bounded conversation context for long sessions
- Persistent-memory context injection
- Mode-aware dynamic system instructions
- Safer API-key handling: no embedded credential in source
- Gemini streaming with fallback models and retries

## Setup
```bash
pip install -r requirements.txt
set JARVIS_API_KEY=your-key-here
python main.py
```

On PowerShell:
```powershell
$env:JARVIS_API_KEY="your-key-here"
python main.py
```

API keys are intentionally not committed to this repository.