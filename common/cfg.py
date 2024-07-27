import io
import os
import pickle
from functools import wraps
from pathlib import Path
from types import SimpleNamespace

import torch
from dotenv import find_dotenv, load_dotenv
import inspect
import openai
import contextlib

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

device = "cuda" if torch.cuda.is_available() else "cpu"
# You can set compute_type to "float32" or "int8".
# Since your GPU does not support float16, you should set "int8" and not "int8_float16".
compute_type = "float16" if device == "cuda" else "int8"



# Interactive or not
def get_is_interactive():
    try:
        __file__
        return False
    except NameError:
        return True
is_interactive = get_is_interactive()

# Prepare a StringIO object to capture the stdout
log_stream = io.StringIO()


# Helpers
def dump_data(data_obj: object, data_path: Path):
    with open(data_path, "wb") as f:
        pickle.dump(data_obj, f)


def load_data(data_path: Path):
    with open(data_path, "rb") as f:
        res = pickle.load(f)
    return res


def get_func_data_path(func, current_dir):
    f_name = get_func_data_path.__name__
    data_path = current_dir / f'{f_name}.pkl'
    return data_path




def get_data(file = None, load = True, log = True, *args, **kwargs):
    caller_file = file if file else inspect.stack()[1].filename

    def decorator(func):

        def get_data_path(func):
            current_dir = Path(caller_file).parent.resolve()
            func_name = func.__name__
            data_path = current_dir / f'{func_name}.pkl'
            return data_path

        data_path = get_data_path(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            final_result = SimpleNamespace(log=None, err=None, res=None)

            if data_path.exists() and load and data_path.stat().st_size > 0:
                res_err = getattr(final_result, 'err', None)
                # Do not load res if last result was with error
                if not res_err:
                    final_result = load_data(data_path)
            else:
                try:
                    res = None
                    # Capture the verbose output during agent initialization
                    if log:
                        with contextlib.redirect_stdout(log_stream):
                            res = func(*args, *kwargs)
                        final_result.log = log_stream.getvalue()
                    else:
                        res = func(*args, *kwargs)
                except Exception as ex:
                    print(f'Error for running `{func.__name__}`: {ex}')
                    final_result.err = ex

                # Retrieve the log from the StringIO object
                final_result.res = res

                dump_data(final_result, data_path)
            return final_result

        return wrapper

    return decorator