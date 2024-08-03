import os
from pathlib import Path
from yarl import URL
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
dataset_dir_pl = dataset_dir / "pl"
poland_csv = dataset_dir_pl / "apartments_rent_pl_2024_06.csv"


# NOTE: Can be used for data generation
# https://faker.readthedocs.io/en/master/locales/pl_PL.html
fake_pl = Faker('pl_PL')  # for Poland
# https://faker.readthedocs.io/en/master/locales/en_US.html
fake_en = Faker('en_US')  # for US

GIT_FS_DATA_SET = URL("https://raw.githubusercontent.com/AleksNeStu/ai-real-estate-assistant/main/dataset/")
GIT_FS_DATA_SET_PL1 = URL("https://github.com/AleksNeStu/ai-real-estate-assistant/blob/main/dataset/pl"
                      U"/apartments_rent_pl_2024_06.csv")
GIT_FS_DATA_SET_PL = GIT_FS_DATA_SET / 'pl/apartments_rent_pl_2024_04.csv'