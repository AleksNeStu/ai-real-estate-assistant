# [💬 AI Real Estate Assistant App](https://ai-real-estate-assistant.streamlit.app/)

## Overview
The AI Real Estate Assistant is a conversational AI application designed to help real estate agencies assist potential buyers and renters in finding their ideal properties. The application uses natural language processing and machine learning to understand user preferences and recommend suitable properties from a database.

For detailed project requirements and specifications, see the [Product Requirements Document](PRD.MD).

## Features
- **Natural Language Conversation**: Engage users in a natural conversation about their property preferences
- **Property Search & Filtering**: Search properties based on location, budget, type, features, and more
- **Multiple Data Sources**: Support for local CSV files and external data sources via URLs
- **Flexible LLM Integration**: Support for OpenAI GPT models and open-source alternatives
- **Responsive Web Interface**: Easy-to-use Streamlit-based user interface

## Technology Stack
- **Frontend**: Streamlit
- **Backend**: Python (3.11+)
- **AI/ML**: LangChain, OpenAI GPT models, Llama models
- **Data Processing**: Pandas, FastEmbed
- **Vector Storage**: DocArrayInMemorySearch, ChromaDB
- **Package Management**: Poetry

## Project Structure
```
├── ai/                    # AI agent implementation
├── app.py                 # V1 application
├── app_v2.py              # V2 application
├── assets/                # Screenshots and images
├── common/                # Common configurations
├── data/                  # Data loading modules
├── dataset/               # Sample datasets
├── pyproject.toml         # Poetry dependencies
├── README.md              # This file
├── PRD.MD                 # Product Requirements Document
├── run_v1.sh              # Script to run V1
├── run_v2.sh              # Script to run V2
├── streaming.py           # Streaming utilities
├── TODO.MD                # Todo list
├── utils/                 # Utility scripts
└── utils.py               # Helper functions
```

## Project Versions

### V1: Pandas DataFrame Agent
- Used `langchain_experimental.agents.agent_toolkits.pandas.base.create_pandas_dataframe_agent`
- Basic property search functionality with single-turn conversations
- Run with: [run_v1.sh](run_v1.sh) | Application file: [app.py](app.py)

![V1 Screenshot](assets/screen.png)

### V2: RAG with Multiple LLM Support
- Uses different LLM models (OpenAI GPT, Llama)
- Implements RAG with `ConversationalRetrievalChain` for multi-turn conversations
- Enhanced property search and filtering capabilities
- Run with: [run_v2.sh](run_v2.sh) | Application file: [app_v2.py](app_v2.py)

![V2 Screenshot](assets/screen2.png)

### TODO:
- Fix "get db freeze" issue
- Comprehensive testing of the application
- Add property visualization features
- Implement additional data sources

[//]: # (![demo.gif]&#40;assets/demo.gif&#41;)

## Architecture
The application follows a modular architecture with the following components:

1. **User Interface**: Streamlit-based web interface
2. **AI Agent**: LLM-powered conversational agent
3. **Data Processing**: CSV loaders and data formatters
4. **Data Storage**: In-memory database and vector stores

## Data Format
The application uses CSV datasets with the following structure. Datasets can be loaded from local files or remote URLs.
## DataFrame Columns

This table describes the columns in the DataFrame:

| Column Name              | Description                                |
|--------------------------|--------------------------------------------|
| `id`                     | Unique identifier for each record.         |
| `city`                   | Name of the city where the property is located. |
| `type`                   | Type of property (e.g., apartment, house). |
| `square_meters`          | Area of the property in square meters.     |
| `rooms`                  | Number of rooms in the property.           |
| `floor`                  | Floor number where the property is located. |
| `floor_count`            | Total number of floors in the building.    |
| `build_year`             | Year the building was constructed.         |
| `latitude`               | Latitude coordinate of the property.       |
| `longitude`              | Longitude coordinate of the property.      |
| `centre_distance`        | Distance from the property to the city center. |
| `poi_count`              | Number of Points of Interest nearby.       |
| `school_distance`        | Distance to the nearest school.            |
| `clinic_distance`        | Distance to the nearest clinic.            |
| `post_office_distance`   | Distance to the nearest post office.       |
| `kindergarten_distance`  | Distance to the nearest kindergarten.      |
| `restaurant_distance`    | Distance to the nearest restaurant.        |
| `college_distance`       | Distance to the nearest college.           |
| `pharmacy_distance`      | Distance to the nearest pharmacy.          |
| `ownership`              | Type of ownership (e.g., condominium).     |
| `building_material`      | Material used in the construction of the building. |
| `condition`              | Condition of the property (e.g., new, good). |
| `has_parking_space`      | Whether the property has a parking space (`True`/`False`). |
| `has_balcony`            | Whether the property has a balcony (`True`/`False`). |
| `has_elevator`           | Whether the building has an elevator (`True`/`False`). |
| `has_security`           | Whether the property has security (`True`/`False`). |
| `has_storage_room`       | Whether the property has a storage room (`True`/`False`). |
| `price`                  | Price of the property.                     |
| `price_media`            | Median price of similar properties.        |
| `price_delta`            | Difference between the property's price and `price_media`. |
| `negotiation_rate`       | Possibility of negotiation (e.g., High, Medium, Low). |
| `bathrooms`              | Number of bathrooms in the property.       |
| `owner_name`             | Name of the property owner.                |
| `owner_phone`            | Contact phone number of the property owner. |
| `has_garden`             | Whether the property has a garden (`True`/`False`). |
| `has_pool`               | Whether the property has a pool (`True`/`False`). |
| `has_garage`             | Whether the property has a garage (`True`/`False`). |
| `has_bike_room`          | Whether the property has a bike room (`True`/`False`). |



## Getting Started

### Prerequisites
- Python 3.11 or later
- [Poetry](https://python-poetry.org/) for dependency management
- OpenAI API Key (optional, for GPT models)

### Installation

#### 1. Clone the repository
```sh
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant
```

#### 2. Set up Poetry environment
```sh
# Install pip and poetry if needed
python -m ensurepip --upgrade
curl -sSL https://install.python-poetry.org | python3 - --version 1.7.0

# Configure Poetry
poetry config virtualenvs.in-project true
poetry config virtualenvs.prompt 'ai-real-estate-assistant'

# Install dependencies
poetry install --no-root
```

#### 3. Activate the virtual environment
```sh
source .venv/bin/activate
```

#### 4. Set up environment variables
Create a `.env` file in the project root with the following contents:
```
OPENAI_API_KEY=your-api-key-here
```

### Running the Application

#### Local Development
Run either version of the application:
```sh
# Run V1
streamlit run app.py
# OR
./run_v1.sh

# Run V2
streamlit run app_v2.py
# OR
./run_v2.sh
```

For additional configuration options:
```sh
# Local run with custom settings
./utils/run_local.sh
```

### Deployment

#### Streamlit Cloud Deployment
This application can be deployed to Streamlit Cloud. For details, see the [Streamlit Deployment Documentation](https://docs.streamlit.io/deploy).

#### Docker Deployment
```sh
# Build and run Docker container
./utils/run_docker.sh
```

#### Development Container
```sh
# Run in development container
./utils/run_dev_container.sh
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
