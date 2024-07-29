import os
from pathlib import Path

import openai
from dotenv import find_dotenv, load_dotenv
from faker import Faker

# Load environment variables
env_file = find_dotenv()
load_dotenv(env_file, override=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
HUGGINGFACEHUB_API_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
LANGCHAIN_API_KEY = os.environ.get("LANGCHAIN_API_KEY")

openai.api_key = OPENAI_API_KEY


# Set paths and cfg parts
current_dir = Path(__file__).parent.resolve()
root_dir = Path(__file__).parent.parent.resolve()
dataset_dir = root_dir / "dataset"
poland_csv = dataset_dir / "apartments_rent_pl_2024_06.csv"


# NOTE: Can be used for data generation
# https://faker.readthedocs.io/en/master/locales/pl_PL.html
fake_pl = Faker('pl_PL')  # for Poland
# https://faker.readthedocs.io/en/master/locales/en_US.html
fake_en = Faker('en_US')  # for US