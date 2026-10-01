# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.4.1)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-F59E0B?style=for-the-badge&logo=python&logoColor=white)
![Version v1.4.1](https://img.shields.io/badge/Version-v1.4.1-EA580C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Tests 668 Passed](https://img.shields.io/badge/Tests-668%20Passed-10B981?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-D97706?style=for-the-badge)

[Versión en Español 🇲🇽](README.md) | [Official Website 🌐](https://memexicanisimos.com)

---

**MASV** (Memexicanisimos Android Screen Viewer) is a native, ultra-lightweight, high-performance graphical workstation (GUI) to control, mirror, and stream Android devices on PC using [`scrcpy`](https://github.com/Genymobile/scrcpy) and `ADB`.

Tailored for **content creators, streamers, photographers, gamers, and developers** who need a comprehensive workstation: native OTG/UHID physical control, clean camera feed for OBS Studio via `v4l2loopback`, network hardening, and multi-device management without bloated Electron or embedded browser dependencies (< 40 MB RAM, < 1% CPU).

---

### 🚀 What's New in Version 1.4.1

- ⚡ **Asynchronous Non-Blocking Session Lifecycle:**
  - Session termination now runs in a detached daemon background thread; eliminates 3-second UI hangs when stopping streams or exiting the application.
- 🩺 **Full Assisted Remediation Catalog (31/31 Bilingual Codes):**
  - Step-by-step diagnostic guidance, detailed technical causes, and resolution steps in English and Spanish for every `ErrorCode`.
- 🎨 **WCAG 2.1 AA Visual Accessibility:**
  - Calibrated luminance contrast ratios for active status pills and buttons across all themes (`Warm Stone`, `Cyber Obsidian`, and `Nordic Slate`), ensuring readability above 4.5:1.
- 📱 **Dynamic Hardware Governance (Android 10 / EMUI 10 / Kirin 710):**
  - Automatic detection of `android_sdk <= 29` devices (e.g. Huawei Y9), auto-injecting `--no-audio` and forcing H.264 video codec to prevent crashes due to lack of OS-level audio playback capture.
- 📷 **Built-in Front and Rear Clean Camera Profiles:**
  - Factory-calibrated profiles for `"📷 Cámara HD"` (rear) and `"📷 Cámara Frontal"` (front) for clean studio feeds into OBS Studio.
- 🛡️ **Encrypted PBKDF2/Fernet Vault with Safe Fallback:**
  - Local host-derived encryption for trusted device records (`vault.enc`) with transparent non-destructive fallback to legacy paths.
- 🧪 **Automated Test Suite of 668 Tests (100% Passing):**
  - Armored hexagonal architecture with > 85% global coverage (100% on network adapters and business logic), zero cyclomatic complexity hotspots (CC <= 10), and strict user data isolation guards.
- 🔀 **Productivity Shortcuts:**
  - `Ctrl + M`: Toggle Compact Mode (500x620) and Advanced Dashboard.
  - `Ctrl + B`: Collapse / Expand sidebar (Dashboard).
  - `Ctrl + I`: Start / Toggle streaming.
  - `Ctrl + R`: Refresh devices.
  - `Ctrl + H`: Open Help Center.
  - `Ctrl + Q`: Exit with automatic lockdown (`adb usb`).

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
