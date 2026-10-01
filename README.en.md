# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.3)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-F59E0B?style=for-the-badge&logo=python&logoColor=white)
![Version v1.3](https://img.shields.io/badge/Version-v1.3-EA580C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-D97706?style=for-the-badge)

[Versión en Español 🇲🇽](README.md) | [Official Website 🌐](https://memexicanisimos.com)

---

**MASV** (Memexicanisimos Android Screen Viewer) is an advanced, modern, lightweight, and high-performance graphical user interface (GUI) designed to control, mirror, and stream Android devices on PC using [`scrcpy`](https://github.com/Genymobile/scrcpy) and `ADB`.

Tailored for **content creators, streamers, photographers, gamers, and developers** who need a comprehensive workstation: native OTG/UHID physical control, clean camera feed for OBS Studio via `v4l2loopback`, network hardening, and multi-device management without bloated Electron or embedded browser dependencies (< 40 MB RAM, < 1% CPU).

---

### 🚀 What's New in Version 1.3

- 🎨 **Dynamic Color Theme Switcher:**
  - `Warm Stone` (Default): Warm, comfortable dark tones engineered for long streaming and editing sessions.
  - `Cyber Obsidian`: Gamer/OBS dark aesthetic with Neon Cyan accents (`#00F0FF`) and high contrast.
  - `Nordic Slate`: Clean technical minimalism in Ice Blue and graphite.
  - Hot-swappable live from the menu bar: `View` $\rightarrow$ `Color Theme`.
- ⌨️ **Physical OTG Mode & UHID Emulation:**
  - Native keyboard and mouse input forwarding using USB HID emulation (`--keyboard=uhid`, `--mouse=uhid`, `--otg`).
  - Allows full physical keyboard/mouse control on the device even without video mirroring or with the display turned off.
- 🌐 **Autonomous Reverse Tethering (`gnirehtet`):**
  - Share your PC's internet connection with your Android phone over USB cable cleanly and stably.
- 📦 **Universal 1-Click Installer & Uninstaller:**
  - Fast 1-liner install command using `curl` with zero manual compilation.
  - Persistent deployment to `~/.MASV/bin/` (you can delete the downloaded folder without breaking anything).
  - GUI options under `File` $\rightarrow$ `📥 Install to System` and `🗑️ Uninstall`.
- ❓ **Interactive Help Center & FAQ:**
  - Built-in collapsible accordion guides in the Help tab (`Ctrl + H`).
  - Documented troubleshooting for Offline devices, Android 10/EMUI restrictions, Trust Vault, and OBS Studio camera mode.
- 🛡️ **Trusted Devices Vault & TCP/IP Lockdown:**
  - Network whitelist to prevent unauthorized connections on public Wi-Fi networks and auto-shield with `adb usb` upon exit (`Ctrl + Q`).

---

### 📥 Direct Downloads (Ready to Use)

| Operating System | File / Format | Installation Type |
| :--- | :--- | :--- |
| **🐧 Linux** (Debian, Ubuntu, Arch, Fedora, Mint) | [`MASV-Linux.tar.gz`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz) | **100% Portable** or via `./install.sh` |
| **🪟 Windows** (Windows 10 & 11) | [`MASV-Windows.exe`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe) | **Standalone Portable** (Bundled scrcpy/adb core) |
| **🍎 macOS** (Intel & Apple Silicon) | [`MASV-macOS`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-macOS) | Binary for macOS Monterey or higher |

---

### 📋 Linux Installation Guide

Choose the method that best matches your workflow:

#### Option A: Automatic 1-Command Installation (Recommended)
Open your terminal and run:
```bash
curl -sSL https://raw.githubusercontent.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/main/install.sh | bash
```
*This fetches the latest release, installs the binary to `~/.MASV/bin/`, sets up the desktop application shortcut with high-res icon, and adds the `MASV` command to your terminal.*

---

#### Option B: 100% Portable Mode (No System Changes)
1. Download [`MASV-Linux.tar.gz`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Linux.tar.gz).
2. Extract it anywhere (e.g. `~/Downloads` or a USB drive):
   ```bash
   tar -xzf MASV-Linux.tar.gz
   ```
3. Double-click the `MASV` binary (or run `./MASV`). It opens immediately with all dependencies bundled!
*(If you later want to install it system-wide, simply go to `File` $\rightarrow$ `📥 Install to System`).*

---

#### Option C: From Source Repository (`git clone`)
```bash
git clone https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer.git MASV
cd MASV
./install.sh
```

---

### 🗑️ Clean Uninstallation

You can cleanly uninstall MASV anytime without leftover files:
* **From Terminal:**
  ```bash
  MASV --uninstall
  ```
  *(or `MASV --uninstall --purge` to also delete user configs and saved profiles)*.
* **From Graphical Interface:**
  Go to `File` $\rightarrow$ `🗑️ Uninstall from System`.

---

### 🪟 Windows Instructions

1. Download [`MASV-Windows.exe`](https://github.com/myinnervoid/Memexicanisimos-Android-Screen-Viewer/releases/latest/download/MASV-Windows.exe).
2. Double-click the downloaded file.
3. The executable comes with `scrcpy` and `adb` pre-bundled; it starts immediately without installing external drivers.

---

### ❓ Frequently Asked Questions (FAQ)

#### 🔴 What should I do if the device shows "Offline"?
Indicates that the phone lost communication with the ADB socket (often caused by USB cable disconnects or USB port power suspend).
* **Fix:** Reconnect the USB cable, verify USB power suspension is off, and click **"⚡ Restart ADB"** in MASV (or in the Device menu).

#### 📱 Huawei Y9 & Android 10 (EMUI 10) Restrictions & Optimization
* **Audio:** Android 10 does not support native internal scrcpy audio capture (requires Android 11+). MASV automatically enables `--no-audio`.
* **Performance:** For Kirin 710 chipsets, we recommend the **H.264** codec capped at **8 Mbps** bitrate and **1080p or 720p** resolution.

#### 🛡️ Trusted Devices Vault & Safe Mode
Registering devices in the vault prevents accidental or unauthorized connections on shared Wi-Fi networks. **Safe Mode** revokes port 5555 (`adb usb`) to close remote access upon exiting with `Ctrl + Q`.

#### 📷 Photo Studio Mode & Clean Camera Feed
Stream a clean rear-camera feed from your phone directly into **OBS Studio** without UI overlays. On Linux, MASV mounts the camera natively as a zero-latency virtual webcam using `v4l2loopback`.

#### 🚪 Clean Exit vs. Minimize to Tray
The Exit button (or `Ctrl + Q`) deterministically terminates the application, halts active scrcpy subprocesses, and stops the device tracker, cleanly freeing up network ports and file locks.

---

## 📜 License

Developed by **Memexicanisimos Studio** under the **MIT License**. Built on the open-source engine of Genymobile/scrcpy.
