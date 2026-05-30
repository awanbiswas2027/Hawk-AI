# Document 17: User & Administrator Manual

---

## 1. Physical Hardware Assembly Guide

This section guides you through assembling the physical Hawk-AI Edge device.

```text
[Neo-6M GPS Module]
   TXD Pin  ──────► RPi GPIO Pin 15 (RXD)
   RXD Pin  ──────► RPi GPIO Pin 14 (TXD)
   VCC Pin  ──────► RPi GPIO Pin 1 (3.3V)
   GND Pin  ──────► RPi GPIO Pin 6 (Ground)

[USB Camera]  ──► RPi USB 2.0 Port
[Power Bank]  ──► RPi USB-C Power Input
```

### 1.1 Bill of Materials (BOM)
* Raspberry Pi 4 Model B (4GB RAM recommended)
* U-Blox Neo-6M GPS Module (with ceramic antenna)
* Wide-Angle 1080p USB Webcam (UVC compliant)
* 3.3V/5V compatible jumper wires
* 64GB SanDisk Extreme MicroSD card
* Outdoor portable Power Bank (10,000mAh, minimum 5V/3A output)
* Custom 3D-printed PETG protective enclosure
* Helmet mount bracket (standard action camera adhesive mounts)

### 1.2 Step-by-Step Wiring Instructions
1. **Unpower the Raspberry Pi**: Ensure the Pi is fully disconnected from power before wiring.
2. **Wire the GPS Module**: Connect jumper wires from the Neo-6M module to the Pi's GPIO header pin row:
   * Connect Neo-6M **VCC** to Raspberry Pi **Pin 1 (3.3V)**.
   * Connect Neo-6M **GND** to Raspberry Pi **Pin 6 (GND)**.
   * Connect Neo-6M **TXD** (Transmit) to Raspberry Pi **Pin 15 (GPIO 15 / RXD)**.
   * Connect Neo-6M **RXD** (Receive) to Raspberry Pi **Pin 14 (GPIO 14 / TXD)**.
3. **Connect Camera**: Plug the wide-angle camera USB lead into one of the blue USB 3.0 ports on the RPi.

### 1.3 Flashing the Software Image
1. Download the pre-built Hawk-AI Edge Image (`hawk-ai-edge-v1.0.img`).
2. Insert your MicroSD card into your computer.
3. Open **Raspberry Pi Imager**:
   * Under *Operating System*, select "Use Custom" and navigate to your downloaded `.img` file.
   * Under *Storage*, select your MicroSD card.
   * Click **Write**.
4. Once completed, insert the card into the Raspberry Pi card slot.

### 1.4 Helmet Mounting Guide
1. Wipe the front/side surface of the motorcycle helmet clean using isopropyl alcohol.
2. Affix the high-adhesion curved action camera mount to the helmet surface. Allow 24 hours to cure.
3. Place the Raspberry Pi in the 3D-printed enclosure. Mount the enclosure to the helmet bracket.
4. Mount the camera to the helmet mount. Adjust the angle so the camera points directly forward when the rider is looking straight ahead.

---

## 2. Initial Setup & Configuration

1. **Power On**: Connect the power bank USB-C cable to the RPi. The system will boot up, showing a solid green status LED.
2. **Access Local Dashboard**:
   * The RPi will broadcast a temporary setup Wi-Fi hotspot named `Hawk-AI-Setup-XXXX`.
   * Connect to this hotspot using a smartphone.
   * Navigate to `http://192.168.4.1` on your phone browser.
3. **Configure Wi-Fi**: Enter your home Wi-Fi credentials. The device will connect to this network post-ride to sync any offline event buffers.
4. **Acquire GPS Lock**: Step outdoors. The GPS module light will begin flashing green, confirming it has established connection with GPS satellites. The system status LED on the Pi case will turn solid green, indicating the system is ready.

---

## 3. Administrator Guide

### 3.1 Portal Deployment
The Cloud Portal is deployed as part of the Docker container stack. Access the management dashboard by visiting `https://portal.hawk-ai.ai` and signing in using your administrative credentials.

### 3.2 System Monitoring & Logs
* **System Health Page**: Displays container CPU usage, DB space remaining, and queue depth indicators.
* **Troubleshooting Logs**: To pull real-time API traffic logs on the AWS host machine, run:
  ```bash
  docker logs --tail 100 -f hawk_ai_api
  ```

---

## 4. Troubleshooting Manual

| Symptom | Probable Cause | Action |
| :--- | :--- | :--- |
| **System status LED remains flashing Orange.** | GPS Module cannot establish satellite lock. | Move the device outdoors away from concrete walls. Check the antenna connection on the GPS board. |
| **LED turns Magenta (Camera Error).** | RPi cannot access the UVC camera interface. | Unplug and re-plug the USB camera. Run `ls /dev/video*` to verify the system lists the camera device node. |
| **Edge events are not syncing to the cloud.** | RPi cannot establish internet connection. | Verify the local dashboard Wi-Fi configurations. Make sure the API Gateway endpoint matches your configuration. |
