import os
import sys
import time
from datetime import datetime, timedelta

from tenda_config import ROUTER_IP, get_tenda_session, get_tenda_status_data, set_network_mode

# Configuration from .env and defaults
SPEED_TEST_URL = os.getenv("SPEED_TEST_URL", "https://nbg1-speed.hetzner.com/100MB.bin")
SPEED_THRESHOLD_MBPS = 2.0
CHECK_INTERVAL_SECONDS = 3600  # 1 hour
INITIAL_4G_DURATION_MINUTES = 20

# ANSI Colors for logging
CLR = {
    "BLUE": "\033[1;34m",
    "GREEN": "\033[1;32m",
    "YELLOW": "\033[1;33m",
    "RED": "\033[1;31m",
    "CYAN": "\033[1;36m",
    "RESET": "\033[0m",
    "GRAY": "\033[1;90m",
}


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = CLR.get(level, CLR["RESET"])
    print(f"{CLR['GRAY']}[{timestamp}]{CLR['RESET']} {color}{msg}{CLR['RESET']}")


def measure_speed(url, duration=5):
    """
    Measures download speed in Mbps using native Python requests.
    Streams the content for 'duration' seconds to estimate speed without downloading large files.
    """
    import requests

    try:
        log(f"Starting speed test against {url}...", "BLUE")
        start_time = time.time()
        with requests.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()
            total_bytes = 0

            # Stream chunks for the specified duration
            for chunk in response.iter_content(chunk_size=16384):
                if chunk:
                    total_bytes += len(chunk)
                if time.time() - start_time > duration:
                    break

        end_time = time.time()
        elapsed = end_time - start_time

        # Calculate Mbps
        mbps = (total_bytes * 8) / (elapsed * 1024 * 1024)
        log(f"Measured speed: {mbps:.2f} Mbps", "GREEN")
        return mbps
    except Exception as e:
        log(f"Speed test failed: {e}", "RED")
        return None


def stay_on_5g_loop():
    """
    Main control loop for network management.
    """
    retry_count = 0
    next_check_time = datetime.now()

    # State tracking
    current_forced_mode = None  # "4g" or None (running normally on 5G)
    mode_expiry = None

    log(f"Stay on 5G script started. Router: {ROUTER_IP}", "CYAN")
    log(
        f"Threshold: {SPEED_THRESHOLD_MBPS} Mbps | Interval: {CHECK_INTERVAL_SECONDS / 60} mins",
        "CYAN",
    )

    while True:
        now = datetime.now()

        # 1. Handle Recovery from 4G
        if current_forced_mode == "4g" and now >= mode_expiry:
            log("4G fallback period expired. Attempting to switch back to 5G...", "YELLOW")
            session, stok = get_tenda_session()
            if session and stok:
                try:
                    if set_network_mode(session, stok, "5g"):
                        log("Switching to 5G mode. Waiting 30s for sync...", "BLUE")
                        time.sleep(30)

                        # Check if it's actually working
                        speed = measure_speed(SPEED_TEST_URL)
                        if speed is None:
                            log("Speed measurement unavailable. Resuming monitoring.", "YELLOW")
                            current_forced_mode = None
                            retry_count = 0
                            mode_expiry = None
                            next_check_time = now + timedelta(seconds=CHECK_INTERVAL_SECONDS)
                        elif speed < SPEED_THRESHOLD_MBPS:
                            retry_count += 1
                            wait_mins = INITIAL_4G_DURATION_MINUTES * (2 ** (retry_count - 1))
                            log(
                                f"5G performance still poor ({speed:.2f} Mbps). "
                                f"Backing off for {wait_mins} mins.",
                                "RED",
                            )
                            if set_network_mode(session, stok, "4g"):
                                current_forced_mode = "4g"
                                mode_expiry = now + timedelta(minutes=wait_mins)
                            else:
                                log("Rollback to 4G failed. Clearing backoff state.", "RED")
                                current_forced_mode = None
                                retry_count = 0
                                mode_expiry = None
                                next_check_time = now + timedelta(seconds=CHECK_INTERVAL_SECONDS)
                        else:
                            log("5G is stable. Resetting backoff counter.", "GREEN")
                            current_forced_mode = None
                            retry_count = 0
                            next_check_time = now + timedelta(seconds=CHECK_INTERVAL_SECONDS)
                    else:
                        log("Failed to switch back to 5G. Resuming normal monitoring.", "RED")
                        current_forced_mode = None
                        retry_count = 0
                        mode_expiry = None
                        next_check_time = now + timedelta(seconds=CHECK_INTERVAL_SECONDS)
                finally:
                    session.close()
            else:
                if session:
                    session.close()
                log("Authentication failed during recovery. Retrying in 5 mins.", "RED")
                time.sleep(300)
            continue

        # 2. Main Monitoring (on 5G)
        if current_forced_mode is None and now >= next_check_time:
            session, stok = get_tenda_session()
            if not session or not stok:
                if session:
                    session.close()
                log("Authentication failed. Retrying in 1 min.", "RED")
                time.sleep(60)
                continue

            try:
                data = get_tenda_status_data(session, stok)
                if not data:
                    log("Failed to get router status.", "RED")
                    time.sleep(60)
                    continue

                sim_info = data.get("simInfo", {})
                mobile_net = str(sim_info.get("mobileNet") or "Unknown")

                log(f"Network Status: {mobile_net}", "BLUE")

                trigger_fallback = False
                reason = ""

                # Check for 3G
                if "3G" in mobile_net.upper():
                    trigger_fallback = True
                    reason = "Detected 3G mode"
                else:
                    # Check Speed
                    speed = measure_speed(SPEED_TEST_URL)
                    if speed is not None and speed < SPEED_THRESHOLD_MBPS:
                        trigger_fallback = True
                        reason = f"Speed dropped below threshold ({speed:.2f} Mbps)"

                if trigger_fallback:
                    log(
                        f"{reason}. Forcing 4G for {INITIAL_4G_DURATION_MINUTES} minutes.", "YELLOW"
                    )
                    if set_network_mode(session, stok, "4g"):
                        current_forced_mode = "4g"
                        mode_expiry = now + timedelta(minutes=INITIAL_4G_DURATION_MINUTES)
                        retry_count = 1
                elif speed is not None:
                    log(
                        f"{mobile_net} is performing well. Next check at "
                        f"{(now + timedelta(seconds=CHECK_INTERVAL_SECONDS)).strftime('%H:%M:%S')}",
                        "GREEN",
                    )
                    next_check_time = now + timedelta(seconds=CHECK_INTERVAL_SECONDS)
                else:
                    log(
                        "Speed measurement skipped or unavailable. Will retry check later.",
                        "YELLOW",
                    )
                    # We don't update next_check_time, so it will retry soon
            finally:
                session.close()

        # Sleep to avoid CPU spin
        time.sleep(10)


if __name__ == "__main__":
    try:
        stay_on_5g_loop()
    except KeyboardInterrupt:
        log("Script stopped by user.", "YELLOW")
        sys.exit(0)
    except Exception as e:
        log(f"Critical error: {e}", "RED")
        sys.exit(1)
