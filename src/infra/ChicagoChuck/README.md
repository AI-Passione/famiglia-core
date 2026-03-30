# Chicago Chuck

Native Ollama server configuration for **[La Passione](https://github.com/davnnis2003/la-passione-inc)**. Runs directly on the host (no Docker) to maximize hardware and GPU utilization.

## Prerequisites

Install Ollama natively for your OS:
- **Linux Fedora (16GB RAM Primary)**: `curl -fsSL https://ollama.com/install.sh | sh`
- **macOS Air (8GB RAM Secondary)**: Download from `ollama.com/download/mac`

## Setup

Run the unified setup script. It auto-detects your OS (configuring `systemd` or `launchd` to map API to `0.0.0.0`) and RAM (automatically pulling the correct models):
```bash
./setup.sh
```

## Usage

During setup, the script will automatically detect and print your machine's local IP address. 

Confirm if it is worksing:

```bash
curl http://<SERVER_IP>:11434
```

*Replace `<SERVER_IP>` with the address printed at the end of the setup script (i.e. the CI job).*
