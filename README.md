# [💬 AI Real Estate Assistant App](https://ai-real-estate-assistant.streamlit.app/)

## Requirements
Develop an AI-powered assistant for a real estate agency that assists potential buyers and renters in finding their ideal property.

The assistant should engage users in a conversation, asking questions about their preferences such as:
- location (city, neighborhood)
- budget range
- property type (apartment, house, condo)
- number of bedrooms and bathrooms
- desired amenities (parking, garden, pool)
- proximity to schools or public transportation.

## Init project for development
```sh
# Install pip and poetry
python -m ensurepip --upgrade
curl -sSL https://install.python-poetry.org | python3 - --version 1.7.0
# Init poetry virtual env
poetry init
poetry env use 3.11
poetry config virtualenvs.in-project true
source .venv/bin/activate
poetry config virtualenvs.prompt 'ai-real-estate-assistant'
poetry config --list
# Add deps
poetry add ...
poetry lock
```

## Run project for development
```sh
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
poetry install --no-root
source .venv/bin/activate
```

## Run app

[Local run](utils/run_local.sh)

## Deploy app

[Streamlit Deploy](https://docs.streamlit.io/deploy)
