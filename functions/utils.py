# ------------------------------ PACKAGES ------------------------------
# Standard imports
import asyncio
import json
import subprocess
from csv import reader
from datetime import datetime
from enum import Enum
from io import StringIO
from json import loads, dump, load
from os import path, getenv
from random import choice
from re import search, findall
from secrets import token_hex
from string import ascii_letters, digits

# Third-party libraries
from sqlalchemy.inspection import inspect


# ------------------------------ .ENV UTILS ------------------------------
def generate_secret_key(length=32):
    return token_hex(length)


def generate_random_string(length=16):
    letters = ascii_letters + digits
    return "".join(choice(letters) for i in range(length))


def generate_db_cred():
    db_user = generate_random_string(12)
    db_password = generate_random_string(16)
    return (db_user, db_password)


def read_env():
    """Read .env file and return its contents as a dictionary"""
    env_vars = {}
    if path.isfile(".env"):
        with open(".env", "r") as env:
            for line in env:
                key, value = line.strip().split("=", 1)
                env_vars[key] = value
    return env_vars


def check_env():
    """Check if required environment variables are present"""
    required_vars = [
        "SECRET_KEY",
        "ALGORITHM",
        "DB_NAME",
        "DB_USERNAME",
        "DB_PASSWORD",
        "DATABASE_URL",
    ]
    env_vars = read_env()
    return all(var in env_vars for var in required_vars)


def create_env():
    """Generate .env file using random credentials"""
    api_log("Generating environment variables ...")
    key = generate_secret_key()
    db_user, db_password = generate_db_cred()
    with open(".env", "a") as env:
        env.write("SECRET_KEY=" + key + "\n")
        env.write("ALGORITHM=HS256\n")
        env.write("DB_NAME=axiom_api\n")
        env.write(f"DB_USERNAME={db_user}\n")
        env.write(f"DB_PASSWORD={db_password}\n")
        env.write(
            f"DATABASE_URL=postgresql+asyncpg://{db_user}:{db_password}@localhost/axiom_api\n"
        )
    api_log("Environment variables created.")
    return


# ------------------------------ API UTILS ------------------------------
# Load JSON data
def load_json():
    """Update and read the cases.json file. If it doesn't exist, create an empty that will be updated.

    Returns:
        list: Three lists that contains the valid input for each choices (profiles, formats, workflows)
    """
    file_path = "./data/cases.json"
    if not path.exists(file_path):
        # Create the file with default content if it doesn't exist
        default_content = {"profiles": [], "formats": [], "workflows": []}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_content, f, indent=4)
    update_cases()
    # Load the JSON data from the file
    with open(file_path, "r", encoding="utf-8") as f:
        data = load(f)

    return data["profiles"], data["formats"], data["workflows"]


# Create an enum from values
def create_enum(name, values):
    return Enum(name, {value: value for value in values})


# Convert a SQLAlchemy model instance to a dictionary.
def to_dict(model_instance):
    return {
        c.key: getattr(model_instance, c.key)
        for c in inspect(model_instance).mapper.column_attrs
    }


# Removes 'hashed_password' and 'id' from a single user dictionary.
def clean_user_data(user_data):
    """Remove unecessary data to display

    Args:
        user_data (dict): Contains every user data

    Returns:
        dict: Contains only firstname, surname, email, disabled
    """
    if not isinstance(user_data, dict):
        user_data = to_dict(user_data)

    user_data.pop("hashed_password", None)
    user_data.pop("id", None)

    return user_data


# Removes 'hashed_password' and 'id' from a list of user dictionaries.
def clean_users_data(users_data):
    return [clean_user_data(user) for user in users_data]


# ------------------------------ SCAN UTILS ------------------------------
# TODO
def save_to_dynamo(input):
    return


# TODO
def save_to_bucket(input):
    subprocess.run(
        [f"aws s3 cp /var/tmp/scan_output/{input} s3://{bucket}/scan_output/{input}"],
        shell=True,
        check=False,
    )
    axiom_log(f"Saving {input} in S3 bucket.")
    return


def add_https_to_each_line(input):
    axiom_log("Parsing input for web request (https/http)")
    with open(f"/var/tmp/scan_input/{input}", "r", encoding="utf-8") as file:
        lines = file.readlines()
    modified_lines = []
    for line in lines:
        line = line.strip()
        if not line.startswith("https://"):
            line = "https://" + line
        modified_lines.append(line + "\n")
    with open(f"/var/tmp/scan_input/{input}", "w", encoding="utf-8") as file:
        file.writelines(modified_lines)
    return


def count_lines_in_txt(file: str):
    with open(file, 'r', encoding="utf-8") as content:
        lines = content.readlines()
    return len(lines)


def count_entries_in_json(file: str):
    with open(file, 'r', encoding="utf-8") as content:
        data = loads(content)
    if isinstance(data, list):
        return len(data)
    return 1


def count_rows_in_csv(file: str) -> int:
    with open(file, 'r', encoding="utf-8") as content:
        read = reader(StringIO(content))
    row_count = sum(1 for row in read)
    return row_count


# Determine the number of instances based on the line count and config.json
async def instances_needed(count: int):
    with open("./data/config.json", encoding="utf-8") as config_file:
        range_config = load(config_file)
    for range_entry in range_config:
        if range_entry["min_lines"] <= count <= range_entry["max_lines"]:
            number = range_entry["instances"]
    axiom_log(f"Axiom fleet initialized with {number} instance (for {count} lines):")
    await start_instances(number)
    return


async def start_instances(number: int):
    axiom_path = getenv("AXIOM_PATH")
    await asyncio.sleep(30)
    result = subprocess.run(
        [f"{axiom_path}axiom-power on 'axiom_node_*' -i {number}"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    axiom_log(result.stdout)
    if result.stderr:
        await init_instances()

    await asyncio.sleep(210)
    command = (
        f"{axiom_path}axiom-ls --json --skip | "
        "jq -r '.Reservations[].Instances[] | "
        'select(.Tags[]?.Value | contains("axiom_node")) | '
        ". as $instance | "
        "$instance.Tags[] | "
        'select(.Key == "Name") | '
        "[.Value, $instance.PublicIpAddress] | "
        "@tsv'"
    )
    result = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    axiom_log(result.stdout)
    return result.stdout


def stop_instances():
    axiom_path = getenv("AXIOM_PATH")
    result = subprocess.run(
        [f"{axiom_path}axiom-power off 'axiom_node_*'"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    axiom_log(result.stdout)
    axiom_log("Axiom fleet stopped")
    return


def init_instances():
    axiom_path = getenv("AXIOM_PATH")
    result = subprocess.run(
        [f"{axiom_path}axiom-fleet 'axiom_node_' -i 10"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    axiom_log(result.stdout)
    return


# ------------------------------ UPDATE UTILS ------------------------------
def extract_profiles(file_content):
    match_block_pattern = r"match profile:\n((?:\s*case .+?:(?:\n|.)*?)+)(?=\n\s*utils.axiom)"
    match_block = search(match_block_pattern, file_content)
    if match_block:
        block_content = match_block.group(1)
        case_pattern = r"case \"([^\"]+)\""
        profiles = findall(case_pattern, block_content)
        return profiles
    return []


def extract_formats(file_content):
    match_block_pattern = r"match format:\n((?:\s*case .+?:(?:\n|.)*?)+)(?=\n\s*utils.axiom)"
    match_block = search(match_block_pattern, file_content)
    if match_block:
        block_content = match_block.group(1)
        case_pattern = r"case \"([^\"]*)\"(?:\s*\|\s*\"([^\"]*)\")?"
        formats = findall(case_pattern, block_content)
        formats = [fmt for sublist in formats for fmt in sublist if fmt]
        formats = list(set(formats))  # Remove duplicates
        return formats
    return []


def extract_workflows(file_content):
    match_block_pattern = r"match workflow:\n((?:\s*case .+?:(?:\n|.)*?)+)(?=\n\s*utils.axiom)"
    match_block = search(match_block_pattern, file_content)
    if match_block:
        block_content = match_block.group(1)
        case_pattern = r"case \"([^\"]+)\""
        workflows = findall(case_pattern, block_content)
        return workflows
    return []


def update_cases():
    """Read the content of scan.py and extract possible profiles, workflows and formats and save it inside the json"""
    source_file = "./functions/scan.py"
    json_file = "./data/cases.json"
    with open(source_file, "r", encoding="utf-8") as file:
        file_content = file.read()

    # Extract up to date profiles, formats and workflows
    profiles = extract_profiles(file_content)
    formats = extract_formats(file_content)
    workflows = extract_workflows(file_content)

    data = {"profiles": profiles, "workflows": workflows, "formats": formats}
    # Save to JSON
    with open(json_file, "w", encoding="utf-8") as file:
        dump(data, file, indent=4)
    return


# ------------------------------ LOG UTILS ------------------------------
def axiom_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(message, bytes):
        formatted_message = message.decode("utf-8").strip()
    else:
        formatted_message = str(message).strip()
        formatted_message = f"{timestamp} - {message}"
        if "error" in message.lower():
            formatted_message = f"\033[91m{formatted_message}\033[0m"
        elif any(
            keyword in message.lower()
            for keyword in ["success", "successful", "successfully"]
        ):
            formatted_message = f"\033[92m{formatted_message}\033[0m"

    with open("/var/log/dnsscan/axiom.log", mode="a", encoding="utf-8") as log:
        log.write(formatted_message + "\n")
    return


def api_log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(message, bytes):
        formatted_message = message.decode("utf-8").strip()
    else:
        formatted_message = str(message).strip()
        formatted_message = f"{timestamp} - {message}"
        if any(keyword in message.lower() for keyword in ["error", "failed", "fail"]):
            formatted_message = f"\033[91m{formatted_message}\033[0m"
        elif any(
            keyword in message.lower()
            for keyword in ["success", "successful", "successfully"]
        ):
            formatted_message = f"\033[92m{formatted_message}\033[0m"
        if "monitoring" in message.lower():
            formatted_message = f"\033[93m{formatted_message}\033[0m"
        if "startup" in message.lower():
            formatted_message = f"\n\n{formatted_message}"

    with open("/var/log/dnsscan/api.log", mode="a", encoding="utf-8") as log:
        log.write(formatted_message + "\n")
    return


def db_log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(message, bytes):
        formatted_message = message.decode("utf-8").strip()
    else:
        formatted_message = str(message).strip()
        formatted_message = f"{timestamp} - {message}"
        if "error" in message.lower():
            formatted_message = f"\033[91m{formatted_message}\033[0m"
        elif any(
            keyword in message.lower()
            for keyword in ["success", "successful", "successfully"]
        ):
            formatted_message = f"\033[92m{formatted_message}\033[0m"
        if "setup" in message.lower():
            formatted_message = f"\n\n{formatted_message}"

    with open("/var/log/dnsscan/database.log", mode="a", encoding="utf-8") as log:
        log.write(formatted_message + "\n")
    return


def cert_json(assets, tool, time_range):
    axiom_path = getenv("AXIOM_PATH")
    date = datetime.now().strftime("%Y-%m-%d")
    command = (
        f"{axiom_path}axiom-ls --json --skip | "
        "jq -r '.Reservations[].Instances[] | "
        "select(.Tags[]?.Value | contains(\"axiom_node\")) | "
        "select(.PublicIpAddress != null) | "
        ".PublicIpAddress'"
    )
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=False
    )
    ip = result.stdout.strip().splitlines()

    scan = {"assets": assets, "ip": ip, "command": tool}
    json_file = "/var/log/dnsscan/cert.json"

    if path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as file:
            existing_data = json.load(file)
    else:
        existing_data = {}

    if date not in existing_data:
        existing_data[date] = {}
    existing_data[date][time_range] = scan

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(existing_data, file, indent=4)
