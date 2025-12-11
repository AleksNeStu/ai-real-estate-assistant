# 🏠 AI Real Estate Assistant

> **A modern, intelligent real estate assistant powered by advanced AI**

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.2+-green?style=flat)](https://langchain.com)
[![CI](https://github.com/AleksNeStu/ai-real-estate-assistant/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AleksNeStu/ai-real-estate-assistant/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> Note: Version 3 (V3) is under active development. Bugs and behavior changes may occur.
> For a stable, non-evolving release, please use the V2 branch: https://github.com/AleksNeStu/ai-real-estate-assistant/tree/ver2

## 🌟 Overview

The AI Real Estate Assistant is a conversational AI application that helps users find their ideal properties through natural language interaction. The modern version (V3) features intelligent query understanding, multi-provider AI model support, sophisticated search capabilities, and a completely modernized UI with dark mode support.

**[Live Demo](https://ai-real-estate-assistant.streamlit.app/)** | **[Documentation](docs/)** | **[Contributing](CONTRIBUTING.md)**

---

## ✨ Key Features

### 🤖 Multiple AI Model Providers
- **OpenAI**: GPT-4o, GPT-4o-mini, O1, O1-mini, O3-mini, GPT-4 Turbo, GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus
- **Google**: Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.0 Flash
- **Grok (xAI)**: Grok 2, Grok 2 Vision, Grok Beta
- **DeepSeek**: DeepSeek Chat, DeepSeek Coder, DeepSeek Reasoner (R1)
- **Ollama**: Local models (Llama 3.3, Mistral, Qwen, Phi-3)
- **Total**: 25+ models across 6 providers

### 🧠 Intelligent Query Processing (Phase 2)
- **Query Analyzer**: Automatically classifies intent and complexity
- **Hybrid Agent**: Routes queries to RAG or specialized tools
- **Smart Routing**: Simple queries → RAG (fast), Complex → Agent+Tools
- **Multi-Tool Support**: Mortgage calculator, property comparison, price analysis

### 🔍 Advanced Search & Retrieval
- **Persistent ChromaDB Vector Store**: Fast, persistent semantic search
- **Hybrid Retrieval**: Semantic + keyword search with MMR diversity
- **Result Reranking**: 30-40% improvement in relevance
- **Filter Extraction**: Automatic extraction of price, rooms, location, amenities

### 💎 Enhanced User Experience (V3 Modernization)
- **Modern Dark Mode**:
  - WCAG 2.1 AA compliant (4.5:1 minimum contrast ratio)
  - System preference detection with manual override
  - Smooth theme transitions
  - Enhanced form label visibility
- **Geospatial Filters & Expert Panel**:
  - Radius-based filters around selected city
  - City price indices (avg/median, price per sqm)
  - Dedicated Expert Panel UI in Market Insights
- **Tailwind CSS Integration**: Modern utility-first CSS framework
- **Responsive Design**: Mobile-first approach for all screen sizes
- **Accessibility**: Full keyboard navigation and screen reader support
- **Real-time Configuration**: Change models and settings on the fly
- **Source Attribution**: See where information comes from
- **Processing Transparency**: View query analysis and routing decisions
- **Conversation Memory**: Maintains context across multiple turns
- **Multi-language Support**: 9 languages (EN, PL, ES, DE, FR, IT, PT, RU, ZH)

### 🛠️ Specialized Tools
- **Mortgage Calculator**: Monthly payments, interest, total cost
- **Property Comparator**: Side-by-side property analysis
- **Price Analyzer**: Statistical analysis and market trends
- **Location Analyzer**: Proximity and neighborhood insights

---

## 🚀 Quick Start

Choose your preferred installation method:

### 🐳 Option 1: Docker (Recommended - All Platforms)

**Easiest way to run the app with zero configuration issues!**

```bash
# 1. Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# 2. Set up environment
cp .env.example .env
# Edit .env and add your API keys

# 3. Start with Docker Compose
docker-compose up -d

# 4. Open browser
# Visit: http://localhost:8501
```

📚 **[Full Docker Guide →](docs/DOCKER.md)**

---

### 💻 Option 2: Local Installation

#### Prerequisites
- Python 3.11 or higher (use Python 3.11 to create the virtual environment and install dependencies)
- pip package manager
- Git
- At least one LLM API key (OpenAI, Anthropic, or Google) OR Ollama installed locally

#### Windows

**PowerShell (Recommended)**:
```powershell
# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Create virtual environment
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

# Run the app
streamlit run app_modern.py
```

**Command Prompt (CMD)**:
```cmd
REM Create virtual environment with Python 3.11
py -3.11 -m venv venv
REM Activate virtual environment
venv\Scripts\activate.bat

REM Upgrade pip and install dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

REM Run the app
streamlit run app_modern.py
```

 

#### macOS

```bash
# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Ensure Python 3.11 is installed (Homebrew)
brew install python@3.11
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile

# Create virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

# Run the app
streamlit run app_modern.py
```

 

#### Linux (Ubuntu/Debian)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and essentials
sudo apt install python3.11 python3.11-venv python3-pip git -y

# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

# Run the app
streamlit run app_modern.py
```

 

#### Configure API Keys (all platforms)
- Required: At least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
- Optional: OLLAMA_BASE_URL for local models

Set for current session:
- Windows (PowerShell):
  ```powershell
  $env:OPENAI_API_KEY="your-openai-key"
  $env:ANTHROPIC_API_KEY="your-anthropic-key"
  $env:GOOGLE_API_KEY="your-google-key"
  ```
- macOS/Linux:
  ```bash
  export OPENAI_API_KEY="your-openai-key"
  export ANTHROPIC_API_KEY="your-anthropic-key"
  export GOOGLE_API_KEY="your-google-key"
  ```

Set persistently:
- Windows (User Environment Variables):
  ```powershell
  [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key", "User")
  [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-key", "User")
  [System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-key", "User")
  ```
- macOS (zsh) and Linux:
  ```bash
  echo 'export OPENAI_API_KEY="your-key"' >> ~/.zshrc
  echo 'export ANTHROPIC_API_KEY="your-key"' >> ~/.zshrc
  echo 'export GOOGLE_API_KEY="your-key"' >> ~/.zshrc
  source ~/.zshrc
  ```

Alternative: `.streamlit/secrets.toml`
```toml
# Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and fill values
OPENAI_API_KEY = "sk-..."
ANTHROPIC_API_KEY = "sk-ant-..."
GOOGLE_API_KEY = "AI-..."
```

---

### 🤖 Option 3: Using Local Models (Ollama)

**No API keys needed!** Run models locally on your machine.

#### Install Ollama

**Windows/macOS**: Download from [ollama.ai](https://ollama.ai/)

**Linux**:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Pull Models and Run

```bash
# Pull a model (one-time setup)
ollama pull llama3.3  # or mistral, qwen2.5, phi3, etc.

# Start Ollama service (runs in background)
ollama serve

# In another terminal, run the app
streamlit run app_modern.py
```

Then in the app:
1. Select "Ollama (Local)" as provider
2. Choose your downloaded model
3. Start chatting!

---

### Running the App

After installation, start the application:

```bash
# Direct command
streamlit run app_modern.py

# Or use convenience script (Unix/macOS/Linux)
./run_modern.sh

# Or use convenience script (Windows PowerShell)
./run_modern.ps1
```

The app will open automatically in your default browser at:
**http://localhost:8501**

If it doesn't open automatically, click the URL shown in the terminal.

---

## 🖼️ Screenshots

Screenshots are generated on demand to match the latest V3 UI.

- Start the app: `streamlit run app_modern.py`
- Install browsers (first time): `npx playwright install`
- Capture: `npm run screenshots`
- Optional: `APP_URL=http://localhost:8502 npm run screenshots`

The generated images are not embedded here to avoid stale visuals. Refer to the app directly for the most up‑to‑date UI.

## 📖 Usage Examples

See the app and `docs/PHASE3_README.md` for practical scenarios (search, mortgage, comparison, market insights). Examples are kept in documentation to avoid duplication and ensure accuracy.

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│  (Model Selection, Settings, Chat Interface)            │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Query Analyzer     │
        │  (Intent, Filters)  │
        └──────────┬──────────┘
                   │
      ┌────────────┴────────────┐
      │                         │
┌─────▼─────┐           ┌──────▼──────┐
│    RAG    │           │    Agent    │
│  (Simple) │           │  (Complex)  │
└─────┬─────┘           └──────┬──────┘
      │                        │
      │                ┌───────▼────────┐
      │                │     Tools      │
      │                │ - Mortgage     │
      │                │ - Comparison   │
      │                │ - Analysis     │
      │                └───────┬────────┘
      │                        │
      └────────────┬───────────┘
                   │
         ┌─────────▼─────────┐
         │  Result Reranker  │
         └─────────┬─────────┘
                   │
         ┌─────────▼─────────┐
         │ Response Formatter│
         └───────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **UI** | Streamlit 1.37+ | Modern web interface |
| **AI Models** | OpenAI, Anthropic, Google, Ollama | Multiple LLM providers |
| **Framework** | LangChain 0.2+ | AI orchestration |
| **Vector Store** | ChromaDB 0.5+ | Persistent semantic search |
| **Embeddings** | FastEmbed (BGE) | Efficient vector generation |
| **Data Validation** | Pydantic 2.5+ | Type-safe schemas |
| **Data Processing** | Pandas 2.1+ | DataFrame operations |
| **Language** | Python 3.11+ | Core development |

---

## 📁 Project Structure (V3)

```
ai-real-estate-assistant/
├── app_modern.py              # 🆕 Modern V3 app (Recommended)
├── run_modern.sh              # 🆕 Launch modern app
├── CONTRIBUTING.md            # 🆕 V3: Contribution guidelines
├── .gitignore                 # 🆕 V3: Enhanced gitignore
│
├── agents/                    # 🆕 Phase 2: Intelligent agents
│   ├── query_analyzer.py      #     Intent classification
│   ├── hybrid_agent.py        #     RAG + Agent orchestration
│   └── recommendation_engine.py #   Personalized recommendations
│
├── analytics/                 # 🆕 Phase 3: Analytics & insights
│   ├── market_insights.py     #     Market trend analysis
│   └── session_tracker.py     #     User behavior tracking
│
├── assets/                    # 🆕 V3: Static assets
│   ├── css/                   #     Stylesheets
│   │   ├── dark_mode.css      #     🆕 Dark mode styles (WCAG AA)
│   │   └── tailwind_custom.css #    🆕 Tailwind utilities
│   ├── js/                    #     JavaScript files
│   │   └── dark_mode.js       #     🆕 Theme toggle & system detection
│   └── *.png                  #     Screenshots
│
├── config/                    # 🆕 Phase 1: Configuration
│   └── settings.py            #     Centralized settings
│
├── data/                      # Data processing
│   ├── schemas.py             # 🆕 Pydantic models
│   └── csv_loader.py          #     CSV data loading
│
├── dataset/                   # Sample property datasets
│   └── pl/                    #     Polish apartment data (6 months)
│
├── docs/                      # 🆕 V3: Documentation (restructured)
│   ├── README.md              #     Documentation navigation
│   ├── PRD.MD                 #     Product requirements
│   ├── MODERNIZATION_PROPOSAL.md # Modernization plan
│   ├── PHASE2_README.md       #     Phase 2: Hybrid agent
│   ├── PHASE3_README.md       #     Phase 3: Analytics & export
│   ├── PHASE4_README.md       #     Phase 4: Advanced visualizations
│   ├── PHASE5_README.md       #     Phase 5: Notifications
│   ├── DEPLOYMENT.md          #     Deployment guide
│   ├── DOCKER.md              #     Docker setup
│   ├── TESTING_GUIDE.md       #     Testing documentation
│   └── TODO.MD                #     Development roadmap
│
├── i18n/                      # 🆕 Phase 1: Internationalization
│   └── translations.py        #     9 language support
│
├── models/                    # 🆕 Phase 1: Model providers
│   ├── provider_factory.py    #     Multi-provider management
│   └── providers/             #     6 providers (OpenAI, Anthropic, etc.)
│       ├── openai.py
│       ├── anthropic.py
│       ├── google.py
│       ├── grok.py
│       ├── deepseek.py
│       └── ollama.py
│
├── notifications/             # 🆕 Phase 5: Alert system
│   ├── email_service.py       #     Email configuration
│   ├── alert_manager.py       #     Alert management
│   └── notification_history.py #    Notification tracking
│
├── tests/                     # Test suite
│   ├── unit/                  #     Unit tests
│   └── integration/           #     Integration tests
│
├── tools/                     # 🆕 Phase 2: Agent tools
│   └── property_tools.py      #     Mortgage, comparison, analysis
│
├── ui/                        # 🆕 Phase 3-4: UI components
│   ├── comparison_viz.py      #     Property comparison
│   ├── price_charts.py        #     Price visualizations
│   ├── radar_charts.py        #     Amenity radar charts
│   ├── metrics.py             #     Metric displays
│   ├── market_dashboard.py    #     Market overview
│   ├── geo_viz.py             #     Map visualizations
│   └── components/            #     Reusable components
│
├── utils/                     # Utility functions
│   ├── ui_helpers.py          # 🆕 V3: UI styling & dark mode
│   ├── exporters.py           # 🆕 Phase 3: PDF, CSV, Excel export
│   ├── saved_searches.py      # 🆕 Phase 3: Search management
│   ├── api_key_validator.py   # 🆕 API key validation
│   └── ollama_detector.py     # 🆕 Local Ollama detection
│
├── vector_store/              # 🆕 Phase 1: Vector storage
│   ├── chroma_store.py        #     Persistent ChromaDB
│   ├── hybrid_retriever.py    #     Advanced retrieval
│   └── reranker.py            #     Result reranking
│
├── .streamlit/                # Streamlit configuration
│   └── config.toml            # 🆕 V3: Dark mode theme
│
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build configuration
└── docker-compose.yml         # Docker Compose setup
```

---

## 🎯 Version Comparison

| Feature | V1 (Legacy) | V2 (Legacy) | **V3 (Modern)** |
|---------|-------------|-------------|-----------------|
| **UI Framework** | Basic Streamlit | Enhanced Streamlit | **Modern Streamlit** |
| **AI Models** | 1 (GPT-3.5) | 4 (GPT + Ollama) | **15+ (4 providers)** |
| **Vector Store** | ❌ None | In-memory (ephemeral) | **✅ Persistent ChromaDB** |
| **Query Intelligence** | ❌ No | ❌ No | **✅ Intent analysis** |
| **Agent System** | DataFrame only | ❌ No | **✅ Hybrid RAG + Tools** |
| **Tools** | ❌ No | ❌ No | **✅ 4 specialized tools** |
| **Reranking** | ❌ No | ❌ No | **✅ Multi-signal** |
| **Type Safety** | ❌ No | Partial | **✅ Full (Pydantic)** |
| **Memory** | Single turn | Multi-turn | **✅ Advanced memory** |
| **Performance** | Slow | Medium | **✅ Optimized** |
| **Extensibility** | Low | Medium | **✅ High (modular)** |

---

## 🎨 UI Features

### Sidebar Controls
- **Model Provider Selection**: Choose from OpenAI, Anthropic, Google, Ollama
- **Model Selection**: 15+ models with details (context, cost, capabilities)
- **Advanced Settings**: Temperature, max tokens, retrieval count
- **Intelligence Features** (Phase 2):
  - ✅ Toggle hybrid agent on/off
  - ✅ Toggle query analysis display
  - ✅ Toggle result reranking
- **Data Sources**: Load from URL or sample datasets
- **Session Management**: Clear chat, reset all

### Main Chat Interface
- **Natural Language Input**: Chat-based property search
- **Processing Badges**: Visual indicators of processing method
  - 🛠️ AI Agent + Tools
  - 🔀 Hybrid (RAG + Agent)
  - 📚 RAG Only
  - ✨ Results Reranked
- **Query Analysis**: (Optional) View intent, complexity, filters
- **Source Documents**: Expandable view of data sources
- **Conversation History**: Maintains context across turns

### Visual Enhancements
- Clean, modern design
- Responsive layout
- Dark mode support (Streamlit theme)
- Real-time streaming responses
- Loading animations

---

## 📊 Performance

- Simple RAG queries: 1–2s (typical)
- Filtered search + reranking: 2–3s
- Analysis/Comparison (hybrid): 5–12s depending on dataset and model
- Relevance improves by ~30–40% with reranking

---

## 🔧 Configuration

### Environment Variables
```bash
# Required (at least one)
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
GOOGLE_API_KEY="AI..."

# Optional
OLLAMA_BASE_URL="http://localhost:11434"  # For local models
```

### Application Settings
Edit `config/settings.py` to customize:
- Default model and provider
- Temperature and token limits
- ChromaDB persist directory
- Sample dataset URLs
- UI layout and theme

---

## 🎯 Complete Feature Set (All Phases)

This application includes **5 complete phases** of development:

### Phase 1: Foundation ✅
- Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama)
- ChromaDB persistent vector storage
- Type-safe Pydantic data models
- Modern Streamlit UI
- CSV data loading

### Phase 2: Intelligence ✅
- Hybrid RAG + Agent architecture
- Query intent classification
- Mortgage calculator tool
- Property comparison tool
- Result reranking (30-40% improvement)
- **Tests**: 88 unit tests

### Phase 3: Advanced Features ✅
- Market insights & analytics
- Property comparison dashboard
- Export to CSV/JSON/Markdown
- Saved search management
- Session tracking & analytics
- **Tests**: 163 unit tests

### Phase 4: Visualizations ✅
- Interactive price charts (Plotly)
- Radar charts for multi-property comparison
- Geographic maps (Folium) with heatmaps
- Market dashboards with KPIs
- Comparison visualizations
- **Tests**: 72 unit tests

### Phase 5: Notifications ✅
- Email notification system (SMTP)
- Price drop alerts
- New property notifications
- Notification preferences management
- Notification history & analytics

Tests: Covered by unit/integration tests across modules (see `tests/`).

---

## 📚 Documentation

- **[Docker Setup Guide](docs/DOCKER.md)**: Complete Docker deployment guide
- **[Streamlit Cloud Deployment](docs/DEPLOYMENT.md)**: Cloud deployment instructions
- **[Product Requirements](docs/PRD.MD)**: Project specifications
- **[Modernization Proposal](docs/MODERNIZATION_PROPOSAL.md)**: V3 architecture
- **[Phase 3 README](docs/PHASE3_README.md)**: Advanced features docs
- **[Phase 4 README](docs/PHASE4_README.md)**: Visualization docs
- **[Phase 5 README](docs/PHASE5_README.md)**: Notification system docs
- **[Testing Guide](docs/TESTING_GUIDE.md)**: Comprehensive testing procedures

---

## 📝 Changelog

Recent changes in V3:
- Geospatial radius filter for property selection (Expert Panel)
- City price indices in Market Insights (avg/median, price per sqm)
- Dropdown UI polish — removed blue accents, unified neutral states
- Documentation restructured under `docs/` and updated status notices
- Launchers improved to skip redundant installs on subsequent runs

---

## 🧪 Development

### Project Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
streamlit run app_modern.py
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio pytest-mock

# Run tests using the test script
./run_tests.sh

# Or run pytest directly
pytest tests/ -v

# Run specific test modes
./run_tests.sh phase5  # Test Phase 5 only
./run_tests.sh full    # Run all tests
```

### Adding New Features
1. **New Model Provider**: Add to `models/providers/`
2. **New Tool**: Add to `tools/property_tools.py`
3. **New UI Component**: Add to `ui/components/`
4. **New Data Schema**: Update `data/schemas.py`

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 🔧 Troubleshooting

### Windows: NumPy Import Error

**Problem:**
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory
```

**Solution:**

1. **Clean reinstall (Recommended)**:
```powershell
# Deactivate and remove virtual environment
deactivate
Remove-Item -Recurse -Force venv

# Create fresh virtual environment
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Upgrade pip and setuptools
python -m pip install --upgrade pip setuptools wheel

# Install numpy first
python -m pip install "numpy>=1.24.0,<2.0.0"

# Install remaining dependencies
python -m pip install -r requirements.txt

# Verify installation
python -c "import numpy; print(f'NumPy {numpy.__version__} installed successfully')"
```

2. **Alternative: Install with cache clearing**:
```powershell
python -m pip cache purge
python -m pip install --no-cache-dir -r requirements.txt
```

3. **Check for conflicts**:
```powershell
# Ensure no numpy folder in project directory
Get-ChildItem -Path . -Filter "numpy" -Recurse -Directory | Remove-Item -Recurse -Force

# Restart terminal and try again
```

### Windows: Pandas C Extension Error

**Problem:**
```
ModuleNotFoundError: No module named 'pandas._libs.pandas_parser'
```

**Root Cause:** Pandas C extensions failed to compile or load properly on Windows.

**Solution:**

1. **Install Microsoft C++ Build Tools** (if not installed):
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "Desktop development with C++" workload
   - Restart your computer after installation

2. **Clean reinstall with pre-built wheels**:
```powershell
# Deactivate and remove virtual environment
deactivate
Remove-Item -Recurse -Force venv

# Create fresh virtual environment
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Upgrade pip and tools
python -m pip install --upgrade pip setuptools wheel

# Install numpy first (IMPORTANT!)
python -m pip install "numpy>=1.24.0,<2.0.0"

# Install pandas separately with no cache
python -m pip install --no-cache-dir --force-reinstall "pandas>=2.2.0,<2.3.0"

# Install remaining dependencies
python -m pip install -r requirements.txt

# Verify installations
python -c "import numpy; import pandas; print(f'NumPy {numpy.__version__}, Pandas {pandas.__version__} OK')"
```

3. **Alternative: Use Microsoft Store Python** (often more compatible):
```powershell
# Install Python from Microsoft Store
# Search "Python 3.11" in Microsoft Store and install

# Then follow the clean reinstall steps above
```

### Windows: Pydantic C Extension Error

**Problem:**
```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

**Root Cause:** Pydantic-core C extensions failed to load. This is another binary extension issue on Windows.

**Solution:**

**Quick Fix — Use the updated launcher:**
```powershell
# Run the modern launcher (handles C extensions order automatically)
.\run_modern.ps1
```

The updated `run_modern.ps1` script installs packages in the correct order:
1. numpy (math operations)
2. pydantic-core (data validation core)
3. pandas (data processing)
4. Everything else

**Manual Fix:**
```powershell
# Remove virtual environment
deactivate
Remove-Item -Recurse -Force venv

# Create fresh environment
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Upgrade tools
python -m pip install --upgrade pip setuptools wheel

# Install in correct order (IMPORTANT!)
python -m pip install "numpy>=1.24.0,<2.0.0"
python -m pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0"
python -m pip install --no-cache-dir "pandas>=2.2.0,<2.3.0"
python -m pip install -r requirements.txt

# Verify
python -c "import numpy; import pandas; import pydantic; print('All OK!')"

# Run app
streamlit run app_modern.py
```

**Why this happens:**
- Python packages with C extensions (numpy, pandas, pydantic-core) need to be compiled for Windows
- pip tries to use pre-built wheels, but sometimes they conflict
- Installing them separately with `--no-cache-dir` ensures clean installation

### Common Issues

**Port already in use (8501)**:
```bash
# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8501 | xargs kill -9
```

**API Key not recognized**:
- Ensure `.env` file is in project root
- Check for extra spaces or quotes in `.env`
- Restart the application after editing `.env`

**ChromaDB persistence issues**:
```bash
# Remove and recreate vector store
rm -rf chroma_db/
# Restart app - it will recreate the database
```

---

## 📄 License

This project is licensed under the Apache 2.0 License — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Alex Nesterovich**
- GitHub: [@AleksNeStu](https://github.com/AleksNeStu)
- Repository: [ai-real-estate-assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)

---

## 🙏 Acknowledgments

- [LangChain](https://langchain.com) for the AI framework
- [Streamlit](https://streamlit.io) for the UI framework
- [OpenAI](https://openai.com), [Anthropic](https://anthropic.com), [Google](https://ai.google), and [Ollama](https://ollama.ai) for AI models
- [ChromaDB](https://www.trychroma.com) for vector storage

---

## 📞 Support

For questions or issues:
- Create an [Issue](https://github.com/AleksNeStu/ai-real-estate-assistant/issues)
- Check existing [Discussions](https://github.com/AleksNeStu/ai-real-estate-assistant/discussions)
- Review the [PRD](docs/PRD.MD) for detailed specifications

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with ❤️ using Python, LangChain, and Streamlit

Copyright © 2025 [Alex Nesterovich](https://github.com/AleksNeStu)

</div>
---

## 📦 Downloads

You can download source archives directly from GitHub for the latest development branch (V3) and the stable legacy branch (V2).

| Version | Branch | Download | SHA256 | Notes |
|--------:|:------:|:---------|:------:|:------|
| V3 (Dev) | main | https://github.com/AleksNeStu/ai-real-estate-assistant/archive/refs/heads/main.zip | compute locally | Active development; breaking changes possible |
| V2 (Stable) | ver2 | https://github.com/AleksNeStu/ai-real-estate-assistant/archive/refs/heads/ver2.zip | compute locally | Stable legacy version without ongoing improvements |

Verify integrity:
- Windows PowerShell: `Get-FileHash .\ai-real-estate-assistant-main.zip -Algorithm SHA256`
- macOS/Linux: `shasum -a 256 ai-real-estate-assistant-main.zip`

---

## 📈 Statistics

- Performance (indicative, varies by dataset and model):
  - Simple RAG queries: 1–2s
  - Filtered search + reranking: 2–3s
  - Price analysis (hybrid): 5–10s
  - Comparison (hybrid): 6–12s
- Resource usage (typical dev machine):
  - Memory: 300–800MB (Streamlit server + Python + Chroma, depends on dataset size)
  - Disk: ChromaDB persist directory grows with dataset size
  - CPU: spikes during embedding and analytics; steady during interaction
- Market Insights:
  - City price indices (avg/median, price per sqm)
  - Geospatial radius filters around selected city

---

## ⚙️ System Requirements & Compatibility

- OS: Windows 11, macOS 13+, Ubuntu 22.04+
- Python: 3.11+
- Optional: Node.js for Playwright screenshots (`npx playwright install`)
- RAM: 4GB minimum (8GB recommended; 16GB for large datasets)
- Disk: ≥1GB free (increase for persistent ChromaDB)
- Browser: Modern Chromium/Firefox/WebKit
