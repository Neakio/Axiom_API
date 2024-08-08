# ------------------------------ PACKAGES ------------------------------
# Independant packages
from psycopg2 import sql, connect

# General packages
from dotenv import load_dotenv
import os
import subprocess

# Internal packages
import functions.utils as utils


# ------------------------------ SETUP ------------------------------
def setup_db():
    """Create the API database with its user and the table users"""
    utils.db_log("Begin database setup ...")
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Fetch variables from .env
        DB_NAME = os.getenv("DB_NAME")
        DB_USERNAME = os.getenv("DB_USERNAME")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        conn = None
        # Establish connection to PostgreSQL server
        conn = connect(
            dbname="postgres",
            user="postgres",
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Create a new database
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        utils.db_log("New database created")
        # Create the new user
        cursor.execute(
            sql.SQL("CREATE USER {} WITH PASSWORD %s").format(
                sql.Identifier(DB_USERNAME)
            ),
            [DB_PASSWORD],
        )
        utils.db_log("New user created")

        # Grant all privileges on the new database to the new user
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(DB_NAME), sql.Identifier(DB_USERNAME)
            )
        )

        # Disable the default 'postgres' superuser by revoking its login privilege
        cursor.execute("ALTER USER postgres NOLOGIN")
        utils.db_log("Default user login revoked")

        utils.db_log(
            f"Database '{DB_NAME}' and user '{DB_USERNAME}' created successfully."
        )
        utils.db_log("The 'postgres' superuser has been disabled.")

    except Exception as e:
        utils.db_log(f"DATABASE ERROR, error during setup : {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

    try:
        # Connect to the newly created database
        conn = connect(dbname=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD)
        conn.autocommit = True  # Ensure autocommit is enabled

        # Create the 'users' table
        cursor = conn.cursor()
        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                surname VARCHAR(50),
                firstname VARCHAR(50),
                email VARCHAR(100) UNIQUE,
                hashed_password VARCHAR(100),
                disabled BOOLEAN DEFAULT FALSE
            )
        """)
        cursor.execute(create_table_query)
        utils.db_log("Table 'users' created successfully.")
    except Exception as e:
        utils.db_log(f"DATABASE ERROR, error during table creation : {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()


# ------------------------------ CHECKER ------------------------------
def check_db_status():
    """Look at PostSQL status with the password provided in the .env. Start the service if not already up."""
    load_dotenv()
    sudo_password = os.getenv("USER_PASSWORD")
    try:
        # Check the status of the PostgreSQL service using sudo
        status_command = ["sudo", "-S", "systemctl", "is-active", "postgresql"]
        process = subprocess.Popen(
            status_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=sudo_password.encode() + b"\n")

        status = stdout.decode().strip()

        if status == "active":
            utils.db_log("PostgreSQL is running.\n")
        else:
            utils.db_log(
                "PostgreSQL is not running. Attempting to start the service ..."
            )
            start_postgres(sudo_password)
    except subprocess.CalledProcessError as e:
        error_message = e.output.decode().strip()
        if (
            "inactive" in error_message
            or "failed" in error_message
            or "unknown" in error_message
        ):
            utils.db_log(
                f"DATABSE ERROR, PostgreSQL status: {error_message}. Attempting to start the service ..."
            )
            start_postgres(sudo_password)
        else:
            utils.db_log(f"Error checking PostgreSQL status: {error_message}")
    return


def start_postgres(sudo_password):
    try:
        # Start the PostgreSQL service using sudo
        start_command = ["sudo", "-S", "systemctl", "start", "postgresql"]
        process = subprocess.Popen(
            start_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=sudo_password.encode() + b"\n")

        if process.returncode == 0:
            utils.db_log("PostgreSQL service started successfully.\n")
        else:
            utils.db_log(
                f"DATABASE ERROR, Error starting PostgreSQL service: {stderr.decode().strip()}"
            )
    except subprocess.CalledProcessError as e:
        utils.db_log(
            f"DATABASE ERROR, Error starting PostgreSQL service: {e.output.decode().strip()}"
        )
    return


if __name__ == "__main__":
    check_db_status()
