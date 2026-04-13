import sys

from tenda_config import ROUTER_IP, get_tenda_session, get_tenda_status_data


def get_tenda_status():
    """
    Fetch the status of the Tenda router and print mobile network details.
    """
    print(f"\033[1;34m[*] Connecting to Tenda Router at {ROUTER_IP}...\033[0m")

    # Authenticate and get session
    session, stok = get_tenda_session()

    if not session or not stok:
        print("\033[1;31m[!] Authentication Failed.\033[0m")
        return

    try:
        data = get_tenda_status_data(session, stok)
        if not data:
            print("\033[1;31m[!] Error: Could not retrieve or parse status data.\033[0m")
            return

        sim_info = data.get("simInfo")
        if not sim_info:
            print("\033[1;33m[!] Warning: 'simInfo' section not found.\033[0m")
            found_keys = sorted(data.keys())
            print(f"\033[1;90m[*] Modules found: {', '.join(found_keys)}\033[0m")
            return

        # Extract fields
        mobile_net = sim_info.get("mobileNet", "Unknown")
        access_band = sim_info.get("accessBand", "Unknown")
        internet_status = sim_info.get("internetStatus", "Unknown")

        # Visual status indicator
        status_color = "\033[1;32m" if internet_status.lower() == "connected" else "\033[1;31m"

        print("\n" + "─" * 40)
        print("\033[1;36mTENDA ROUTER STATUS REPORT\033[0m")
        print("─" * 40)
        print(f" \033[1;37mNetwork Type:\033[0m     {mobile_net}")
        print(f" \033[1;37mAccess Band:\033[0m      {access_band}")
        print(f" \033[1;37mInternet Status:\033[0m  {status_color}{internet_status.upper()}\033[0m")
        print("─" * 40 + "\n")
    finally:
        # Close the session
        session.close()


if __name__ == "__main__":
    try:
        get_tenda_status()
    except KeyboardInterrupt:
        print("\n\033[1;33m[!] Operation cancelled by user.\033[0m")
        sys.exit(0)
