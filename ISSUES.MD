# Open Issues & Tasks

## Internationalization (i18n)
- Translate remaining non‑English strings (especially Polish) in the Notifications tab:
  - "Email Provider"
  - "Email Username"
  - "Email Password/App Password"
  - "💾 Save Email Configuration"
- Verify all supported languages have complete coverage across tabs and controls.

## Documentation Improvements
- Add a Mermaid diagram to README explaining the data preload flow, where data is stored (cache vs vector store), and session lifecycle.
- Clean up redundant or outdated docs and files; make the documentation production‑ready.

## Model Comparison Tab
- Show token and price information per provider/model.
- Include local models in comparison (when available) with guidance on capabilities and costs.

## Theming
- Integrate a free theme for the AI Real Estate UI (consistent colors, typography, dark/light modes).

## Local Models & Offline Usage
- Add more local models support.
- Provide clear instructions to install/start local models if not installed, and how to run offline.

## Configuration & Secrets
- Ensure `OPENAI_API_KEY` and other provider keys are not stored in the repository.
- Use environment variables locally and Streamlit Cloud secrets in deployment.

## Questions
- Where are keys stored?
  - Locally: in OS environment variables accessed via `config/settings.py` (`openai_api_key`, etc.). Optionally `.env` during development, but `.env` must never be committed.
  - Deployment: in Streamlit Cloud "Secrets" (or other secret managers). Keys are injected into the environment at runtime.


