# 📱 MASV — Memexicanisimos Android Screen Viewer (v1.4)

![Open Source · Python · scrcpy](https://img.shields.io/badge/Open%20Source-Python%20%7C%20scrcpy-F59E0B?style=for-the-badge&logo=python&logoColor=white)
![Version v1.4](https://img.shields.io/badge/Version-v1.4-EA580C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows%20%7C%20macOS-D97706?style=for-the-badge)

[Versión en Español 🇲🇽](README.md) | [Official Website 🌐](https://memexicanisimos.com)

---

**MASV** (Memexicanisimos Android Screen Viewer) is an advanced, modern, lightweight, and high-performance graphical user interface (GUI) designed to control, mirror, and stream Android devices on PC using [`scrcpy`](https://github.com/Genymobile/scrcpy) and `ADB`.

Tailored for **content creators, streamers, photographers, gamers, and developers** who need a comprehensive workstation: native OTG/UHID physical control, clean camera feed for OBS Studio via `v4l2loopback`, network hardening, and multi-device management without bloated Electron or embedded browser dependencies (< 40 MB RAM, < 1% CPU).

---

### 🚀 What's New in Version 1.4

- 🛡️ **Frictionless Trusted Devices Vault:**
  - Interactive "Trust and Remember" prompt that registers devices in the Vault with one click, eliminating repetitive Safe Mode warnings.
- ⌨️ **Integrated OTG Mode (USB Hardware Control without Video):**
  - Control your phone using your PC's keyboard and mouse via USB HID emulation (`--otg`).
  - Does not open a video window, reducing host CPU usage to practically 0% while typing or navigating on your phone. Accessible directly from the main Quick-Cast Dashboard and `Device` menu.
- 🌐 **USB Internet Sharing (Reverse Tethering via `gnirehtet`):**
  - Share your PC's high-speed internet connection with your Android phone over USB when Wi-Fi or cellular data are unavailable. Integrated button in the Device tab.
- 📱 **Robust Multi-Device Support (Up to 16 Phones):**
  - Dynamic `PortPoolAllocator` (ports 27183 to 27199) supporting multiple concurrent Android devices in independent, labeled windows.
- 🌐 **Full Internationalization (Español 🇲🇽 / English 🇺🇸):**
  - Live language switcher under `View` $\rightarrow$ `Language / Idioma` and in the footer with 1-click assisted app restart. 100% bilingual documentation and FAQ.
- ❓ **Refined Interactive FAQ & Help Center (19 Sections):**
  - Fully synchronized mousewheel smooth scrolling across all elements.
  - Fixed accordion expand/collapse toggling and complete bilingual parity.
- 🎨 **Calibrated Themes & Contrast:**
  - `Warm Stone` (Default), `Cyber Obsidian`, and `Nordic Slate` with dynamic redraws ensuring perfect contrast and readability.
- 📷 **Smart Camera Mode & Modern Sensor Protection (48MP / 12MP):**
  - Guaranteed compatibility for Android 12+ (SDK 31+) phones with high-resolution physical camera sensors (vivo, Samsung, Motorola, Xiaomi).
  - Automatic preventive max-size clamping to 1920 px and omission of `--no-downsize-on-error`, preventing hardware MediaCodec crashes on ultra-high resolutions (e.g. 4608x3456 on 48MP sensors).
  - Assisted `v4l2loopback` detection: if `/dev/video9` is not loaded in Linux, seamlessly offers a 1-click on-screen desktop preview window or guidance for OBS Studio setup.
  - Transparent profile normalization: extracts camera and OTG flags from `extra_args` without triggering security whitelist errors.
- 🧪 **Exhaustive Connection Test Suite (269 Tests):**
  - Automated test coverage for USB screen mirroring, camera mode, OTG mode, TCP/IP wireless networking, and chipset governance (Kirin vs Qualcomm).
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
