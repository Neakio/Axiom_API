# FastAPI with PostgreSQL, Axiom, and AWS

This project is a FastAPI application that handles user requests for domain scanning using Axiom. It integrates PostgreSQL for database management, JWT for security, and uses Python subprocess to execute Axiom commands. The scan results are then uploaded to an S3 bucket. The entire setup is deployed on an AWS EC2 instance.

## Features

- **FastAPI**: Web framework for building APIs.
- **PostgreSQL**: Database for storing user information.
- **JWT (JSON Web Tokens)**: Secure user authentication.
- **Axiom**: Tool for domain scanning.
- **AWS S3**: Storage for scan results.
- **AWS EC2**: Deployment environment.
- **AWS Secret**: Admin credential.


## Prerequisites

- An EC2 instance with Amazon Linux 2 or Ubuntu
- Python 3.8+
- AWS account with S3 bucket (dnsscan)
- Secret on AWS Secret Manager (AxiomAPI_OAuth)
- Axiom installed on the EC2

## Installation

### Setting Up EC2 Instance

1. **Launch EC2 Instance**:
    
    - Launch a new EC2 instance using Amazon Linux 2 or Ubuntu.
    - Configure security groups to allow inbound traffic on port 8000 (or your preferred port) and SSH access.
    

2. **Connect to EC2 Instance**:
    
	```bash
    ssh -i your-key.pem ec2-user@your-ec2-public-ip
	```
    
3. **Clone the repository**:
    
	```bash
    git clone https://github.com/your-repo/fastapi-axiom.git cd API
	```
    
4. **Create a virtual environment and install dependencies**:
    
	```bash
    python3 -m venv venv source venv/bin/activate pip install -r requirements.txt
	```
    
5. **Install and Configure Axiom**:
    
	```bash
    bash <(curl -s https://raw.githubusercontent.com/pry0cc/axiom/master/interact/axiom-configure)
	```

6. **Install Postgresql and edit config file**:
    
	```bash
    sudo apt-get install postgresql
    sed -i '/^local   all             postgres                                peer/i\local   all             postgres                                trust\nlocal   all             all                                     password' /etc/postgresql/14/main/pg_hba.conf
    systemctl restart postgresql
	```

7. **Configure environment variables**:
    
    - Create a `.env` file in the project root and add 
      - USER_PASSWORD : the user password for sudo command execution
      - BUCKET_NAME : AWS S3 Bucket name
      - REGION_NAME : AWS Region of your ressources
      - SECRET_NAME : AWS Secret name of the admin token
      
8. **Start the FastAPI server**:
    
	```bash
    uvicorn app:app --host 0.0.0.0 --port 8000
    OR
    python3 main.py
	```
    

## Usage

### User Authentication
On admin side : 
- **Register**: `POST /users`
  - Body: `{
  "surname": "user",
  "firstname": "user",
  "email": "user@example.com",
  "password": "user"
}`

On user side : 
- **Login**: `POST /token`
  - Body: `{ "username": "user@example.com", "password": "user"}`

### Domain Scanning

- **Request Scan**: `GET /scans`
    - Parameters: ?q={module}&domain={domain}
  
- **Request Scan**: `POST /scans`
    - Parameters: ?q={module}
    - Body: File


## Modules

| Query      | Usage                             | Tool      | Valid outputs        | Exact command                              |
|------------|-----------------------------------|-----------|----------------------|--------------------------------------------|
| ip_list    | Retrieve IP addresses of domains  | DnsX      | default (txt)        | dnsx -re                                   |
| dns_list   | Discover subdomains               | Amass     | default (txt)        | amass                                      |
| web_list   | Enumerate Web directories and files| Gau      | default (txt)<br>json| gau                                        |
| waf_check  | Detect and identify WAF protection| Wafw00f   | default (txt)        | wafw00f                                    |
| ssl_check  | Analyse SSL/TLS configurations    | Testssl   | default (txt)<br>HTML | testssl                                    |
| http_check | Check for reachable website       | HTTPX     | default (txt)        | httpx -fr -sc -location -title -method     |
| port_scan  | Identify open ports and running services| Nmap | default (txt)<br>xml/html | nmap -sV -sC                          |
| web_scan   | Retrieve global website data      | Aquatone  | default (folder)     | aquatone                                   |
| dns_check  | Retrieve domain data              | Whois     | default (folder)     | whois                                      |
