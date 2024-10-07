# ------------------------------ PACKAGES ------------------------------
# General packages
import asyncio
import subprocess
import pty
from requests import exceptions, post
from datetime import datetime
from os import getenv, path
# Internal packages
import functions.utils as utils



# ------------------------------ PROCESSING ------------------------------
async def processing(q, domain, usecase: bool, output="txt", uuid="", client_ip=""):
    """Prepare API request for the scan and call it

    Args:
        q (str): Profile/Workflow chosen
        domain (str): Input filename
        usecase (bool): Check if a workflow has been requested
        output (str, optional): Output type. Default empty.
        uuid (str, optional): Job UUID, it will be used to send a response and as a str in the filename. Default empty.
        client_ip (str, optional): Requester IP address used to send result. Default empty.
    """
    utils.api_log(
        f"API call received. Start processing for {input} (usecase?:{usecase}). The uuid is {uuid} and client_ip is {client_ip}"
    )
    domain, ext = path.splitext(input)
    current_datetime = datetime.now().strftime("%Y-%m-%d")
    file = f"{current_datetime}_{domain}" if not uuid else f"{current_datetime}_{domain}_{uuid}"
    utils.api_log(f"Output filename: {file}")

    if not usecase:
        code = await scan(input=input, output=file, profile=(q.value), format=output)
    else:
        code = await scan(input={input.filename}, output=file, workflow=(q.value))
    
    status = "completed" if code == 0 else "error"
    
    if uuid and client_ip:
        await notify(status, file, uuid, client_ip)
    return status


# ------------------------- Main scan function -------------------------
async def scan(input, output, profile=None, workflow=None, format=""):
    """Run axiom-scan based on arguments provided

    Args:
        input (str): Input filename
        output (str): Output filename
        profile (str, optional): Single scan case. Defaults to None.
        workflow (str, optional): Workflow case. Defaults to None.
        format (str, optional): Output type. Default empty.

    Returns:
        code: return error/success code
    """
    if format is None:
        format = ""
    tool = None
    outype = None
    count = 0
    utils.axiom_log("-----------------------")
    if profile is not None and workflow is not None:
        utils.axiom_log(
            f"Invalid input. Both profile ({profile}) and workflow ({workflow}) have been provided, discarding scan"
        )
        return 1
    match profile:
        case "ip_list":
            tool = "dnsx -re"
        case "dns_list":
            tool = "amass"
            return
        case "web_list":
            tool = "gau"
        case "waf_check":
            tool = "wafw00f"
            utils.add_https_to_each_line(input)
        case "ssl_check":
            tool = "testssl"
            utils.add_https_to_each_line(input)
        case "http_check":
            tool = "httpx -fr -sc -location -title -method"
        case "dns_check":
            tool = "whois"
            return
        case "web_scan":
            tool = "aquatone"
        case "port_scan":
            tool = "nmap -sV -sC"
        case _:
            if workflow is None:
                utils.axiom_log(f"Invalid profile: {profile}, discarding scan")
                utils.axiom_log("-----------------------")
                return 1
    utils.axiom_log(f"Tool used: {tool}")
    match workflow:
        case "dns_inventory":
            dns(input, output)
            exit
        case "security_inventory":
            security(input, output)
            exit
        case "r2p":
            webapp_inventory(input, output)
            exit
        case "web_inventory":
            web(input, output)
            exit
        case _:
            if profile is None:
                utils.axiom_log(f"Invalid workflow: {workflow}, discarding scan")
                utils.axiom_log("-----------------------")
                return 1
    utils.axiom_log(f"Workflow used: {workflow}")
    match format:
        case "txt":
            outype = "-o"
        case "json":
            outype = "-oJ"
        case "html":
            outype = "-oH"
        case _:
            utils.axiom_log(f"Invalid format: {format}, discarding scan")
            utils.axiom_log("-----------------------")
            return 1
    utils.axiom_log(f"Output format: {outype}")
    count = 0
    # Determine the file type and count the number of lines, entries, or rows
    if ".json" in input:
        count = utils.count_entries_in_json(f"/var/tmp/scan_input/{input}")
    elif ".csv" in input:
        count = utils.count_rows_in_csv(f"/var/tmp/scan_input/{input}")
    elif ".txt" in input:
        count = utils.count_lines_in_txt(f"/var/tmp/scan_input/{input}")
    else:
        utils.axiom_log(f"Incorrect input filename : {input}")

    with open(f"/var/tmp/scan_input/{input}", "r") as file:
        lines_list = [line.strip() for line in file.readlines()]
    await utils.instances_needed(count)  # Start needed instances

    starttime = datetime.now().strftime("%H:%M:%S")
    await axiom(tool, outype, input, f"/var/tmp/scan_output/{output}", profile)
    endtime = datetime.now().strftime("%H:%M:%S")

    utils.save_to_bucket(f"{output}.{format}")

    length = f"{starttime} - {endtime}"
    utils.cert_json(lines_list, tool, length)
    utils.stop_instances()
    subprocess.run(
        [f"rm /var/tmp/scan_input/{input}"],
        shell=True,
        check=False
    )
    utils.axiom_log("-----------------------")
    return 0

async def notify(status, file, uuid, client_ip):
    try:
        callback_url = f"http://{client_ip}/callback"
        response = post(callback_url, json={"status": status, "file": file, "uuid": uuid})
        response.raise_for_status()
    except exceptions.RequestException as e:
        utils.api_log(f"Failed to notify client IP: {client_ip}, error: {e}")

        
# -------------------------- Use case function --------------------------


async def web(input, output):
    path = "/var/tmp/workflow/"
    await axiom("httprobe", "-o", f"/var/tmp/scan_input/{input}", f"{path}httprobe", "web_scan")
    await axiom("nmap", "-o", f"/var/tmp/scan_input/{input}", f"{path}nmap", "web_scan")
    utils.axiom_log("Merging nmap and httprobe result")
    command = f"python3 /home/ubuntu/scripts/url_merge.py -i {path}/nmap.html -o {path}/httprobe -w imperva"
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, process.communicate)

    await axiom("gau", "-oJ", f"{path}dnsx", f"{path}dnsx", "web_scan")
    await axiom("testssl --json", "-o", f"{path}dnsx", f"{path}dnsx", "web_scan")
    await axiom("aquatone", "-oH", f"{path}dnsx", f"{path}dnsx", "web_scan")
    utils.axiom_log("Merging testssl and gau into aquatone report")
    command = f"python3 /home/ubuntu/scripts/merge_webscan.py -a {path}/aquatone.html -g {path}/gau -t {path}/testssl" #TODO finish script
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, process.communicate)

    exit


async def security(input, output):
    path = "/var/tmp/workflow/"
    exit


async def dns(input, output):
    path = "/var/tmp/workflow/"
    exit


async def webapp_inventory(input, output):
    path = "/var/tmp/workflow/"
    await axiom("dnsx", "-o", f"/var/tmp/scan_input/{input}", f"{path}dnsx", "webapp_inventory")
    await axiom("httprobe", "-o", f"{path}dnsx", f"{path}httprobe", "webapp_inventory")

    utils.axiom_log("Adding httprobe result to dnsx")
    command = f"cat {path}httprobe >> {path}dnsx" #TODO check this command
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    await axiom("nmap -p 80,443,8080 -sV -sC", "-oX", f"{path}dnsx", f"{path}nmap", "webapp_inventory") #TODO check nmap output
    utils.axiom_log("Filtering html of nmap result")
    waf = getenv("WAF")
    word = getenv("word")
    command = f"python3 /home/ubuntu/scripts/html_filtering.py -i {path}/nmap.html -o {path}/filtered_nmap.html -w {waf} -u {word}"
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, process.communicate)
    utils.axiom_log("Filtering url of nmap result")
    command = f"python3 /home/ubuntu/scripts/url_filtering.py -i {path}/filtered_nmap.html -o /var/tmp/scan_output/{output} -f csv"
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, process.communicate)


    process = subprocess.Popen(
        f"cp {path}/httprobe /var/tmp/scan_output/{output}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    utils.save_to_bucket(output)
    process = subprocess.Popen(
        f"rm {path}/* ", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    exit



async def axiom(module, outype, input, output, profile):
    axiom_path = getenv("AXIOM_PATH")
    home = getenv("HOME")
    env = {
        "TERM": "xterm",
        "HOME": str(home),
        "PATH": "/home/ubuntu/go/bin:/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/ubuntu/.local/bin:/home/ubuntu/.axiom/interact"
    }
    command = f"{axiom_path}axiom-scan /var/tmp/scan_input/{input} -m {module} {outype} {output}"
    utils.axiom_log(f"Start of {profile} for /var/tmp/scan_input/{input}")
    utils.axiom_log(f"{command}")
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        command, shell=True, stdin=slave_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, close_fds=True
    )
    stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, process.communicate)
    if process.returncode != 0 or "exiting" in stdout:
        utils.axiom_log("Command failed with error: ")
        utils.axiom_log(stderr)
        utils.axiom_log("Command output: ")
        utils.axiom_log(stdout)
        utils.axiom_log(
            f"End of {profile} using {module}, see error at: /var/log/dnsscan/axiom.log"
        )
        return 1
    utils.axiom_log("Command output:")
    utils.axiom_log(stdout)
    utils.axiom_log(
        f"End of {profile} using {module}, succesfull result: {output}\n"
    )
    return 0