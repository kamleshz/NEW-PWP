import datetime
from datetime import date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import webdriver_manager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import tkinter as tk
import tkinter.filedialog as fd
import getpass
import time
import pandas as pd
import tkinter as tk
import easygui
from pathlib import Path
import datetime
import requests
import json
import os
import math
import difflib
import hashlib
import platform
import re
import subprocess
import sys
import threading
import tempfile
import webbrowser
import zipfile
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from PyPDF2 import PdfMerger,PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from selenium.webdriver.common.action_chains import ActionChains
from requests.exceptions import ConnectTimeout

APP_VERSION = "1.0.1"
UPDATE_METADATA_URL = "https://raw.githubusercontent.com/kamleshz/NEW-PWP/main/desktop_release.json"
DEFAULT_RELEASE_PAGE_URL = "https://github.com/kamleshz/NEW-PWP/releases/latest"
DEFAULT_RELEASE_DOWNLOAD_URL = "https://github.com/kamleshz/NEW-PWP/releases/latest/download/PWPDesktopApp.zip"
APP_EXECUTABLE_NAME = "PWPDesktopApp.exe"
LICENSE_VALIDATE_URL = "https://api.recirculytics.in/v1/validate"
SW_VERSION = APP_VERSION
PRIMARY_CACHE_ROOT = Path(os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home()))
FALLBACK_CACHE_ROOT = Path.home() / ".recirculytics"
LICENSE_GRACE_SECS = 86400
GST_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b")

_license_info = {
    "key": "",
    "customer_name": "",
    "tier": "",
    "expires_on": "",
    "allowed_gsts": [],
    "fy_start": "",
    "fy_end": "",
    "portal_gst": "",
    "offline": False,
    "license_verified": False,
    "gst_verified": False,
}

def parse_version_parts(version_value):
    version_text = str(version_value or "").strip().lstrip("vV")
    parts = []
    for piece in version_text.split("."):
        digits = "".join(char for char in piece if char.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def is_newer_version(latest_version, current_version):
    return parse_version_parts(latest_version) > parse_version_parts(current_version)

def fetch_release_metadata():
    response = requests.get(UPDATE_METADATA_URL, timeout=10)
    response.raise_for_status()
    metadata = response.json()
    if not isinstance(metadata, dict):
        raise ValueError("Invalid update metadata format.")
    return metadata

def build_release_notes_text(metadata):
    notes = metadata.get("release_notes", [])
    if isinstance(notes, list):
        notes = [str(item).strip() for item in notes if str(item).strip()]
        return "\n".join(f"- {item}" for item in notes)
    return str(notes).strip()

def get_release_download_url(metadata):
    return str(metadata.get("download_url", "")).strip() or DEFAULT_RELEASE_DOWNLOAD_URL

def open_update_download(metadata):
    download_url = get_release_download_url(metadata) or DEFAULT_RELEASE_PAGE_URL
    webbrowser.open(download_url)

def get_update_summary_lines(latest_version):
    return [
        f"Current version: {APP_VERSION}",
        f"Latest version: {latest_version}"
    ]

def get_runtime_app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def is_packaged_desktop_app():
    return getattr(sys, "frozen", False)

def download_update_package(metadata):
    download_url = get_release_download_url(metadata)
    if not download_url:
        raise ValueError("Update metadata does not contain a downloadable ZIP URL.")

    temp_dir = Path(tempfile.mkdtemp(prefix="pwp_update_"))
    zip_path = temp_dir / "PWPDesktopApp.zip"
    with requests.get(download_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(zip_path, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_handle.write(chunk)
    return zip_path

def extract_update_package(zip_path):
    extract_dir = zip_path.parent / "extracted"
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    expected_exe = extract_dir / APP_EXECUTABLE_NAME
    if not expected_exe.exists():
        raise ValueError("Downloaded update package is missing PWPDesktopApp.exe.")
    return extract_dir

def launch_updater_script(extract_dir):
    target_dir = get_runtime_app_dir()
    target_exe = target_dir / APP_EXECUTABLE_NAME
    source_dir = Path(extract_dir).resolve()
    cleanup_dir = source_dir.parent
    script_path = cleanup_dir / "apply_update.ps1"

    script_content = f"""$ErrorActionPreference = "Stop"
Start-Sleep -Seconds 2
$sourceDir = "{source_dir}"
$targetDir = "{target_dir}"

Copy-Item (Join-Path $sourceDir "{APP_EXECUTABLE_NAME}") (Join-Path $targetDir "{APP_EXECUTABLE_NAME}") -Force
if (Test-Path (Join-Path $sourceDir "desktop_release.json")) {{
    Copy-Item (Join-Path $sourceDir "desktop_release.json") (Join-Path $targetDir "desktop_release.json") -Force
}}
if (Test-Path (Join-Path $sourceDir "CLIENT_README.txt")) {{
    Copy-Item (Join-Path $sourceDir "CLIENT_README.txt") (Join-Path $targetDir "CLIENT_README.txt") -Force
}}

Start-Process "{target_exe}"
Start-Sleep -Seconds 2
Remove-Item "{cleanup_dir}" -Recurse -Force
"""

    script_path.write_text(script_content, encoding="utf-8")
    creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path)
        ],
        creationflags=creation_flags
    )

def start_auto_update(metadata, latest_version):
    if not is_packaged_desktop_app():
        messagebox.showinfo(
            "Auto Update Not Available",
            "Automatic self-update works only in the packaged desktop EXE.\n\n"
            "The download page will open instead."
        )
        open_update_download(metadata)
        return

    if 'update_status' in globals():
        update_status(f"Downloading version {latest_version}...", "info")

    def worker():
        try:
            zip_path = download_update_package(metadata)
            extract_dir = extract_update_package(zip_path)
        except Exception as e:
            root.after(
                0,
                lambda: messagebox.showerror(
                    "Update Failed",
                    "The app could not download or prepare the update package.\n\n"
                    f"Reason: {e}"
                )
            )
            root.after(0, lambda: update_status("Automatic update failed.", "error"))
            return

        def install_update():
            if 'update_status' in globals():
                update_status(f"Installing version {latest_version} and restarting...", "info")
            messagebox.showinfo(
                "Installing Update",
                f"Version {latest_version} has been downloaded.\n\n"
                "The app will now close, replace itself, and restart automatically."
            )
            launch_updater_script(extract_dir)
            root.after(300, root.destroy)

        root.after(0, install_update)

    threading.Thread(target=worker, daemon=True).start()

def handle_update_success(metadata, show_latest_message, auto_check):
    latest_version = str(metadata.get("version", "")).strip()
    if not latest_version:
        if not auto_check:
            messagebox.showwarning("Update Check", "Update metadata is missing a version number.")
        return

    if is_newer_version(latest_version, APP_VERSION):
        release_notes = build_release_notes_text(metadata)
        prompt_lines = get_update_summary_lines(latest_version)
        if release_notes:
            prompt_lines.extend(["", "Release notes:", release_notes])
        prompt_lines.extend(["", "Do you want to download and install the update now?"])
        if 'update_status' in globals():
            update_status(f"New version {latest_version} is available.", "info")
        if messagebox.askyesno("Update Available", "\n".join(prompt_lines)):
            start_auto_update(metadata, latest_version)
        return

    if 'update_status' in globals():
        update_status(f"You are using the latest desktop version ({APP_VERSION}).", "success")
    if show_latest_message:
        messagebox.showinfo(
            "No Updates",
            "\n".join(get_update_summary_lines(latest_version)) + "\n\nYou are already using the latest desktop version."
        )

def handle_update_error(error_message, auto_check):
    if 'update_status' in globals():
        update_status("Unable to check for updates right now.", "error")
    if not auto_check:
        messagebox.showwarning(
            "Update Check Failed",
            "The app could not check GitHub for a newer version right now.\n\n"
            f"Reason: {error_message}\n\n"
            "Please verify your internet connection and try again later."
        )

def check_for_updates(show_latest_message=True, auto_check=False):
    if 'update_status' in globals():
        update_status("Checking for desktop updates...", "info")

    def worker():
        try:
            metadata = fetch_release_metadata()
        except Exception as e:
            root.after(0, lambda: handle_update_error(str(e), auto_check))
            return
        root.after(0, lambda: handle_update_success(metadata, show_latest_message, auto_check))

    threading.Thread(target=worker, daemon=True).start()


def normalize_license_key(value):
    return str(value or "").strip().upper()


def normalize_gst(value):
    return str(value or "").strip().upper()


def normalize_gst_list(values):
    if isinstance(values, str):
        values = [values]
    return [normalize_gst(item) for item in (values or []) if normalize_gst(item)]


def get_machine_id():
    try:
        import machineid
        return machineid.hashed_id("recirculytics-pwp")
    except Exception:
        pass

    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography"
        )
        machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        return hashlib.sha256(str(machine_guid).encode("utf-8")).hexdigest()
    except Exception:
        return hashlib.sha256(platform.node().encode("utf-8")).hexdigest()


def get_license_cache_candidates():
    return [
        PRIMARY_CACHE_ROOT / "ReCirculytics" / "lc.cache",
        FALLBACK_CACHE_ROOT / "lc.cache",
    ]


def save_license_cache(data):
    cache_data = dict(data)
    cache_data["cached_at"] = time.time()
    for cache_file in get_license_cache_candidates():
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
            return
        except Exception:
            continue


def load_cached_license_file():
    for cache_file in get_license_cache_candidates():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def load_cached_license(license_key):
    cached = load_cached_license_file()
    if not cached:
        return None
    if normalize_license_key(cached.get("key")) != normalize_license_key(license_key):
        return None
    if time.time() - float(cached.get("cached_at", 0)) >= LICENSE_GRACE_SECS:
        return None
    return cached


def get_cached_license_key():
    cached = load_cached_license_file() or {}
    return normalize_license_key(cached.get("key", ""))


def apply_license_info(license_key, response_data, gst_verified=False, portal_gst=""):
    _license_info.update({
        "key": normalize_license_key(license_key),
        "customer_name": str(response_data.get("customer_name", "")).strip(),
        "tier": str(response_data.get("tier", "")).strip(),
        "expires_on": str(response_data.get("expires_on", "")).strip(),
        "allowed_gsts": normalize_gst_list(response_data.get("allowed_gsts", [])),
        "fy_start": str(response_data.get("fy_start", "")).strip(),
        "fy_end": str(response_data.get("fy_end", "")).strip(),
        "portal_gst": normalize_gst(portal_gst or response_data.get("gst", "")),
        "offline": bool(response_data.get("offline", False)),
        "license_verified": bool(response_data.get("ok", False)),
        "gst_verified": bool(gst_verified),
    })


def validate_license_online(license_key, gst=""):
    normalized_key = normalize_license_key(license_key)
    normalized_gst = normalize_gst(gst)
    payload = {
        "license_key": normalized_key,
        "machine_id": get_machine_id(),
        "gst": normalized_gst,
        "sw_version": SW_VERSION,
    }

    try:
        response = requests.post(LICENSE_VALIDATE_URL, json=payload, timeout=10)
    except requests.exceptions.ConnectionError:
        cached = load_cached_license(normalized_key)
        if cached:
            return {
                "ok": True,
                "offline": True,
                "customer_name": cached.get("customer_name", ""),
                "tier": cached.get("tier", ""),
                "expires_on": cached.get("expires_on", ""),
                "allowed_gsts": cached.get("allowed_gsts", []),
                "fy_start": cached.get("fy_start", ""),
                "fy_end": cached.get("fy_end", ""),
                "gst": normalized_gst,
            }
        return {
            "ok": False,
            "message": "Cannot reach the license server and no recent cached session was found."
        }
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "message": "License server timed out. Please check your internet connection and try again."
        }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"License validation error: {exc}"
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "message": (
                f"License server returned HTTP {response.status_code}. "
                "Please contact support@recirculytics.in."
            ),
        }

    try:
        data = response.json()
    except Exception:
        return {
            "ok": False,
            "message": "License server returned an unreadable response."
        }

    if data.get("status") == "valid":
        cache_payload = {
            "key": normalized_key,
            "customer_name": data.get("customer_name", ""),
            "tier": data.get("tier", ""),
            "expires_on": data.get("expires_on", ""),
            "allowed_gsts": normalize_gst_list(data.get("allowed_gsts", [])),
            "fy_start": data.get("fy_start", ""),
            "fy_end": data.get("fy_end", ""),
        }
        save_license_cache(cache_payload)
        return {
            "ok": True,
            **cache_payload,
            "gst": normalized_gst,
        }

    return {
        "ok": False,
        "code": data.get("code", "UNKNOWN"),
        "message": data.get("message", "License validation failed."),
    }


def build_license_summary_lines():
    allowed_gsts = ", ".join(_license_info.get("allowed_gsts", [])) or "Not set"
    footer_mode = "Offline grace mode" if _license_info.get("offline") else "Online validated"
    return [
        f"Customer: {_license_info.get('customer_name') or 'Not available'}",
        f"Tier: {_license_info.get('tier') or 'Not available'}",
        f"Expires: {_license_info.get('expires_on') or 'Not available'}",
        f"Allowed GST: {allowed_gsts}",
        f"License key: {_license_info.get('key') or 'Not available'}",
        f"Validation mode: {footer_mode}",
    ]


def build_about_text():
    lines = [
        "PWP Automation Dashboard",
        f"Desktop version: {APP_VERSION}",
        "",
        "License",
    ]
    lines.extend(build_license_summary_lines())
    portal_gst = _license_info.get("portal_gst") or "Not verified"
    lines.extend([
        f"Portal GST: {portal_gst}",
        f"GST verified: {'Yes' if _license_info.get('gst_verified') else 'No'}",
    ])
    return "\n".join(lines)


def scrape_portal_gst_candidates():
    if 'driver' not in globals() or driver is None:
        return []

    text_fragments = []
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if body_text:
            text_fragments.append(body_text)
    except Exception:
        pass

    try:
        if driver.page_source:
            text_fragments.append(driver.page_source)
    except Exception:
        pass

    candidates = []
    seen = set()
    for fragment in text_fragments:
        for match in GST_PATTERN.findall(fragment.upper()):
            if match not in seen:
                seen.add(match)
                candidates.append(match)
    return candidates


def verify_portal_gst_against_license():
    license_key = _license_info.get("key")
    if not license_key:
        return False, "License key is not available in this session."

    candidates = scrape_portal_gst_candidates()
    if not candidates:
        return False, (
            "Unable to detect GST on the CPCB page. After logging in, open the page or profile "
            "where GST is visible, then try Login again."
        )

    last_error = "Unable to validate the portal GST."
    for portal_gst in candidates:
        response = validate_license_online(license_key, portal_gst)
        if response.get("ok"):
            apply_license_info(license_key, response, gst_verified=True, portal_gst=portal_gst)
            return True, portal_gst
        last_error = response.get("message", last_error)

    _license_info["gst_verified"] = False
    return False, last_error


class LicenseGateDialog:
    def __init__(self, master):
        self.master = master
        self.result = False
        self.license_key = ""

        self.window = tk.Toplevel()
        self.window.title("License Validation")
        self.window.configure(bg="#F8FAFC")
        self.window.resizable(False, False)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        self.status_var = tk.StringVar(value="Enter your license key to continue.")
        self.key_var = tk.StringVar(value=get_cached_license_key())

        container = tk.Frame(self.window, bg="#F8FAFC", padx=18, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="PWP Automation Tool - Licensed Edition",
            bg="#F8FAFC",
            fg="#0F172A",
            font=("Verdana", 11, "bold"),
        ).pack(anchor="w")

        tk.Label(
            container,
            text="ReCirculytics Sustainable Solutions LLP",
            bg="#F8FAFC",
            fg="#475569",
            font=("Verdana", 9),
        ).pack(anchor="w", pady=(4, 10))

        tk.Label(
            container,
            text="License Key",
            bg="#F8FAFC",
            fg="#334155",
            font=("Verdana", 9, "bold"),
        ).pack(anchor="w")

        self.entry = tk.Entry(container, textvariable=self.key_var, width=42, font=("Verdana", 10))
        self.entry.pack(fill="x", pady=(6, 10))
        self.entry.focus_set()

        tk.Label(
            container,
            textvariable=self.status_var,
            bg="#F8FAFC",
            fg="#0F766E",
            justify="left",
            wraplength=360,
            font=("Verdana", 9),
        ).pack(anchor="w", pady=(0, 12))

        button_row = tk.Frame(container, bg="#F8FAFC")
        button_row.pack(fill="x")

        self.validate_button = tk.Button(
            button_row,
            text="Validate License",
            command=self.validate,
            bg="#0F766E",
            fg="#FFFFFF",
            activebackground="#115E59",
            activeforeground="#FFFFFF",
            width=18,
            cursor="hand2",
        )
        self.validate_button.pack(side="left")

        tk.Button(
            button_row,
            text="Cancel",
            command=self.cancel,
            bg="#E2E8F0",
            fg="#0F172A",
            activebackground="#CBD5E1",
            activeforeground="#0F172A",
            width=12,
            cursor="hand2",
        ).pack(side="right")

        self.window.bind("<Return>", lambda _event: self.validate())
        self.window.bind("<Escape>", lambda _event: self.cancel())

        self.window.update_idletasks()
        x = self.master.winfo_screenwidth() // 2 - self.window.winfo_reqwidth() // 2
        y = self.master.winfo_screenheight() // 2 - self.window.winfo_reqheight() // 2
        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.window.attributes("-topmost", True)
        self.window.after(300, lambda: self.window.attributes("-topmost", False))

    def validate(self):
        license_key = normalize_license_key(self.key_var.get())
        if not license_key:
            self.status_var.set("Enter a valid license key.")
            return

        self.validate_button.config(state="disabled")
        self.status_var.set("Validating license with the server...")
        self.window.update_idletasks()

        response = validate_license_online(license_key)
        if response.get("ok"):
            apply_license_info(license_key, response, gst_verified=False)
            self.license_key = license_key
            self.result = True
            self.window.destroy()
            return

        self.status_var.set(response.get("message", "License validation failed."))
        self.validate_button.config(state="normal")

    def cancel(self):
        self.result = False
        self.window.destroy()


def show_about_dialog():
    messagebox.showinfo("About", build_about_text())


def run_startup_license_gate():
    dialog = LicenseGateDialog(root)
    root.wait_window(dialog.window)
    return dialog.result

def custom_wait_clickable_and_click(driver, locator, attempts=10):
    count = 0
    success = False
    while count < attempts:
        try:
            elem = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator))
            elem.click()
            success = True
            break
        except Exception as e:
            print(f"Attempt {count+1} failed: {e}")
            time.sleep(1)
            count += 1
    if not success:
        driver.save_screenshot(f"error_{locator[1]}.png")
        raise Exception(f"Failed to click element: {locator}")

STATE_DISTRICT_MASTER_RAW = """
ANDAMAN AND NICOBAR ISLANDS|Nicobar
ANDAMAN AND NICOBAR ISLANDS|North and Middle Andaman
ANDAMAN AND NICOBAR ISLANDS|South Andaman
ANDHRA PRADESH|Anantapur
ANDHRA PRADESH|Chittoor
ANDHRA PRADESH|East Godavari
ANDHRA PRADESH|Guntur
ANDHRA PRADESH|Krishna
ANDHRA PRADESH|Kurnool
ANDHRA PRADESH|Nellore
ANDHRA PRADESH|Prakasam
ANDHRA PRADESH|Srikakulam
ANDHRA PRADESH|Visakhapatnam
ANDHRA PRADESH|Vizianagaram
ANDHRA PRADESH|West Godavari
ANDHRA PRADESH|YSR Kadapa
ARUNACHAL PRADESH|Tawang
ARUNACHAL PRADESH|West Kameng
ARUNACHAL PRADESH|East Kameng
ARUNACHAL PRADESH|Papum Pare
ARUNACHAL PRADESH|Kurung Kumey
ARUNACHAL PRADESH|Kra Daadi
ARUNACHAL PRADESH|Lower Subansiri
ARUNACHAL PRADESH|Upper Subansiri
ARUNACHAL PRADESH|West Siang
ARUNACHAL PRADESH|East Siang
ARUNACHAL PRADESH|Siang
ARUNACHAL PRADESH|Upper Siang
ARUNACHAL PRADESH|Lower Siang
ARUNACHAL PRADESH|Lower Dibang Valley
ARUNACHAL PRADESH|Dibang Valley
ARUNACHAL PRADESH|Anjaw
ARUNACHAL PRADESH|Lohit
ARUNACHAL PRADESH|Namsai
ARUNACHAL PRADESH|Changlang
ARUNACHAL PRADESH|Tirap
ARUNACHAL PRADESH|Longding
ASSAM|Baksa
ASSAM|Barpeta
ASSAM|Biswanath
ASSAM|Bongaigaon
ASSAM|Cachar
ASSAM|Charaideo
ASSAM|Chirang
ASSAM|Darrang
ASSAM|Dhemaji
ASSAM|Dhubri
ASSAM|Dibrugarh
ASSAM|Goalpara
ASSAM|Golaghat
ASSAM|Hailakandi
ASSAM|Hojai
ASSAM|Jorhat
ASSAM|Kamrup Metropolitan
ASSAM|Kamrup
ASSAM|Karbi Anglong
ASSAM|Karimganj
ASSAM|Kokrajhar
ASSAM|Lakhimpur
ASSAM|Majuli
ASSAM|Morigaon
ASSAM|Nagaon
ASSAM|Nalbari
ASSAM|Dima Hasao
ASSAM|Sivasagar
ASSAM|Sonitpur
ASSAM|South Salmara-Mankachar
ASSAM|Tinsukia
ASSAM|Udalguri
ASSAM|West Karbi Anglong
BIHAR|Araria
BIHAR|Arwal
BIHAR|Aurangabad
BIHAR|Banka
BIHAR|Begusarai
BIHAR|Bhagalpur
BIHAR|Bhojpur
BIHAR|Buxar
BIHAR|Darbhanga
BIHAR|East Champaran (Motihari)
BIHAR|Gaya
BIHAR|Gopalganj
BIHAR|Jamui
BIHAR|Jehanabad
BIHAR|Kaimur (Bhabua)
BIHAR|Katihar
BIHAR|Khagaria
BIHAR|Kishanganj
BIHAR|Lakhisarai
BIHAR|Madhepura
BIHAR|Madhubani
BIHAR|Munger (Monghyr)
BIHAR|Muzaffarpur
BIHAR|Nalanda
BIHAR|Nawada
BIHAR|Patna
BIHAR|Purnia (Purnea)
BIHAR|Rohtas
BIHAR|Saharsa
BIHAR|Samastipur
BIHAR|Saran
BIHAR|Sheikhpura
BIHAR|Sheohar
BIHAR|Sitamarhi
BIHAR|Siwan
BIHAR|Supaul
BIHAR|Vaishali
BIHAR|West Champaran
CHANDIGARH|Chandigarh
CHHATTISGARH|Balod
CHHATTISGARH|Baloda Bazar
CHHATTISGARH|Balrampur
CHHATTISGARH|Bastar
CHHATTISGARH|Bemetara
CHHATTISGARH|Bijapur
CHHATTISGARH|Bilaspur
CHHATTISGARH|Dantewada (South Bastar)
CHHATTISGARH|Dhamtari
CHHATTISGARH|Durg
CHHATTISGARH|Gariyaband
CHHATTISGARH|Janjgir-Champa
CHHATTISGARH|Jashpur
CHHATTISGARH|Kabirdham (Kawardha)
CHHATTISGARH|Kanker (North Bastar)
CHHATTISGARH|Kondagaon
CHHATTISGARH|Korba
CHHATTISGARH|Korea (Koriya)
CHHATTISGARH|Mahasamund
CHHATTISGARH|Mungeli
CHHATTISGARH|Narayanpur
CHHATTISGARH|Raigarh
CHHATTISGARH|Raipur
CHHATTISGARH|Rajnandgaon
CHHATTISGARH|Sukma
CHHATTISGARH|Surajpur
CHHATTISGARH|Surguja
DADRA AND NAGAR HAVELI AND DAMAN AND DIU|Dadra & Nagar Haveli
DELHI|Central Delhi
DELHI|East Delhi
DELHI|New Delhi
DELHI|North Delhi
DELHI|North East Delhi
DELHI|North West Delhi
DELHI|Shahdara
DELHI|South Delhi
DELHI|South East Delhi
DELHI|South West Delhi
DELHI|West Delhi
GOA|North Goa
GOA|South Goa
GUJARAT|Ahmedabad
GUJARAT|Amreli
GUJARAT|Anand
GUJARAT|Aravalli
GUJARAT|Banaskantha (Palanpur)
GUJARAT|Bharuch
GUJARAT|Bhavnagar
GUJARAT|Botad
GUJARAT|Chhota Udepur
GUJARAT|Dahod
GUJARAT|Dangs (Ahwa)
GUJARAT|Devbhoomi Dwarka
GUJARAT|Gandhinagar
GUJARAT|Gir Somnath
GUJARAT|Jamnagar
GUJARAT|Junagadh
GUJARAT|Kachchh
GUJARAT|Kheda (Nadiad)
GUJARAT|Mahisagar
GUJARAT|Mehsana
GUJARAT|Morbi
GUJARAT|Narmada (Rajpipla)
GUJARAT|Navsari
GUJARAT|Panchmahal (Godhra)
GUJARAT|Patan
GUJARAT|Porbandar
GUJARAT|Rajkot
GUJARAT|Sabarkantha (Himmatnagar)
GUJARAT|Surat
GUJARAT|Surendranagar
GUJARAT|Tapi (Vyara)
GUJARAT|Vadodara
GUJARAT|Valsad
HARYANA|Ambala
HARYANA|Bhiwani
HARYANA|Charkhi Dadri
HARYANA|Faridabad
HARYANA|Fatehabad
HARYANA|Gurgaon
HARYANA|Hisar
HARYANA|Jhajjar
HARYANA|Jind
HARYANA|Kaithal
HARYANA|Karnal
HARYANA|Kurukshetra
HARYANA|Mahendragarh
HARYANA|Mewat
HARYANA|Palwal
HARYANA|Panchkula
HARYANA|Panipat
HARYANA|Rewari
HARYANA|Rohtak
HARYANA|Sirsa
HARYANA|Sonipat
HARYANA|Yamunanagar
HIMACHAL PRADESH|Bilaspur
HIMACHAL PRADESH|Chamba
HIMACHAL PRADESH|Hamirpur
HIMACHAL PRADESH|Kangra
HIMACHAL PRADESH|Kinnaur
HIMACHAL PRADESH|Kullu
HIMACHAL PRADESH|Lahaul & Spiti
HIMACHAL PRADESH|Mandi
HIMACHAL PRADESH|Shimla
HIMACHAL PRADESH|Sirmaur (Sirmour)
HIMACHAL PRADESH|Solan
HIMACHAL PRADESH|Una
JAMMU AND KASHMIR|Anantnag
JAMMU AND KASHMIR|Bandipore
JAMMU AND KASHMIR|Baramulla
JAMMU AND KASHMIR|Budgam
JAMMU AND KASHMIR|Doda
JAMMU AND KASHMIR|Ganderbal
JAMMU AND KASHMIR|Jammu
JAMMU AND KASHMIR|Kargil
JAMMU AND KASHMIR|Kathua
JAMMU AND KASHMIR|Kishtwar
JAMMU AND KASHMIR|Kulgam
JAMMU AND KASHMIR|Kupwara
JAMMU AND KASHMIR|Leh
JAMMU AND KASHMIR|Poonch
JAMMU AND KASHMIR|Pulwama
JAMMU AND KASHMIR|Rajouri
JAMMU AND KASHMIR|Ramban
JAMMU AND KASHMIR|Reasi
JAMMU AND KASHMIR|Samba
JAMMU AND KASHMIR|Shopian
JAMMU AND KASHMIR|Srinagar
JAMMU AND KASHMIR|Udhampur
JHARKHAND|Bokaro
JHARKHAND|Chatra
JHARKHAND|Deoghar
JHARKHAND|Dhanbad
JHARKHAND|Dumka
JHARKHAND|East Singhbhum
JHARKHAND|Garhwa
JHARKHAND|Giridih
JHARKHAND|Godda
JHARKHAND|Gumla
JHARKHAND|Hazaribag
JHARKHAND|Jamtara
JHARKHAND|Khunti
JHARKHAND|Koderma
JHARKHAND|Latehar
JHARKHAND|Lohardaga
JHARKHAND|Pakur
JHARKHAND|Palamu
JHARKHAND|Ramgarh
JHARKHAND|Ranchi
JHARKHAND|Sahibganj
JHARKHAND|Seraikela-Kharsawan
JHARKHAND|Simdega
JHARKHAND|West Singhbhum
KARNATAKA|Bagalkot
KARNATAKA|Ballari (Bellary)
KARNATAKA|Belagavi (Belgaum)
KARNATAKA|Bengaluru (Bangalore) Rural
KARNATAKA|Bengaluru (Bangalore) Urban
KARNATAKA|Bidar
KARNATAKA|Chamarajanagar
KARNATAKA|Chikballapur
KARNATAKA|Chikkamagaluru (Chikmagalur)
KARNATAKA|Chitradurga
KARNATAKA|Dakshina Kannada
KARNATAKA|Davangere
KARNATAKA|Dharwad
KARNATAKA|Gadag
KARNATAKA|Hassan
KARNATAKA|Haveri
KARNATAKA|Kalaburagi (Gulbarga)
KARNATAKA|Kodagu
KARNATAKA|Kolar
KARNATAKA|Koppal
KARNATAKA|Mandya
KARNATAKA|Mysuru (Mysore)
KARNATAKA|Raichur
KARNATAKA|Ramanagara
KARNATAKA|Shivamogga (Shimoga)
KARNATAKA|Tumakuru (Tumkur)
KARNATAKA|Udupi
KARNATAKA|Uttara Kannada (Karwar)
KARNATAKA|Vijayapura (Bijapur)
KARNATAKA|Yadgir
KERALA|Alappuzha
KERALA|Ernakulam
KERALA|Idukki
KERALA|Kannur
KERALA|Kasaragod
KERALA|Kollam
KERALA|Kottayam
KERALA|Kozhikode
KERALA|Malappuram
KERALA|Palakkad
KERALA|Pathanamthitta
KERALA|Thiruvananthapuram
KERALA|Thrissur
KERALA|Wayanad
LADAKH|Kargil
LADAKH|Leh
LAKSHADWEEP|Agatti
LAKSHADWEEP|Amini
LAKSHADWEEP|Androth
LAKSHADWEEP|Bithra
LAKSHADWEEP|Chethlath
LAKSHADWEEP|Kavaratti
LAKSHADWEEP|Kadmath
LAKSHADWEEP|Kalpeni
LAKSHADWEEP|Kilthan
LAKSHADWEEP|Minicoy
MADHYA PRADESH|Agar Malwa
MADHYA PRADESH|Alirajpur
MADHYA PRADESH|Anuppur
MADHYA PRADESH|Ashoknagar
MADHYA PRADESH|Balaghat
MADHYA PRADESH|Barwani
MADHYA PRADESH|Betul
MADHYA PRADESH|Bhind
MADHYA PRADESH|Bhopal
MADHYA PRADESH|Burhanpur
MADHYA PRADESH|Chhatarpur
MADHYA PRADESH|Chhindwara
MADHYA PRADESH|Damoh
MADHYA PRADESH|Datia
MADHYA PRADESH|Dewas
MADHYA PRADESH|Dhar
MADHYA PRADESH|Dindori
MADHYA PRADESH|Guna
MADHYA PRADESH|Gwalior
MADHYA PRADESH|Harda
MADHYA PRADESH|Hoshangabad
MADHYA PRADESH|Indore
MADHYA PRADESH|Jabalpur
MADHYA PRADESH|Jhabua
MADHYA PRADESH|Katni
MADHYA PRADESH|Khandwa
MADHYA PRADESH|Khargone
MADHYA PRADESH|Mandla
MADHYA PRADESH|Mandsaur
MADHYA PRADESH|Morena
MADHYA PRADESH|Narsinghpur
MADHYA PRADESH|Neemuch
MADHYA PRADESH|Panna
MADHYA PRADESH|Raisen
MADHYA PRADESH|Rajgarh
MADHYA PRADESH|Ratlam
MADHYA PRADESH|Rewa
MADHYA PRADESH|Sagar
MADHYA PRADESH|Satna
MADHYA PRADESH|Sehore
MADHYA PRADESH|Seoni
MADHYA PRADESH|Shahdol
MADHYA PRADESH|Shajapur
MADHYA PRADESH|Sheopur
MADHYA PRADESH|Shivpuri
MADHYA PRADESH|Sidhi
MADHYA PRADESH|Singrauli
MADHYA PRADESH|Tikamgarh
MADHYA PRADESH|Ujjain
MADHYA PRADESH|Umaria
MADHYA PRADESH|Vidisha
MAHARASHTRA|Ahmednagar
MAHARASHTRA|Akola
MAHARASHTRA|Amravati
MAHARASHTRA|Aurangabad
MAHARASHTRA|Beed
MAHARASHTRA|Bhandara
MAHARASHTRA|Buldhana
MAHARASHTRA|Chandrapur
MAHARASHTRA|Dhule
MAHARASHTRA|Gadchiroli
MAHARASHTRA|Gondia
MAHARASHTRA|Hingoli
MAHARASHTRA|Jalgaon
MAHARASHTRA|Jalna
MAHARASHTRA|Kolhapur
MAHARASHTRA|Latur
MAHARASHTRA|Mumbai City
MAHARASHTRA|Mumbai Suburban
MAHARASHTRA|Nagpur
MAHARASHTRA|Nanded
MAHARASHTRA|Nandurbar
MAHARASHTRA|Nashik
MAHARASHTRA|Osmanabad
MAHARASHTRA|Palghar
MAHARASHTRA|Parbhani
MAHARASHTRA|Pune
MAHARASHTRA|Raigad
MAHARASHTRA|Ratnagiri
MAHARASHTRA|Sangli
MAHARASHTRA|Satara
MAHARASHTRA|Sindhudurg
MAHARASHTRA|Solapur
MAHARASHTRA|Thane
MAHARASHTRA|Wardha
MAHARASHTRA|Washim
MAHARASHTRA|Yavatmal
MANIPUR|Bishnupur
MANIPUR|Chandel
MANIPUR|Churachandpur
MANIPUR|Imphal East
MANIPUR|Imphal West
MANIPUR|Jiribam
MANIPUR|Kakching
MANIPUR|Kamjong
MANIPUR|Kangpokpi
MANIPUR|Noney
MANIPUR|Pherzawl
MANIPUR|Senapati
MANIPUR|Tamenglong
MANIPUR|Tengnoupal
MANIPUR|Thoubal
MANIPUR|Ukhrul
MEGHALAYA|East Garo Hills
MEGHALAYA|East Jaintia Hills
MEGHALAYA|East Khasi Hills
MEGHALAYA|North Garo Hills
MEGHALAYA|Ri Bhoi
MEGHALAYA|South Garo Hills
MEGHALAYA|South West Garo Hills
MEGHALAYA|South West Khasi Hills
MEGHALAYA|West Garo Hills
MEGHALAYA|West Jaintia Hills
MEGHALAYA|West Khasi Hills
MIZORAM|Aizawl
MIZORAM|Champhai
MIZORAM|Kolasib
MIZORAM|Lawngtlai
MIZORAM|Lunglei
MIZORAM|Mamit
MIZORAM|Saiha
MIZORAM|Serchhip
NAGALAND|Dimapur
NAGALAND|Kiphire
NAGALAND|Kohima
NAGALAND|Longleng
NAGALAND|Mokokchung
NAGALAND|Mon
NAGALAND|Peren
NAGALAND|Phek
NAGALAND|Tuensang
NAGALAND|Wokha
NAGALAND|Zunheboto
ODISHA|Angul
ODISHA|Balangir
ODISHA|Balasore
ODISHA|Bargarh
ODISHA|Bhadrak
ODISHA|Boudh
ODISHA|Cuttack
ODISHA|Deogarh
ODISHA|Dhenkanal
ODISHA|Gajapati
ODISHA|Ganjam
ODISHA|Jagatsinghapur
ODISHA|Jajpur
ODISHA|Jharsuguda
ODISHA|Kalahandi
ODISHA|Kandhamal
ODISHA|Kendrapara
ODISHA|Kendujhar (Keonjhar)
ODISHA|Khordha
ODISHA|Koraput
ODISHA|Malkangiri
ODISHA|Mayurbhanj
ODISHA|Nabarangpur
ODISHA|Nayagarh
ODISHA|Nuapada
ODISHA|Puri
ODISHA|Rayagada
ODISHA|Sambalpur
ODISHA|Sonepur
ODISHA|Sundargarh
PONDICHERRY|Pondicherry
PONDICHERRY|Karaikal
PONDICHERRY|Mahe
PONDICHERRY|Yanam
PUNJAB|Amritsar
PUNJAB|Barnala
PUNJAB|Bathinda
PUNJAB|Faridkot
PUNJAB|Fatehgarh Sahib
PUNJAB|Fazilka
PUNJAB|Ferozepur
PUNJAB|Gurdaspur
PUNJAB|Hoshiarpur
PUNJAB|Jalandhar
PUNJAB|Kapurthala
PUNJAB|Ludhiana
PUNJAB|Mansa
PUNJAB|Moga
PUNJAB|Muktsar
PUNJAB|Nawanshahr (Shahid Bhagat Singh Nagar)
PUNJAB|Pathankot
PUNJAB|Patiala
PUNJAB|Rupnagar
PUNJAB|Sahibzada Ajit Singh Nagar (Mohali)
PUNJAB|Sangrur
PUNJAB|Tarn Taran
RAJASTHAN|Ajmer
RAJASTHAN|Alwar
RAJASTHAN|Banswara
RAJASTHAN|Baran
RAJASTHAN|Barmer
RAJASTHAN|Bharatpur
RAJASTHAN|Bhilwara
RAJASTHAN|Bikaner
RAJASTHAN|Bundi
RAJASTHAN|Chittorgarh
RAJASTHAN|Churu
RAJASTHAN|Dausa
RAJASTHAN|Dholpur
RAJASTHAN|Dungarpur
RAJASTHAN|Hanumangarh
RAJASTHAN|Jaipur
RAJASTHAN|Jaisalmer
RAJASTHAN|Jalore
RAJASTHAN|Jhalawar
RAJASTHAN|Jhunjhunu
RAJASTHAN|Jodhpur
RAJASTHAN|Karauli
RAJASTHAN|Kota
RAJASTHAN|Nagaur
RAJASTHAN|Pali
RAJASTHAN|Pratapgarh
RAJASTHAN|Rajsamand
RAJASTHAN|Sawai Madhopur
RAJASTHAN|Sikar
RAJASTHAN|Sirohi
RAJASTHAN|Sri Ganganagar
RAJASTHAN|Tonk
RAJASTHAN|Udaipur
SIKKIM|East Sikkim
SIKKIM|North Sikkim
SIKKIM|South Sikkim
SIKKIM|West Sikkim
TAMIL NADU|Ariyalur
TAMIL NADU|Chennai
TAMIL NADU|Coimbatore
TAMIL NADU|Cuddalore
TAMIL NADU|Dharmapuri
TAMIL NADU|Dindigul
TAMIL NADU|Erode
TAMIL NADU|Kanchipuram
TAMIL NADU|Kanyakumari
TAMIL NADU|Karur
TAMIL NADU|Krishnagiri
TAMIL NADU|Madurai
TAMIL NADU|Nagapattinam
TAMIL NADU|Namakkal
TAMIL NADU|Nilgiris
TAMIL NADU|Perambalur
TAMIL NADU|Pudukkottai
TAMIL NADU|Ramanathapuram
TAMIL NADU|Salem
TAMIL NADU|Sivaganga
TAMIL NADU|Thanjavur
TAMIL NADU|Theni
TAMIL NADU|Thoothukudi (Tuticorin)
TAMIL NADU|Tiruchirappalli
TAMIL NADU|Tirunelveli
TAMIL NADU|Tiruppur
TAMIL NADU|Tiruvallur
TAMIL NADU|Tiruvannamalai
TAMIL NADU|Tiruvarur
TAMIL NADU|Vellore
TAMIL NADU|Viluppuram
TAMIL NADU|Virudhunagar
TELANGANA|Adilabad
TELANGANA|Bhadradri Kothagudem
TELANGANA|Hyderabad
TELANGANA|Jagtial
TELANGANA|Jangaon
TELANGANA|Jayashankar Bhoopalpally
TELANGANA|Jogulamba Gadwal
TELANGANA|Kamareddy
TELANGANA|Karimnagar
TELANGANA|Khammam
TELANGANA|Komaram Bheem Asifabad
TELANGANA|Mahabubabad
TELANGANA|Mahabubnagar
TELANGANA|Mancherial
TELANGANA|Medak
TELANGANA|Medchal
TELANGANA|Nagarkurnool
TELANGANA|Nalgonda
TELANGANA|Nirmal
TELANGANA|Nizamabad
TELANGANA|Peddapalli
TELANGANA|Rajanna Sircilla
TELANGANA|Rangareddy
TELANGANA|Sangareddy
TELANGANA|Siddipet
TELANGANA|Suryapet
TELANGANA|Vikarabad
TELANGANA|Wanaparthy
TELANGANA|Warangal (Rural)
TELANGANA|Warangal (Urban)
TELANGANA|Yadadri Bhuvanagiri
TRIPURA|Dhalai
TRIPURA|Gomati
TRIPURA|Khowai
TRIPURA|North Tripura
TRIPURA|Sepahijala
TRIPURA|South Tripura
TRIPURA|Unakoti
TRIPURA|West Tripura
UTTAR PRADESH|Agra
UTTAR PRADESH|Aligarh
UTTAR PRADESH|Allahabad
UTTAR PRADESH|Ambedkar Nagar
UTTAR PRADESH|Amethi (Chatrapati Sahuji Mahraj Nagar)
UTTAR PRADESH|Amroha (J.P. Nagar)
UTTAR PRADESH|Auraiya
UTTAR PRADESH|Azamgarh
UTTAR PRADESH|Baghpat
UTTAR PRADESH|Bahraich
UTTAR PRADESH|Ballia
UTTAR PRADESH|Balrampur
UTTAR PRADESH|Banda
UTTAR PRADESH|Barabanki
UTTAR PRADESH|Bareilly
UTTAR PRADESH|Basti
UTTAR PRADESH|Bhadohi
UTTAR PRADESH|Bijnor
UTTAR PRADESH|Budaun
UTTAR PRADESH|Bulandshahr
UTTAR PRADESH|Chandauli
UTTAR PRADESH|Chitrakoot
UTTAR PRADESH|Deoria
UTTAR PRADESH|Etah
UTTAR PRADESH|Etawah
UTTAR PRADESH|Faizabad
UTTAR PRADESH|Farrukhabad
UTTAR PRADESH|Fatehpur
UTTAR PRADESH|Firozabad
UTTAR PRADESH|Gautam Buddha Nagar
UTTAR PRADESH|Ghaziabad
UTTAR PRADESH|Ghazipur
UTTAR PRADESH|Gonda
UTTAR PRADESH|Gorakhpur
UTTAR PRADESH|Hamirpur
UTTAR PRADESH|Hapur (Panchsheel Nagar)
UTTAR PRADESH|Hardoi
UTTAR PRADESH|Hathras
UTTAR PRADESH|Jalaun
UTTAR PRADESH|Jaunpur
UTTAR PRADESH|Jhansi
UTTAR PRADESH|Kannauj
UTTAR PRADESH|Kanpur Dehat
UTTAR PRADESH|Kanpur Nagar
UTTAR PRADESH|Kanshiram Nagar (Kasganj)
UTTAR PRADESH|Kaushambi
UTTAR PRADESH|Kushinagar (Padrauna)
UTTAR PRADESH|Lakhimpur - Kheri
UTTAR PRADESH|Lalitpur
UTTAR PRADESH|Lucknow
UTTAR PRADESH|Maharajganj
UTTAR PRADESH|Mahoba
UTTAR PRADESH|Mainpuri
UTTAR PRADESH|Mathura
UTTAR PRADESH|Mau
UTTAR PRADESH|Meerut
UTTAR PRADESH|Mirzapur
UTTAR PRADESH|Moradabad
UTTAR PRADESH|Muzaffarnagar
UTTAR PRADESH|Pilibhit
UTTAR PRADESH|Pratapgarh
UTTAR PRADESH|RaeBareli
UTTAR PRADESH|Rampur
UTTAR PRADESH|Saharanpur
UTTAR PRADESH|Sambhal (Bhim Nagar)
UTTAR PRADESH|Sant Kabir Nagar
UTTAR PRADESH|Shahjahanpur
UTTAR PRADESH|Shamali (Prabuddh Nagar)
UTTAR PRADESH|Shravasti
UTTAR PRADESH|Siddharth Nagar
UTTAR PRADESH|Sitapur
UTTAR PRADESH|Sonbhadra
UTTAR PRADESH|Sultanpur
UTTAR PRADESH|Unnao
UTTAR PRADESH|Varanasi
UTTARAKHAND|Almora
UTTARAKHAND|Bageshwar
UTTARAKHAND|Chamoli
UTTARAKHAND|Champawat
UTTARAKHAND|Dehradun
UTTARAKHAND|Haridwar
UTTARAKHAND|Nainital
UTTARAKHAND|Pauri Garhwal
UTTARAKHAND|Pithoragarh
UTTARAKHAND|Rudraprayag
UTTARAKHAND|Tehri Garhwal
UTTARAKHAND|Udham Singh Nagar
UTTARAKHAND|Uttarkashi
WEST BENGAL|Alipurduar
WEST BENGAL|Bankura
WEST BENGAL|Birbhum
WEST BENGAL|Burdwan (Bardhaman)
WEST BENGAL|Cooch Behar
WEST BENGAL|Dakshin Dinajpur (South Dinajpur)
WEST BENGAL|Darjeeling
WEST BENGAL|Hooghly
WEST BENGAL|Howrah
WEST BENGAL|Jalpaiguri
WEST BENGAL|Kalimpong
WEST BENGAL|Kolkata
WEST BENGAL|Malda
WEST BENGAL|Murshidabad
WEST BENGAL|Nadia
WEST BENGAL|North 24 Parganas
WEST BENGAL|Paschim Medinipur (West Medinipur)
WEST BENGAL|Purba Medinipur (East Medinipur)
WEST BENGAL|Purulia
WEST BENGAL|South 24 Parganas
WEST BENGAL|Uttar Dinajpur (North Dinajpur)
""".strip()

def normalize_place_name(value):
    return " ".join(str(value).strip().upper().split())

def normalize_district_lookup_name(value):
    cleaned_value = normalize_place_name(value)
    cleaned_value = cleaned_value.split("(", 1)[0].strip()
    cleaned_value = "".join(char if char.isalnum() or char.isspace() else " " for char in cleaned_value)
    return " ".join(cleaned_value.split())

def build_state_district_master():
    state_district_map = {}
    state_name_map = {}
    district_lookup_map = {}
    for line in STATE_DISTRICT_MASTER_RAW.splitlines():
        state, district = [part.strip() for part in line.split("|", 1)]
        state_key = normalize_place_name(state)
        district_key = normalize_place_name(district)
        district_name = " ".join(district.split())
        state_district_map.setdefault(state_key, {})
        state_district_map[state_key][district_key] = district_name
        state_name_map[state_key] = " ".join(state.split())
        district_lookup_map.setdefault(state_key, {})
        district_lookup_key = normalize_district_lookup_name(district)
        district_lookup_map[state_key][district_lookup_key] = district_name
    return state_district_map, state_name_map, district_lookup_map

STATE_DISTRICT_MASTER, STATE_NAME_MASTER, DISTRICT_LOOKUP_MASTER = build_state_district_master()

def get_state_suggestion(state_name):
    matches = difflib.get_close_matches(
        normalize_place_name(state_name),
        list(STATE_NAME_MASTER.keys()),
        n=1,
        cutoff=0.6
    )
    if not matches:
        return ""
    return STATE_NAME_MASTER[matches[0]]

def get_district_suggestion(state_key, district_name):
    districts = STATE_DISTRICT_MASTER.get(state_key, {})
    district_lookup = DISTRICT_LOOKUP_MASTER.get(state_key, {})
    district_lookup_key = normalize_district_lookup_name(district_name)

    if district_lookup_key in district_lookup:
        return district_lookup[district_lookup_key]

    matches = difflib.get_close_matches(
        normalize_place_name(district_name),
        list(districts.keys()),
        n=1,
        cutoff=0.6
    )
    if matches:
        return districts[matches[0]]

    lookup_matches = difflib.get_close_matches(
        district_lookup_key,
        list(district_lookup.keys()),
        n=1,
        cutoff=0.6
    )
    if not lookup_matches:
        return ""
    return district_lookup[lookup_matches[0]]

def get_district_match_details(state_key, district_name):
    districts = STATE_DISTRICT_MASTER.get(state_key, {})
    district_lookup = DISTRICT_LOOKUP_MASTER.get(state_key, {})
    full_district_key = normalize_place_name(district_name)
    lookup_district_key = normalize_district_lookup_name(district_name)

    if full_district_key in districts:
        return True, districts[full_district_key], False

    if lookup_district_key in district_lookup:
        return False, district_lookup[lookup_district_key], True

    full_matches = difflib.get_close_matches(
        full_district_key,
        list(districts.keys()),
        n=1,
        cutoff=0.5
    )
    if full_matches:
        return False, districts[full_matches[0]], True

    lookup_matches = difflib.get_close_matches(
        lookup_district_key,
        list(district_lookup.keys()),
        n=1,
        cutoff=0.5
    )
    if lookup_matches:
        return False, district_lookup[lookup_matches[0]], True

    return False, "", False

def get_state_and_district_suggestion(state_name, district_name):
    suggested_state = get_state_suggestion(state_name)
    suggested_district = ""
    if suggested_state:
        suggested_state_key = normalize_place_name(suggested_state)
        suggested_district = get_district_suggestion(suggested_state_key, district_name)
    return suggested_state, suggested_district

def get_state_validation_message(state_name, suggested_state):
    if suggested_state:
        return "State spelling mismatch. Use Suggested State."
    return "State name not found in master list."

def get_district_validation_message(state_name, district_name, suggested_district):
    if suggested_district:
        entered_district = normalize_place_name(district_name)
        suggested_district_key = normalize_place_name(suggested_district)
        if entered_district != suggested_district_key:
            return "District spelling mismatch. Use Suggested District."
    return "District does not belong to the selected state."

def build_name_of_entity_value(row):
    registration_type = normalize_place_name(row.get('Registration Type', ''))
    application_number = " ".join(str(row.get('Application Number', '')).strip().split())
    entity_name = " ".join(str(row.get('Entity Name', '')).strip().split())
    entity_type = " ".join(str(row.get('Entity Type', '')).strip().split())
    existing_name = " ".join(str(row.get('Name of the Entity', '')).strip().split())

    if registration_type == 'REGISTERED':
        if application_number and entity_name:
            return f"{application_number} - {entity_name}"
        if entity_name:
            return entity_name
        return existing_name

    if entity_name:
        return entity_name
    return existing_name

def prepare_name_of_entity_column(df):
    prepared_df = df.copy()
    prepared_df['Name of the Entity'] = prepared_df.apply(build_name_of_entity_value, axis=1)
    return prepared_df

def validate_state_district_data(df, source_file_path=None):
    if 'State' not in df.columns or 'District' not in df.columns:
        if 'update_status' in globals():
            update_status("Validation failed: 'State' or 'District' column is missing.", "error")
        messagebox.showerror("Validation Error", "Uploaded file must contain 'State' and 'District' columns.")
        return False, df

    prepared_df = prepare_name_of_entity_column(df)
    validation_errors = []
    validation_audit = []

    for index, row in prepared_df.iterrows():
        state_name = " ".join(str(row.get('State', '')).strip().split())
        district_name = " ".join(str(row.get('District', '')).strip().split())
        audit_row = {
            'Excel Row': index + 2,
            'State': state_name,
            'District': district_name,
            'Name of the Entity': " ".join(str(row.get('Name of the Entity', '')).strip().split()),
            'Suggested State': "",
            'Suggested District': "",
            'Validation Result': ""
        }

        if not state_name and not district_name:
            audit_row['Validation Result'] = "Skipped: State and District both blank."
            validation_audit.append(audit_row)
            continue

        if not state_name or not district_name:
            suggested_state, suggested_district = get_state_and_district_suggestion(state_name, district_name)
            audit_row['Suggested State'] = suggested_state
            audit_row['Suggested District'] = suggested_district
            audit_row['Validation Result'] = "Error: State or District is blank."
            validation_audit.append(audit_row)
            validation_errors.append({
                'Excel Row': index + 2,
                'State': state_name,
                'District': district_name,
                'Suggested State': suggested_state,
                'Suggested District': suggested_district,
                'Validation Error': "State or District is blank."
            })
            continue

        state_key = normalize_place_name(state_name)
        district_key = normalize_place_name(district_name)

        if state_key not in STATE_DISTRICT_MASTER:
            suggested_state, suggested_district = get_state_and_district_suggestion(state_name, district_name)
            validation_message = get_state_validation_message(state_name, suggested_state)
            audit_row['Suggested State'] = suggested_state
            audit_row['Suggested District'] = suggested_district
            audit_row['Validation Result'] = f"Error: {validation_message}"
            validation_audit.append(audit_row)
            validation_errors.append({
                'Excel Row': index + 2,
                'State': state_name,
                'District': district_name,
                'Suggested State': suggested_state,
                'Suggested District': suggested_district,
                'Validation Error': validation_message
            })
            continue

        is_exact_district_match, suggested_district, is_spelling_match = get_district_match_details(state_key, district_name)
        if not is_exact_district_match:
            validation_message = (
                "District spelling mismatch. Use Suggested District."
                if is_spelling_match and suggested_district
                else "District does not belong to the selected state."
            )
            audit_row['Suggested State'] = STATE_NAME_MASTER[state_key]
            audit_row['Suggested District'] = suggested_district
            audit_row['Validation Result'] = f"Error: {validation_message}"
            validation_audit.append(audit_row)
            validation_errors.append({
                'Excel Row': index + 2,
                'State': state_name,
                'District': district_name,
                'Suggested State': STATE_NAME_MASTER[state_key],
                'Suggested District': suggested_district,
                'Validation Error': validation_message
            })
            continue

        audit_row['Suggested State'] = STATE_NAME_MASTER[state_key]
        audit_row['Suggested District'] = STATE_DISTRICT_MASTER[state_key][district_key]
        audit_row['Validation Result'] = "Valid"
        validation_audit.append(audit_row)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    save_folder = str(Path(source_file_path).resolve().parent) if source_file_path else os.path.expanduser("~/Desktop")
    prepared_file_path = ""
    if source_file_path:
        source_path = Path(source_file_path).resolve()
        prepared_file_path = str(source_path.parent / f"{source_path.stem}_prepared_{timestamp}.xlsx")
        prepared_df.to_excel(prepared_file_path, index=False, engine='openpyxl')

    if validation_errors:
        validation_df = pd.DataFrame(validation_errors)
        validation_audit_df = pd.DataFrame(validation_audit)
        validation_file_path = os.path.join(save_folder, f"district_validation_errors_{timestamp}.xlsx")
        with pd.ExcelWriter(validation_file_path, engine='openpyxl') as writer:
            validation_df.to_excel(writer, sheet_name='Errors', index=False)
            validation_audit_df.to_excel(writer, sheet_name='Audit', index=False)
            prepared_df.to_excel(writer, sheet_name='Prepared Data', index=False)
        print(f"District validation failed. Report saved: {validation_file_path}")
        if 'update_status' in globals():
            update_status("Validation failed. Prepared file and correction report saved in the same folder.", "error")
        messagebox.showerror(
            "District Validation Failed",
            f"Some rows have invalid State/District values.\nPrepared upload file saved at:\n{prepared_file_path}\n\nValidation report saved at:\n{validation_file_path}"
        )
        return False, prepared_df

    if 'update_status' in globals():
        update_status("State and district validation completed successfully.", "success")
    if prepared_file_path:
        if 'update_status' in globals():
            update_status("Validation completed and prepared file saved in the same folder.", "success")
        messagebox.showinfo(
            "Validation Successful",
            f"State and district details are valid.\nPrepared file saved at:\n{prepared_file_path}"
        )
    return True, prepared_df



def login():
    global invoicee
    global roww
    global driver
    today = date.today()
    driver = webdriver.Edge()
    driver.maximize_window()
    driver.implicitly_wait(15)
    driver.get('https://eprplastic.cpcb.gov.in/#/plastic/home')
    time.sleep(1)

    pwp_button_locator = (By.XPATH, '/html/body/app-root/app-plastic/div/app-home-new/div/div/div[3]/div/div/div[1]/h6/label[2]/input')
    custom_wait_clickable_and_click(driver, pwp_button_locator)

    mail = easygui.enterbox("Enter Email ")
    passs = easygui.enterbox("Enter Password")
    action = ActionChains(driver)
    action.click(on_element = driver.find_element(by=By.XPATH, value='//*[@id="user_name"]')).perform()
    action.click(on_element = driver.find_element(by=By.XPATH, value='//*[@id="password_pass"]')).perform()
    driver.find_element(by=By.XPATH, value='//*[@id="user_name"]').send_keys(mail)
    driver.find_element(by=By.XPATH, value='//*[@id="password_pass"]').send_keys(passs)


    errors = []
    invoicee = []
    roww=[]
    c=-1

    print(driver.get_cookies())

def data_upload():
    root = tk.Tk()
    file = fd.askopenfilename(parent=root, title='Choose a record file')
    root.destroy()
    if not file:
        if 'update_status' in globals():
            update_status("Data upload cancelled. No file selected.", "info")
        return
    if 'selected_file_var' in globals():
        selected_file_var.set(f"Selected File: {Path(file).name}")
    df = pd.read_excel(file, keep_default_na=False, converters={'Bank Account No': str,'HSN Code': str,'E-Invoice Number': str,'IFSC Code':str})
    df['Quantity In MT'] = df['Quantity In MT'].astype('float64')
    df['Sales date']=df['Sales date'].astype(str)
    df['Principal Amount'] = df['Principal Amount'].astype('float64')
    df['GST Amount'] = df['GST Amount'].astype('float64')
    is_valid, df = validate_state_district_data(df, file)
    if not is_valid:
        return

    global errors
    global invoicee
    global driver
    errors = []
    invoicee = []

    ssa = easygui.enterbox('What do you want to Uplaod? Select one option -\na) Export Data Entry\nb) Normal Data Entry')
    if not ssa:
        if 'update_status' in globals():
            update_status("Data upload cancelled. No option selected.", "info")
        return

    if ssa.lower() == 'a':
        upload_button_text = "Add New Export "
        output_prefix = "export_output_file"
    elif ssa.lower() == 'b':
        upload_button_text = "Add New "
        output_prefix = "Normla_output_file"
    else:
        messagebox.showerror("Invalid Selection", "Please enter only a or b.")
        if 'update_status' in globals():
            update_status("Data upload cancelled. Invalid upload option.", "error")
        return

    for i, row in df.iterrows():
        driver.refresh()
        driver.get('https://eprplastic.cpcb.gov.in/#/epr/details/sales')
        time.sleep(1)

        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//button[text()="{upload_button_text}"]'))
            ).click()
        except Exception:
            errors.append('Add New button not clickable')
            invoicee.append(str(df['E-Invoice Number'][i]))
            continue

        excel_category = row['Category of Plastic']
        excel_process = row['Process Code']
        excel_plastic = row['Plastic Type']
        excel_product = row['Product']
        excel_quantity = float(row['Quantity In MT'])

        table_rows = driver.find_elements(By.XPATH, '//tbody[@id="ScrollableSimpleTableBody"]/tr')
        for table_row in table_rows:
            category = table_row.find_element(By.XPATH, './td[3]/span').get_attribute('title')
            process = table_row.find_element(By.XPATH, './td[4]/span').get_attribute('title')
            plastic = table_row.find_element(By.XPATH, './td[5]/span').get_attribute('title')
            product = table_row.find_element(By.XPATH, './td[6]/span').get_attribute('title')
            quantity = float(table_row.find_element(By.XPATH, './td[8]/span').get_attribute('title'))
            print(excel_category, ">>", category)
            print(excel_process, ">>", process)
            print(excel_plastic, ">>", plastic)
            print(excel_product, ">>", product)
            print(excel_quantity, ">>", quantity)

            if (
                category.strip().lower() == excel_category.strip().lower()
                and process.strip().lower() == excel_process.strip().lower()
                and plastic.strip().lower() == excel_plastic.strip().lower()
                and product.strip().lower() == excel_product.strip().lower()
                and quantity >= excel_quantity
            ):
                checkbox = table_row.find_element(By.XPATH, './td[2]/input[@type="checkbox"]')
                checkbox.click()
                time.sleep(1)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@name="qty_product_sold"]'))
                ).send_keys(df['Quantity In MT'][i])

                time.sleep(2)
                scroll_element = driver.find_element(by=By.XPATH, value='//button[contains(text(),"Generate EPR Invoice Number")]')
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'})",
                    scroll_element
                )
                time.sleep(2)

                if ssa.lower() == 'b':
                    try:
                        driver.find_element(by=By.XPATH, value='//*[@placeholder="Select Registration Type"]//input').send_keys(df['Registration Type'][i])
                        WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                        ).click()
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(2)

                if str(df['Registration Type'][i]).lower() == 'registered':
                    if ssa.lower() == 'b':
                        try:
                            driver.find_element(by=By.XPATH, value='//*[@placeholder="Select Entity Type"]//input').send_keys(df['Entity Type'][i])
                            WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                            ).click()
                        except Exception:
                            errors.append('registeration error')
                            invoicee.append(str(df['E-Invoice Number'][i]))
                        time.sleep(5)

                        try:
                            driver.find_element(by=By.XPATH, value='//*[@placeholder="Select Entity Name"]//input').send_keys(df['Name of the Entity'][i])
                            WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                            ).click()
                        except Exception:
                            errors.append('registeration error')
                            invoicee.append(str(df['E-Invoice Number'][i]))
                        time.sleep(2)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter GST number"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter GST number"]').send_keys(df['GST No. of Seller'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    if ssa.lower() == 'b':
                        try:
                            driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter Buyer GST number"]').clear()
                            driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter Buyer GST number"]').send_keys(df['Buyer GST'][i])
                        except Exception:
                            errors.append('registeration error')
                            invoicee.append(str(df['E-Invoice Number'][i]))
                        time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter HSN code"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter HSN code"]').send_keys(df['HSN Code'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter E-invoice number"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter E-invoice number"]').send_keys(df['E-Invoice Number'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter account number"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter account number"]').send_keys(df['Bank Account No'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="ifsc_code"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="ifsc_code"]').send_keys(df['IFSC Code'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="amount"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="amount"]').send_keys(df['Principal Amount'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="gst_amount"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="gst_amount"]').send_keys(df['GST Amount'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        a = str(df['Sales date'][i])[:8]
                        d = f"{a[:4]}-{a[4:6]}-{a[6:]}"
                        date_input = driver.find_element(By.XPATH, '//input[@name="salesDate"]')
                        driver.execute_script("""
                            arguments[0].value = arguments[1];
                            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        """, date_input, d)
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(2)

                else:
                    try:
                        driver.find_element(by=By.XPATH, value='//*[@placeholder="Entity Name"]').clear()
                        driver.find_element(by=By.XPATH, value='//*[@placeholder="Entity Name"]').send_keys(df['Name of the Entity'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="address"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="address"]').send_keys(df['Address'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    if ssa.lower() == 'b':
                        try:
                            driver.find_element(by=By.XPATH, value='//*[@name="entity_state_id"]//input').send_keys(df['State'][i])
                            WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                            ).click()
                        except Exception:
                            errors.append('registeration error')
                            invoicee.append(str(df['E-Invoice Number'][i]))
                        time.sleep(2)

                        try:
                            driver.find_element(by=By.XPATH, value='//*[@name="entity_district"]//input').send_keys((df['District'][i]).lower().strip())
                            WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                            ).click()
                        except Exception:
                            errors.append('registeration error')
                            invoicee.append(str(df['E-Invoice Number'][i]))
                        time.sleep(2)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter GST number"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter GST number"]').send_keys(df['GST No. of Seller'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    if ssa.lower() == 'b':
                        try:
                            driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter Buyer GST number"]').clear()
                            driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter Buyer GST number"]').send_keys(df['Buyer GST'][i])
                        except Exception:
                            errors.append('registeration error')
                            invoicee.append(str(df['E-Invoice Number'][i]))
                        time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter HSN code"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter HSN code"]').send_keys(df['HSN Code'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter E-invoice number"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter E-invoice number"]').send_keys(df['E-Invoice Number'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter account number"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter account number"]').send_keys(df['Bank Account No'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="ifsc_code"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="ifsc_code"]').send_keys(df['IFSC Code'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="amount"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="amount"]').send_keys(df['Principal Amount'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        driver.find_element(by=By.XPATH, value='//input[@name="gst_amount"]').clear()
                        driver.find_element(by=By.XPATH, value='//input[@name="gst_amount"]').send_keys(df['GST Amount'][i])
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(1)

                    try:
                        a = str(df['Sales date'][i])[:8]
                        d = f"{a[:4]}-{a[4:6]}-{a[6:]}"
                        date_input = driver.find_element(By.XPATH, '//input[@name="salesDate"]')
                        driver.execute_script("""
                            arguments[0].value = arguments[1];
                            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        """, date_input, d)
                    except Exception:
                        errors.append('registeration error')
                        invoicee.append(str(df['E-Invoice Number'][i]))
                    time.sleep(2)

                try:
                    WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"Generate EPR Invoice Number")]'))
                    ).click()
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"Confirm")]'))
                    ).click()
                    copy_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//input[@name="invoice_number"]/following-sibling::button'))
                    )
                    copy_button.click()
                    time.sleep(3)

                    epr_invoice_input = driver.find_element(By.XPATH, '//input[@name="invoice_number"]')
                    epr_invoice_number = epr_invoice_input.get_attribute('value')
                    df.at[i, 'EPR Invoice Number'] = epr_invoice_number
                    print(f"Selected: {category}, Quantity: {quantity}")
                except Exception:
                    df.at[i, 'EPR Invoice Number'] = ""
                break

    now = datetime.datetime.now()
    output_file = f'{output_prefix}_{now.strftime("%d%m%Y_%H%M%S")}.xlsx'
    df.to_excel(output_file, index=False)
    print(f"File saved: {output_file}")

def invoice_upload():
    root = tk.Tk()
    file = fd.askopenfilename(parent=root, title='Choose a record file')
    file2 = fd.askopenfilenames(parent=root, title='Choose a pdf files')
    root.destroy()
    if not file:
        if 'update_status' in globals():
            update_status("Invoice upload cancelled. No Excel file selected.", "info")
        return
    if 'selected_file_var' in globals():
        selected_file_var.set(f"Selected File: {Path(file).name}")
    df1 = pd.DataFrame(list(file2), columns =['file_path'])
    df1['file_name'] = 0
    for i in range(len(df1)):
        file_path = df1.loc[i, 'file_path']
        file_name = Path(file_path).stem
        df1.loc[i, 'file_name'] = file_name
    df = pd.read_excel(file, keep_default_na=False, converters={'pdf_filename': str,'Invoice No':str})
    df['pdf_filename']=df['pdf_filename'].astype(str)
    df['Invoice No']=df['Invoice No'].astype(str)

    global errors
    global invoicee
    global driver
    errors = []
    invoicee = []
    for i, row in df.iterrows():
        driver.refresh()
        try:
            driver.find_element(by=By.XPATH, value='//*[@placeholder="Search"]').clear()
            driver.find_element(by=By.XPATH, value='//*[@placeholder="Search"]').send_keys(df['Invoice No'][i])
        
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Search"]'))).click()
        
            matching_row = df1[df1['file_name'] == row['pdf_filename']]
            if matching_row.empty:
                raise ValueError(f"No matching PDF found for pdf_filename: {row['pdf_filename']}")
        
            file_path_for_upload = matching_row.iloc[0]['file_path']
            time.sleep(2)
            invoice_no = df['Invoice No'][i]
            element = driver.find_element(By.XPATH, f'//tbody[@id="ScrollableSimpleTableBody"]/tr[td[7][normalize-space()="{invoice_no}"]]/td[15]/span')
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            element.click()
            upload_file = driver.find_element(by=By.XPATH, value='//*[@name="invoice"]')
            upload_file.send_keys(file_path_for_upload)
            time.sleep(2)
            # upload = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Upload" and not (@type)]')))
            # custom_wait_clickable_and_click(upload)
            # WebDriverWait(driver, 20).until_not(EC.presence_of_element_located((By.XPATH, '//button[text()="Upload" and not (@type)]')))
        
            # time.sleep(5)
            upload = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[text()="Upload" and not (@type)]'))
            ).click()
            # custom_wait_clickable_and_click(upload)
            
            # try:
            WebDriverWait(driver, 30).until(EC.invisibility_of_element_located((By.XPATH, '//button[text()="Upload" and not (@type)]')))
            # except:
            #     print("Upload button is still visible. Proceeding anyway.")
            
            time.sleep(5)
        
        
            # Add logic for post-upload actions, if required
            print(f"Uploaded file for Invoice No: {row['Invoice No']}, Filename: {row['pdf_filename']}")
        except:
            errors.append('Invoice upload error')
            invoicee.append(str(df['Invoice No'][i]))
            
    if errors:
        error_df = pd.DataFrame({
            'Invoice No': invoicee,
            'Error': errors
        })

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        save_folder = os.path.expanduser("~/Desktop")  # or any path you prefer
        error_file_path = os.path.join(save_folder, f"invoice_upload_errors_{timestamp}.xlsx")

        error_df.to_excel(error_file_path, index=False, engine='openpyxl')
        print(f"\n❌ Error report saved: {error_file_path}")
    else:
        print("\n✅ All invoices uploaded successfully.")

        # break

def download_excel_format():
    columns = [
        "Category of Plastic",
        "Process Code",
        "Plastic Type",
        "Product",
        "Quantity In MT",
        "Registration Type",
        "Entity Type",
        "Application Number",
        "Entity Name",
        "Name of the Entity",
        "Dropdown Number",
        "Address",
        "State",
        "District",
        "GST No. of Seller",
        "Buyer GST",
        "HSN Code",
        "E-Invoice Number",
        "Bank Account No",
        "IFSC Code",
        "% of Recycled Plastic",
        "Principal Amount",
        "GST Amount",
        "Sales date"
    ]
    df = pd.DataFrame(columns=columns)
    root = tk.Tk()
    file_path = fd.asksaveasfilename(
        parent=root,
        title="Save Data Upload Excel Format",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")]
    )
    root.destroy()
    if not file_path:
        return
    df.to_excel(file_path, index=False)
    print(f"Template file saved: {file_path}")

def download_invoice_excel_format():
    columns = [
        "Invoice No",
        "pdf_filename"
    ]
    df = pd.DataFrame(columns=columns)
    root = tk.Tk()
    file_path = fd.asksaveasfilename(
        parent=root,
        title="Save Invoice Upload Excel Format",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")]
    )
    root.destroy()
    if not file_path:
        return
    df.to_excel(file_path, index=False)
    print(f"Invoice upload template file saved: {file_path}")

def download_delete_excel_format():
    columns = [
        "Invoice No"
    ]
    df = pd.DataFrame(columns=columns)
    root = tk.Tk()
    file_path = fd.asksaveasfilename(
        parent=root,
        title="Save Delete Entry Excel Format",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")]
    )
    root.destroy()
    if not file_path:
        return
    df.to_excel(file_path, index=False)
    print(f"Delete entry template file saved: {file_path}")

def delete_upload_data():
    root = tk.Tk()
    file = fd.askopenfilename(parent=root, title='Choose Records Deletion File')
    root.destroy()
    if not file:
        if 'update_status' in globals():
            update_status("Delete upload data cancelled. No file selected.", "info")
        return
    if 'selected_file_var' in globals():
        selected_file_var.set(f"Selected File: {Path(file).name}")
    df = pd.read_excel(file, converters={'Invoice No': str})

    global errors
    global invoicee
    global driver
    errors = []
    invoicee = []

    for _, row in df.iterrows():
        invoice_no = row['Invoice No']
        driver.refresh()
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@placeholder="Search"]'))
            )
            search_input.clear()
            search_input.send_keys(invoice_no)

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Search"]'))
            ).click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table/tbody/tr"))
            )

            row_xpath = f'//table/tbody/tr[td[7][normalize-space()="{invoice_no}"]]'
            delete_xpath = row_xpath + '//em[contains(@class,"fa-trash")]'

            delete_icon = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, delete_xpath))
            )

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_icon)
            driver.execute_script("arguments[0].click();", delete_icon)

            confirm = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//div[contains(@class,"confirm_delete")]//button[normalize-space()="Delete"]')
                )
            )

            driver.execute_script("arguments[0].click();", confirm)

        except Exception as e:
            errors.append(str(e))
            invoicee.append(invoice_no)

def scrap_data():
    from lxml import html

    def scrape_table(driver, column_indexes, column_names, file_prefix, check_upload=False):
        data_lists = {name: [] for name in column_names}

        while True:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//tbody[@id="ScrollableSimpleTableBody"]/tr[1]')
                    )
                )

                target_element = driver.find_element(
                    By.XPATH,
                    '//tbody[@id="ScrollableSimpleTableBody"]/tr[1]'
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    target_element
                )

            except Exception:
                print("No rows found. Ending scraping.")
                break

            time.sleep(2)

            tree = html.fromstring(driver.page_source)
            rows = tree.xpath('//tbody[@id="ScrollableSimpleTableBody"]/tr')

            row_index = 1

            for row in rows:
                cells = row.xpath('./td')

                for col_name, col_index in zip(column_names, column_indexes):
                    if col_index < len(cells):
                        data_lists[col_name].append(cells[col_index].text_content())
                    else:
                        data_lists[col_name].append("")

                if check_upload:
                    try:
                        upload_class = tree.xpath(
                            f'//tbody[@id="ScrollableSimpleTableBody"]/tr[{row_index}]/td[15]/span/@class'
                        )
                        upload_class = upload_class[0] if upload_class else ''
                    except Exception:
                        upload_class = ''

                    if "color-red" in upload_class:
                        data_lists['Invoice File Status'].append("Pending")
                    else:
                        data_lists['Invoice File Status'].append("Uploaded")

                row_index += 1

            try:
                next_button = driver.find_element(
                    By.XPATH,
                    '//button[@ngbtooltip="Next"]'
                )

                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(next_button)
                ).click()

                time.sleep(5)

            except Exception:
                print("Next button not found. Finished scraping.")
                break

        df = pd.DataFrame(data_lists)

        now = datetime.datetime.now()
        filename = f"{file_prefix}_{now.strftime('%d%m%Y_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False)

        print(f"✅ File saved: {filename}")
        if 'update_status' in globals():
            update_status(f"Scraping completed. File saved: {filename}", "success")
        messagebox.showinfo("Scraping Completed", f"File saved successfully:\n{filename}")

    choice = easygui.enterbox(
        '''
Select which data to scrape:

a) Procurement Data Entry
b) Production Data Entry
c) Inventory & Sales Entry
'''
    )

    if not choice:
        if 'update_status' in globals():
            update_status("Scraping cancelled. No selection provided.", "info")
        return

    if choice.lower() == 'a':
        scrape_table(
            driver,
            column_indexes=[1, 2, 3, 4, 5, 6, 7, 8, 9],
            column_names=[
                'Name of Supplier',
                'Address of Supplier',
                'Categories of Plastic',
                'Qty. of Waste Plastic (Tons)',
                'GST No',
                'Aadhar No',
                'Mobile No',
                'Procurement Date',
                'Date of Entry'
            ],
            file_prefix="Procurement_scrap_file"
        )

    elif choice.lower() == 'b':
        scrape_table(
            driver,
            column_indexes=[1, 2, 3, 4, 5, 6, 7, 8],
            column_names=[
                'Category',
                'Process Code',
                'Plastic Type',
                'Product',
                'Qty. of Product(Tons)',
                'Qty. of Input Waste(Tons)',
                'Percentage of Recycled plastic in product',
                'Date of Production'
            ],
            file_prefix="Production_scrap_file"
        )

    elif choice.lower() == 'c':
        scrape_table(
            driver,
            column_indexes=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            column_names=[
                'Seller GST No',
                'Total Qty. of Product Sold (Tons)',
                'Amount(₹)',
                'Date of Sale',
                'Register Type',
                'Invoice No',
                'Name of the Entity',
                'Address',
                'District',
                'State',
                'Total Potential Generated',
                'Invoice file',
                'Invoice File Status'
            ],
            file_prefix="Inventory_sales_scrap_file",
            check_upload=True
        )

    else:
        print("❌ Invalid selection")
        if 'update_status' in globals():
            update_status("Invalid scraping selection.", "error")
        messagebox.showerror("Invalid Selection", "Please enter only a, b, or c.")

from tkinter import *
from PIL import ImageTk, Image
from tkinter import filedialog, messagebox

APP_BG = "#F0F9FF"
HEADER_BG = "#0F766E"
HEADER_TEXT = "#FFFFFF"
SUBTEXT_COLOR = "#CCFBF1"
CARD_BG = "#FFFFFF"
TEXT_COLOR = "#374151"
MUTED_TEXT = "#6B7280"
PRIMARY_BG = "#16A34A"
PRIMARY_ACTIVE_BG = "#15803D"
PRIMARY_TEXT = "#FFFFFF"
SECONDARY_BG = "#F3F4F6"
SECONDARY_ACTIVE_BG = "#E5E7EB"
SECONDARY_TEXT = "#1F2937"
WARNING_BG = "#DBEAFE"
WARNING_ACTIVE_BG = "#BFDBFE"
WARNING_TEXT = "#1D4ED8"
DANGER_BG = "#FEE2E2"
DANGER_ACTIVE_BG = "#FECACA"
DANGER_TEXT = "#B91C1C"
DISABLED_BG = "#E5E7EB"
DISABLED_TEXT = "#9CA3AF"
STATUS_BG = "#E0F2FE"

app_logged_in = False
action_buttons = []

def update_status(message, status_type="info"):
    if 'status_var' not in globals():
        return

    color_map = {
        "info": "#0F766E",
        "success": "#166534",
        "error": "#B91C1C"
    }
    status_var.set(message)
    status_label.config(fg=color_map.get(status_type, "#0F766E"))
    root.update_idletasks()

def update_login_status(is_logged_in):
    if 'login_status_var' not in globals():
        return

    if is_logged_in:
        login_status_var.set("Login Status: Connected")
        login_badge.config(bg="#DCFCE7", fg="#166534")
    else:
        login_status_var.set("Login Status: Not Connected")
        login_badge.config(bg="#FEE2E2", fg="#B91C1C")
    root.update_idletasks()

def update_license_status_display():
    if 'license_status_var' not in globals():
        return

    if _license_info.get("license_verified"):
        if _license_info.get("offline"):
            license_status_var.set("License: Valid (Offline Grace)")
            license_badge.config(bg="#FEF3C7", fg="#92400E")
        else:
            license_status_var.set("License: Valid")
            license_badge.config(bg="#DCFCE7", fg="#166534")
    else:
        license_status_var.set("License: Not Verified")
        license_badge.config(bg="#FEE2E2", fg="#B91C1C")
    root.update_idletasks()


def update_gst_status_display():
    if 'gst_status_var' not in globals():
        return

    portal_gst = _license_info.get("portal_gst")
    if _license_info.get("gst_verified") and portal_gst:
        gst_status_var.set(f"Portal GST: {portal_gst}")
        gst_badge.config(bg="#DCFCE7", fg="#166534")
    else:
        gst_status_var.set("Portal GST: Not Verified")
        gst_badge.config(bg="#FEE2E2", fg="#B91C1C")
    root.update_idletasks()


def update_license_footer():
    if 'license_footer_var' not in globals():
        return

    customer_name = _license_info.get("customer_name") or "Unknown customer"
    tier = _license_info.get("tier") or "No tier"
    expires_on = _license_info.get("expires_on") or "No expiry info"
    portal_gst = _license_info.get("portal_gst") or "GST pending"
    license_footer_var.set(
        f"Licensed to: {customer_name} | Tier: {tier} | Expires: {expires_on} | Portal GST: {portal_gst}"
    )
    root.update_idletasks()


def refresh_access_state():
    actions_enabled = bool(
        _license_info.get("license_verified")
        and app_logged_in
        and _license_info.get("gst_verified")
    )
    set_action_buttons_state(actions_enabled)
    update_license_status_display()
    update_gst_status_display()
    update_license_footer()


def set_action_buttons_state(enabled):
    state = NORMAL if enabled else DISABLED
    for button in action_buttons:
        button.config(state=state)
        if enabled:
            button.config(bg=button.default_bg, fg=button.default_fg)
        else:
            button.config(bg=DISABLED_BG, fg=DISABLED_TEXT)

def choose_validation_file():
    chooser = tk.Tk()
    chooser.withdraw()
    file_path = fd.askopenfilename(parent=chooser, title='Choose a record file')
    chooser.destroy()
    return file_path

def validate_excel_file():
    file_path = choose_validation_file()
    if not file_path:
        update_status("Validation cancelled. No file selected.", "info")
        return

    selected_file_var.set(f"Selected File: {Path(file_path).name}")
    update_status("Validating uploaded Excel file...", "info")
    try:
        df = pd.read_excel(file_path, keep_default_na=False)
        validate_state_district_data(df, file_path)
    except Exception as e:
        update_status("Unable to validate the selected file.", "error")
        messagebox.showerror("Validation Error", str(e))

def run_login():
    global app_logged_in
    update_status("Opening login flow...", "info")
    try:
        login()
        app_logged_in = 'driver' in globals() and driver is not None
        if not app_logged_in:
            update_status("Login window did not initialize successfully.", "error")
            refresh_access_state()
            return

        messagebox.showinfo(
            "Complete CPCB Login",
            "The browser has been opened and credentials were filled.\n\n"
            "Complete any captcha or final login step in the browser, wait until the portal page is fully loaded, "
            "and keep the GST-visible page open.\n\nThen click OK to verify the licensed GST."
        )

        ok, result_message = verify_portal_gst_against_license()
        if ok:
            update_login_status(True)
            update_status(
                f"Login completed and licensed GST verified: {result_message}. Actions are now enabled.",
                "success"
            )
        else:
            app_logged_in = False
            update_login_status(False)
            update_status("Login completed but GST verification failed.", "error")
            messagebox.showerror(
                "GST Verification Failed",
                result_message
            )
        refresh_access_state()
    except Exception as e:
        app_logged_in = False
        update_login_status(False)
        _license_info["gst_verified"] = False
        _license_info["portal_gst"] = ""
        refresh_access_state()
        update_status("Login failed.", "error")
        messagebox.showerror("Login Error", str(e))

def require_portal_access(action_name):
    if not _license_info.get("license_verified"):
        update_status("A valid license is required before using the app.", "error")
        messagebox.showwarning("License Required", "A valid license is required before using this app.")
        return False
    if app_logged_in and _license_info.get("gst_verified"):
        return True
    update_status(f"Please login and verify the licensed GST before using {action_name}.", "error")
    messagebox.showwarning(
        "Login Required",
        f"Please complete CPCB login and GST verification before using {action_name}."
    )
    return False

def run_data_upload():
    if not require_portal_access("Data Upload"):
        return
    update_status("Starting data upload. File validation will run first.", "info")
    try:
        data_upload()
        update_status("Data upload finished.", "success")
    except Exception as e:
        update_status("Data upload failed.", "error")
        messagebox.showerror("Data Upload Error", str(e))

def run_invoice_upload():
    if not require_portal_access("Invoice Upload"):
        return
    update_status("Starting invoice upload...", "info")
    try:
        invoice_upload()
        update_status("Invoice upload finished.", "success")
    except Exception as e:
        update_status("Invoice upload failed.", "error")
        messagebox.showerror("Invoice Upload Error", str(e))

def run_scrap_data():
    if not require_portal_access("Scrap Data"):
        return
    update_status("Starting data scraping...", "info")
    try:
        scrap_data()
        update_status("Data scraping finished.", "success")
    except Exception as e:
        update_status("Data scraping failed.", "error")
        messagebox.showerror("Scrap Data Error", str(e))

def run_delete_upload_data():
    if not require_portal_access("Delete Upload Data"):
        return
    if not messagebox.askyesno("Confirm Delete", "Do you want to continue with delete upload data?"):
        update_status("Delete action cancelled.", "info")
        return
    update_status("Starting delete upload data...", "info")
    try:
        delete_upload_data()
        update_status("Delete upload data finished.", "success")
    except Exception as e:
        update_status("Delete upload data failed.", "error")
        messagebox.showerror("Delete Upload Error", str(e))

root = Tk()
root.title(f"PWP Automation Dashboard v{APP_VERSION}")
root.configure(bg=APP_BG)
root.resizable(width=False, height=False)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = 860
window_height = 600
x_cordinate = int((screen_width / 2) - (window_width / 2))
y_cordinate = int((screen_height / 2) - (window_height / 2))
root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
root.withdraw()

status_var = StringVar(value="Ready. Validate your license, then login and verify GST.")
login_status_var = StringVar(value="Login Status: Not Connected")
license_status_var = StringVar(value="License: Not Verified")
gst_status_var = StringVar(value="Portal GST: Not Verified")
license_footer_var = StringVar(value="Licensed to: Unknown customer | Tier: No tier | Expires: No expiry info | Portal GST: GST pending")
selected_file_var = StringVar(value="Selected File: None")

menubar = Menu(root, bg=HEADER_BG, fg=HEADER_TEXT, tearoff=0)
root.config(menu=menubar)

file_menu = Menu(menubar, tearoff=0, bg=HEADER_BG, fg=HEADER_TEXT)
menubar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Exit", command=root.quit)

excel_menu = Menu(menubar, tearoff=0, bg=HEADER_BG, fg=HEADER_TEXT)
menubar.add_cascade(label="Excel Format", menu=excel_menu)
excel_menu.add_command(label="Download Data Upload Format", command=download_excel_format)
excel_menu.add_command(label="Download Invoice Upload Format", command=download_invoice_excel_format)
excel_menu.add_command(label="Download Delete Entry Format", command=download_delete_excel_format)

view_menu = Menu(menubar, tearoff=0, bg=HEADER_BG, fg=HEADER_TEXT)
menubar.add_cascade(label="Help", menu=view_menu)
view_menu.add_command(label="About", command=show_about_dialog)
view_menu.add_command(label="Check for Updates", command=lambda: check_for_updates(show_latest_message=True, auto_check=False))

header_frame = Frame(root, bg=HEADER_BG, padx=24, pady=18)
header_frame.pack(fill="x")

header_top = Frame(header_frame, bg=HEADER_BG)
header_top.pack(fill="x")

title_label = Label(
    header_top,
    text="PWP Automation Dashboard",
    bg=HEADER_BG,
    fg=HEADER_TEXT,
    font=("Verdana", 20, "bold")
)
title_label.pack(side="left")

badge_frame = Frame(header_top, bg=HEADER_BG)
badge_frame.pack(side="right")

gst_badge = Label(
    badge_frame,
    textvariable=gst_status_var,
    bg="#FEE2E2",
    fg="#B91C1C",
    font=("Verdana", 9, "bold"),
    padx=10,
    pady=6
)
gst_badge.pack(side="right", padx=(8, 0))

license_badge = Label(
    badge_frame,
    textvariable=license_status_var,
    bg="#FEE2E2",
    fg="#B91C1C",
    font=("Verdana", 9, "bold"),
    padx=10,
    pady=6
)
license_badge.pack(side="right", padx=(8, 0))

login_badge = Label(
    badge_frame,
    textvariable=login_status_var,
    bg="#FEE2E2",
    fg="#B91C1C",
    font=("Verdana", 9, "bold"),
    padx=10,
    pady=6
)
login_badge.pack(side="right")

subtitle_label = Label(
    header_frame,
    text="1. License validation  2. Login  3. GST verification  4. Validate and run actions",
    bg=HEADER_BG,
    fg=SUBTEXT_COLOR,
    font=("Verdana", 10)
)
subtitle_label.pack(anchor="w", pady=(10, 0))

content_frame = Frame(root, bg=APP_BG, padx=20, pady=18)
content_frame.pack(expand=True, fill="both")

top_info_frame = Frame(content_frame, bg=APP_BG)
top_info_frame.pack(fill="x", pady=(0, 14))

workflow_card = Frame(top_info_frame, bg=CARD_BG, padx=18, pady=16, highlightbackground="#A5F3FC", highlightthickness=1)
workflow_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

workflow_title = Label(
    workflow_card,
    text="Workflow",
    bg=CARD_BG,
    fg=TEXT_COLOR,
    font=("Verdana", 12, "bold")
)
workflow_title.pack(anchor="w")

workflow_text = Label(
    workflow_card,
    text="The app validates your license first. After CPCB login, the portal GST must match the licensed GST before actions unlock.",
    bg=CARD_BG,
    fg=MUTED_TEXT,
    justify="left",
    wraplength=360,
    font=("Verdana", 9)
)
workflow_text.pack(anchor="w", pady=(6, 0))

file_card = Frame(top_info_frame, bg=CARD_BG, padx=18, pady=16, highlightbackground="#A5F3FC", highlightthickness=1)
file_card.pack(side="left", fill="both", expand=True, padx=(8, 0))

file_title = Label(
    file_card,
    text="File Info",
    bg=CARD_BG,
    fg=TEXT_COLOR,
    font=("Verdana", 12, "bold")
)
file_title.pack(anchor="w")

file_text = Label(
    file_card,
    textvariable=selected_file_var,
    bg=CARD_BG,
    fg=MUTED_TEXT,
    justify="left",
    wraplength=320,
    font=("Verdana", 9)
)
file_text.pack(anchor="w", pady=(6, 0))

dashboard_frame = Frame(content_frame, bg=APP_BG)
dashboard_frame.pack(fill="both", expand=True)

dashboard_frame.grid_columnconfigure(0, weight=2)
dashboard_frame.grid_columnconfigure(1, weight=1)

left_panel = Frame(dashboard_frame, bg=CARD_BG, padx=18, pady=18, highlightbackground="#A5F3FC", highlightthickness=1)
left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

right_panel = Frame(dashboard_frame, bg=CARD_BG, padx=18, pady=18, highlightbackground="#A5F3FC", highlightthickness=1)
right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

left_title = Label(left_panel, text="Main Actions", bg=CARD_BG, fg=TEXT_COLOR, font=("Verdana", 12, "bold"))
left_title.pack(anchor="w")

left_subtitle = Label(left_panel, text="Primary workflow for licensed login, validation and upload.", bg=CARD_BG, fg=MUTED_TEXT, font=("Verdana", 9))
left_subtitle.pack(anchor="w", pady=(4, 14))

right_title = Label(right_panel, text="Utilities", bg=CARD_BG, fg=TEXT_COLOR, font=("Verdana", 12, "bold"))
right_title.pack(anchor="w")

right_subtitle = Label(
    right_panel,
    text="Support actions for cleanup and reporting.",
    bg=CARD_BG,
    fg=MUTED_TEXT,
    font=("Verdana", 9),
    justify="left",
    wraplength=220
)
right_subtitle.pack(anchor="w", pady=(4, 14))

button_width = 18
button_height = 2

def create_action_button(parent, text, command, bg, active_bg, fg, row, column):
    button = Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=fg,
        font=("Verdana", 11, "bold"),
        width=button_width,
        height=button_height,
        wraplength=190,
        bd=0,
        highlightthickness=0,
        cursor="hand2"
    )
    button.default_bg = bg
    button.default_fg = fg
    button.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
    return button

left_buttons = Frame(left_panel, bg=CARD_BG)
left_buttons.pack(fill="both", expand=True)
left_buttons.grid_columnconfigure(0, weight=1)
left_buttons.grid_columnconfigure(1, weight=1)

right_buttons = Frame(right_panel, bg=CARD_BG)
right_buttons.pack(fill="both", expand=True)
right_buttons.grid_columnconfigure(0, weight=1)

btn_login = create_action_button(left_buttons, "Login", run_login, PRIMARY_BG, PRIMARY_ACTIVE_BG, PRIMARY_TEXT, 0, 0)
btn_validate = create_action_button(left_buttons, "Validate Excel", validate_excel_file, WARNING_BG, WARNING_ACTIVE_BG, WARNING_TEXT, 0, 1)
btn_data = create_action_button(left_buttons, "Data Upload", run_data_upload, SECONDARY_BG, SECONDARY_ACTIVE_BG, SECONDARY_TEXT, 1, 0)
btn_invoice = create_action_button(left_buttons, "Invoice Upload", run_invoice_upload, SECONDARY_BG, SECONDARY_ACTIVE_BG, SECONDARY_TEXT, 1, 1)

btn_delete = create_action_button(right_buttons, "Delete Upload Data", run_delete_upload_data, DANGER_BG, DANGER_ACTIVE_BG, DANGER_TEXT, 0, 0)
btn_scrape = create_action_button(right_buttons, "Scrap Data", run_scrap_data, SECONDARY_BG, SECONDARY_ACTIVE_BG, SECONDARY_TEXT, 1, 0)

guide_title = Label(right_panel, text="Quick Guide", bg=CARD_BG, fg=TEXT_COLOR, font=("Verdana", 11, "bold"))
guide_title.pack(anchor="w", pady=(14, 6))

guide_text = Label(
    right_panel,
    text="License validation is required at startup.\nLogin unlocks GST verification.\nProtected actions stay disabled until the portal GST matches the license.",
    bg=CARD_BG,
    fg=MUTED_TEXT,
    justify="left",
    wraplength=220,
    font=("Verdana", 9)
)
guide_text.pack(anchor="w")

license_footer_label = Label(
    right_panel,
    textvariable=license_footer_var,
    bg=CARD_BG,
    fg=MUTED_TEXT,
    justify="left",
    wraplength=220,
    font=("Verdana", 8)
)
license_footer_label.pack(anchor="w", pady=(12, 0))

status_frame = Frame(root, bg=STATUS_BG, padx=20, pady=12)
status_frame.pack(fill="x", side="bottom")

status_title = Label(
    status_frame,
    text="Process Status",
    bg=STATUS_BG,
    fg=TEXT_COLOR,
    font=("Verdana", 10, "bold")
)
status_title.pack(anchor="w")

status_label = Label(
    status_frame,
    textvariable=status_var,
    bg=STATUS_BG,
    fg="#0F766E",
    anchor="w",
    justify="left",
    font=("Verdana", 9)
)
status_label.pack(fill="x", pady=(4, 0))

action_buttons = [btn_validate, btn_data, btn_invoice, btn_delete, btn_scrape]
set_action_buttons_state(False)
update_login_status(False)
update_license_status_display()
update_gst_status_display()
update_license_footer()

if not run_startup_license_gate():
    root.destroy()
    sys.exit(0)

refresh_access_state()
update_status("License validated. Complete CPCB login and GST verification to unlock actions.", "info")
root.deiconify()
root.after(1500, lambda: check_for_updates(show_latest_message=False, auto_check=True))

root.mainloop()




