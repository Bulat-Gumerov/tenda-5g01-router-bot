import sys

from tenda_config import ROUTER_IP, get_tenda_session, get_tenda_status_data, set_network_mode


def ensure_4g_mode():
    """
    Check current network mode and switch to 4G if it's currently 3G.
    """
    print(f"\033[1;34m[*] Running 4G enforcement check on {ROUTER_IP}...\033[0m")

    # 1. Authenticate
    session, stok = get_tenda_session()
    if not session or not stok:
        print("\033[1;31m[!] Authentication Failed.\033[0m")
        return

    try:
        # 2. Get Current Status
        data = get_tenda_status_data(session, stok)
        if not data:
            print("\033[1;31m[!] Error: Could not check current mode.\033[0m")
            return

        sim_info = data.get("simInfo")
        if not isinstance(sim_info, dict):
            print("\033[1;31m[!] Error: Invalid or missing simInfo module.\033[0m")
            return

        # Defensive read of mobileNet
        raw_mode = sim_info.get("mobileNet")
        current_mode = raw_mode if isinstance(raw_mode, str) else "Unknown"

        print(f"[*] Current mode detected: \033[1;37m{current_mode}\033[0m")

        # 3. Decision Logic
        if current_mode == "4G":
            print("\033[1;32m[✓] Already in 4G mode.\033[0m")
        else:
            print(f"\033[1;33m[!] {current_mode} detected. Switching to 4G mode...\033[0m")
            if set_network_mode(session, stok, "4g"):
                pass  # No subsequent state updates in this script
    finally:
        # Close the session
        session.close()


if __name__ == "__main__":
    try:
        ensure_4g_mode()
    except KeyboardInterrupt:
        print("\n\033[1;33m[!] Operation cancelled.\033[0m")
        sys.exit(0)
