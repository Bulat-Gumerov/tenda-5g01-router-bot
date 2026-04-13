# Tenda 5G01 Automation Tools

A collection of Python scripts to monitor and manage **Tenda 5G01** 5G routers via their web API. These tools are designed to automate network mode switching and ensure stable connectivity.

## 📋 Features

- **Automated Login**: Securely authenticates with the router using MD5-hashed passwords.
- **Status Monitoring**: Detailed reporting of network type (3G/4G/5G), access band, and connection status.
- **Network Mode Management**: Programmatically switch between 4G and 5G NSA modes.
- **Auto-Recovery**:
  - `tenda_ensure_4g.py`: Prevents the router from falling back to slow 3G connections.
  - `tenda_stay_on_5g.py`: Monitors 5G performance and automatically fails back to 4G if speeds drop, with intelligent exponential backoff for 5G recovery.

## 🛠 Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed.

### Installation

1. Clone this repository.
2. Initialize the environment:
   ```bash
   uv sync
   ```
3. Create a `.env` file in the project root:
   ```env
   ROUTER_IP=192.168.1.1
   ROUTER_PWD=your_router_password
   SPEED_TEST_URL=http://speedtest.sin1.sg.leaseweb.net/10mb.bin
   ```

## 🚀 Usage

### 1. View Status
Get a quick report of your current network status:
```bash
uv run tenda_status.py
```

### 2. Manual Mode Switching
Switch the router's network mode manually:
```bash
uv run tenda_config.py 4g
# OR
uv run tenda_config.py 5g
```

### 3. Ensure 4G (Anti-3G)
Check if the router is on 3G and force it to 4G if necessary:
```bash
uv run tenda_ensure_4g.py
```

### 4. Smart 5G Monitoring
Run a background loop that monitors 5G speed and stability:
```bash
uv run tenda_stay_on_5g.py
```
*Note: You can configure thresholds like `SPEED_THRESHOLD_MBPS` directly in the script or via environment variables.*

## 🛠 Development

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

To check for issues:
```bash
uv run ruff check .
```

To automatically fix issues and format code:
```bash
uv run ruff check --fix .
uv run ruff format .
```

## 📁 File Structure

- `tenda_config.py`: Core logic for API interaction and authentication.
- `tenda_status.py`: User-friendly status CLI.
- `tenda_ensure_4g.py`: One-off check to prevent 3G usage.
- `tenda_stay_on_5g.py`: Advanced monitoring and auto-switching daemon.
- `.env`: Configuration file for IP and Credentials.

## ⚠️ Disclaimer
These scripts interact with the router's internal API. Specifically tested on the **Tenda 5G01** AX1800 5G NR Router. Use at your own risk.
