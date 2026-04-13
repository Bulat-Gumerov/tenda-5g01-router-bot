import hashlib
import json
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configuration Constants
ROUTER_IP = os.getenv("ROUTER_IP", "192.168.1.1")
ROUTER_PWD = os.getenv("ROUTER_PWD")
DEFAULT_TIMEOUT = 10


def parse_multi_json(text):
    """
    Parses a string that may contain multiple concatenated JSON objects.
    Returns a list of parsed dictionaries.
    """
    objs = []
    decoder = json.JSONDecoder()
    pos = 0
    text = text.strip()
    while pos < len(text):
        try:
            # Skip any whitespace or junk between objects
            while pos < len(text) and text[pos] in " \n\r\t":
                pos += 1
            if pos >= len(text):
                break

            obj, delta = decoder.raw_decode(text[pos:])
            objs.append(obj)
            pos += delta
        except json.JSONDecodeError:
            # If we hit a snag, try to find the next '{'
            next_start = text.find("{", pos + 1)
            if next_start == -1:
                break
            pos = next_start
    return objs


def get_tenda_session():
    """
    Log in to the Tenda router and retrieve the session token (stok).
    """
    if not ROUTER_PWD:
        print("\033[1;31m[!] Error: ROUTER_PWD not found in environment.\033[0m")
        return None, None
    # Session to persist cookies
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Tenda-5G01-Automation (https://github.com/Bulat-Gumerov/tenda-5g01-router-bot)",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"http://{ROUTER_IP}/index.html",
        }
    )

    # Prepare Login Credentials
    # Hashing: Uppercase MD5
    hashed_pwd = hashlib.md5(ROUTER_PWD.encode()).hexdigest().upper()

    # Time format: YYYY-M-D HH:MM:SS
    now = datetime.now()
    time_str = f"{now.year}-{now.month}-{now.day} {now.strftime('%H:%M:%S')}"

    login_payload = {"userName": "admin", "password": hashed_pwd, "time": time_str}

    # Step 1: Login
    login_url = f"http://{ROUTER_IP}/login/Auth"
    try:
        response = session.post(login_url, json=login_payload, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        login_data = response.json()

        if login_data.get("errCode") != 0:
            print(f"Login failed: {login_data}")
            session.close()
            return None, None

        # Step 2: Get stokCfg
        rand = time.time()
        stok_url = f"http://{ROUTER_IP}/goform/stokCfg?rand={rand}"

        stok_response = session.get(stok_url, timeout=DEFAULT_TIMEOUT)
        stok_response.raise_for_status()
        stok_data = stok_response.json()

        # Extract stok
        stok = stok_data.get("stokCfg", {}).get("stok")
        if not stok:
            # Fallback to login response if stokCfg didn't return it
            stok = login_data.get("stok")

        if not stok:
            session.close()
            return None, None

        return session, stok

    except Exception as e:
        print(f"Error during login: {e}")
        if "session" in locals():
            session.close()
        return None, None


def get_tenda_status_data(session, stok):
    """
    Fetch the raw status modules from the Tenda router.
    Returns a unified dictionary of modules or None if failed.
    """
    rand = time.time()
    # Requesting key modules
    url = f"http://{ROUTER_IP}/;stok={stok}/goform/getModules?rand={rand}&modules=simStatus,simInfo,meshTopo,systemCfg"

    try:
        response = session.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        json_objs = parse_multi_json(response.text)
        if not json_objs:
            return None

        # Merge all objects into one result (later objects overwrite earlier ones)
        result = {}
        for obj in json_objs:
            result.update(obj)
        return result
    except Exception as e:
        print(f"Error fetching status data: {e}")
        return None


def set_network_mode(session, stok, mode):
    """
    Switch the network mode between 4G and 5G NSA.
    """
    # Profile list provided by the user
    profiles = [
        {
            "profileName": "INTERNET",
            "apn": "internet",
            "simUser": "true",
            "simPwd": "true",
            "pdpType": "IPv4v6",
            "authType": "PAP",
            "isSys": "true",
            "isDefault": "true",
        },
        {
            "profileName": "TRUE-H INTERNET",
            "apn": "internet",
            "simUser": "true",
            "simPwd": "true",
            "pdpType": "IPv4",
            "authType": "NONE",
            "isSys": "false",
            "isDefault": "true",
        },
        {
            "profileName": "TRUE-H INTERNET 2",
            "apn": "internet",
            "simUser": "",
            "simPwd": "",
            "pdpType": "IPv4v6",
            "authType": "NONE",
            "isSys": "false",
            "isDefault": "true",
        },
        {
            "profileName": "TRUE",
            "apn": "internet",
            "simUser": "True",
            "simPwd": "True",
            "pdpType": "IPv4v6",
            "authType": "CHAP",
            "isSys": "false",
            "isDefault": "true",
        },
    ]

    # dataOptions: 4g = 2, 5g NSA = 1
    data_options = 2 if mode == "4g" else 1

    payload = {
        "simWan": {
            "mobileData": True,
            "dataRoaming": False,
            "dataOptions": data_options,
            "profileIndex": "0",
            "action": 1,
            "list": profiles,
            "mtu": 1500,
        }
    }

    # Endpoint URL with stok
    url = f"http://{ROUTER_IP}/;stok={stok}/goform/setModules?modules=simWan"

    print(f"Applying settings for {mode.upper()} mode...")
    try:
        response = session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        result = response.json()

        if result.get("errCode") == 0:
            print(f"Successfully applied {mode.upper()} settings.")
        else:
            print(f"Router returned error: {result}")

    except Exception as e:
        print(f"Error sending request: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tenda_config.py [4g|5g]")
        sys.exit(1)

    target_mode = sys.argv[1].lower()
    if target_mode not in ["4g", "5g"]:
        print("Invalid mode. Please specify '4g' or '5g'.")
        sys.exit(1)

    # Get session and token
    sess, token = get_tenda_session()
    if sess and token:
        set_network_mode(sess, token, target_mode)
    else:
        print("Failed to authenticate with the router.")
