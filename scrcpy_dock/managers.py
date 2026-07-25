import threading
import subprocess
import time
from .utils import find_portable_binaries

class ScrcpySession:
    def __init__(self, serial: str, profile_name: str, proc: subprocess.Popen):
        self.serial       = serial
        self.profile_name = profile_name
        self.process      = proc
        self.pid          = proc.pid
        self.active       = True
        self.t0           = time.time()

    def uptime(self) -> str:
        s = int(time.time() - self.t0)
        return f"{s // 60:02d}:{s % 60:02d}"

    def terminate(self):
        try:
            self.process.terminate()
            for _ in range(30):
                if self.process.poll() is not None:
                    break
                time.sleep(0.1)
            if self.process.poll() is None:
                self.process.kill()
        except Exception:
            pass
        self.active = False


class ProfileManager:
    def __init__(self, cfg: dict):
        self.cfg = cfg
    
    def get_profiles(self) -> dict:
        return self.cfg.get("profiles", {})
    
    def save_profile(self, name: str, data: dict, save_cb):
        self.cfg["profiles"][name] = data
        save_cb(self.cfg)
        
    def delete_profile(self, name: str, save_cb):
        if name in self.cfg["profiles"]:
            del self.cfg["profiles"][name]
            save_cb(self.cfg)


class DeviceManager:
    def __init__(self):
        self.devices = []
        self.adb, _ = find_portable_binaries()
        self.refreshing = False

    def scan_devices(self, callback_update_ui, log_cb=None):
        if self.refreshing or not self.adb:
            return
        self.refreshing = True
        
        def task():
            try:
                r = subprocess.run([self.adb, "devices"], capture_output=True, text=True, timeout=6)
                lines = r.stdout.strip().split("\n")[1:]
                found = []
                for ln in lines:
                    if not ln.strip():
                        continue
                    parts  = ln.split()
                    serial, state = parts[0], parts[1]
                    if state == "device":
                        m = subprocess.run(
                            [self.adb, "-s", serial, "shell", "getprop", "ro.product.model"],
                            capture_output=True, text=True, timeout=4)
                        model = m.stdout.strip() or "Android"
                        found.append((serial, model, "ok"))
                    elif state == "unauthorized":
                        found.append((serial, "⚠  Acepta el permiso en el teléfono", "unauth"))
                    else:
                        found.append((serial, f"[{state}]", "other"))
                self.devices = found
                if callback_update_ui:
                    callback_update_ui(found)
            except Exception as e:
                if log_cb:
                    log_cb("ERROR", f"Escaneo ADB: {e}")
                if callback_update_ui:
                    callback_update_ui([])
            finally:
                self.refreshing = False
                
        threading.Thread(target=task, daemon=True).start()


class SessionManager:
    def __init__(self, log_q):
        self.sessions = {}
        self.adb, self.scrcpy = find_portable_binaries()
        self.log_q = log_q

    def start_scene(self, serial: str, profile_name: str, profile_data: dict, success_cb=None):
        if not self.scrcpy:
            self.log_q.put(("ERROR", "No se encontró el binario scrcpy"))
            return

        cmd = [self.scrcpy, "-s", serial, "--window-title", f"Dock: {profile_name}"]
        if profile_data.get("bitrate"):
            cmd.extend(["--video-bit-rate", profile_data["bitrate"]])
        if profile_data.get("max_size"):
            cmd.extend(["--max-size", profile_data["max_size"]])
        if profile_data.get("max_fps"):
            cmd.extend(["--max-fps", profile_data["max_fps"]])
        
        a_src = profile_data.get("audio_source", "playback")
        if a_src != "none":
            cmd.extend(["--audio-source", a_src])
        else:
            cmd.append("--no-audio")
            
        if profile_data.get("camera_id") and a_src == "mic":
            pass 
            
        if profile_data.get("turn_screen_off"):
            cmd.append("--turn-screen-off")
        if profile_data.get("stay_awake"):
            cmd.append("--stay-awake")
        if profile_data.get("extra_args"):
            cmd.extend(profile_data["extra_args"].split())

        def task():
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace"
                )
                sess = ScrcpySession(serial, profile_name, proc)
                self.sessions[serial] = sess
                self.log_q.put(("INFO", f"[{serial}] Lanzado PID {proc.pid} con perfil '{profile_name}'"))
                
                if success_cb:
                    success_cb()

                for line in proc.stdout:
                    if line.strip():
                        self.log_q.put(("INFO", f"[{serial}] {line.strip()}"))
                        
                proc.wait()
                self.log_q.put(("INFO", f"[{serial}] Finalizó con código {proc.returncode}"))
                if serial in self.sessions:
                    del self.sessions[serial]
            except Exception as e:
                self.log_q.put(("ERROR", f"[{serial}] {e}"))
                
        threading.Thread(target=task, daemon=True).start()

    def stop_session(self, serial: str):
        if serial in self.sessions:
            self.sessions[serial].terminate()
            del self.sessions[serial]

    def stop_all(self):
        for serial in list(self.sessions.keys()):
            self.stop_session(serial)
