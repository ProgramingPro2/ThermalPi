# Systemd Service Setup

The Thermal Fusion HUD can run as a systemd service, allowing it to start automatically on boot and be managed with standard systemctl commands.

## Service File

The service file `thermalpi-hud.service` is located in the project root. It:
- Runs as the `jpearce` user
- Sets up the required environment variables (LD_LIBRARY_PATH)
- Activates the Python virtual environment
- Starts the HUD application
- Restarts automatically on failure (with a 5-second delay)

## Installation

The service file has already been installed on the Pi. To reinstall or update:

```bash
# Copy service file to systemd directory
sudo cp thermalpi-hud.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable thermalpi-hud.service
```

## Service Management

### Start the service
```bash
sudo systemctl start thermalpi-hud.service
```

### Stop the service
```bash
sudo systemctl stop thermalpi-hud.service
```

### Restart the service
```bash
sudo systemctl restart thermalpi-hud.service
```

### Check service status
```bash
sudo systemctl status thermalpi-hud.service
```

### View service logs
```bash
# View recent logs
sudo journalctl -u thermalpi-hud.service -n 50

# Follow logs in real-time
sudo journalctl -u thermalpi-hud.service -f

# View logs since boot
sudo journalctl -u thermalpi-hud.service -b
```

### Enable/Disable auto-start on boot
```bash
# Enable auto-start
sudo systemctl enable thermalpi-hud.service

# Disable auto-start
sudo systemctl disable thermalpi-hud.service
```

## Service Configuration

The service is configured to:
- **Type**: `simple` - systemd considers the service started once the main process starts
- **Restart**: `always` - automatically restart if the service stops
- **RestartSec**: `5` - wait 5 seconds before restarting
- **After**: `network.target` - start after network is available (though not required)

## Troubleshooting

If the service fails to start:

1. Check the service status:
   ```bash
   sudo systemctl status thermalpi-hud.service
   ```

2. Check the logs for errors:
   ```bash
   sudo journalctl -u thermalpi-hud.service -n 100
   ```

3. Verify the service file syntax:
   ```bash
   sudo systemd-analyze verify thermalpi-hud.service
   ```

4. Test running the script manually:
   ```bash
   cd ~/ThermalPi
   export LD_LIBRARY_PATH=~/ThermalPi/libraries:/usr/local/lib:$LD_LIBRARY_PATH
   source .venv/bin/activate
   python3 thermal_fusion_hud.py
   ```

5. Ensure all hardware is connected and permissions are correct:
   - SPI is enabled
   - USB cameras are accessible
   - Display hardware is connected

