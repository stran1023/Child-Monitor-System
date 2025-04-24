# 👨‍👩‍👧‍👦 ChildMonitor System

A Python-based parental control system that monitors and limits children's computer usage based on customizable schedules. The system includes two programs:

- **Child Program (C):** Enforces time limits, monitors usage, and restricts access.
- **Parent Program (P):** Allows parents to view & update the schedule, upload it to the cloud, and review logs.

---

## 📁 Project Structure
```
src_code/
├── child_program.py           # Main logic for enforcing usage limits
├── parent_program.py          # Tool for parents to edit schedule and sync
├── cloud_sync.py              # Shared module for Google Drive API
├── schedule.txt               # Main schedule file (cloud synced)
├── block_until.txt            # Save the time children can use computer again
├── last_modified.txt          # Timestamp for last downloaded schedule
├── credentials.json           # OAuth credentials for Google Drive
├── usage_tracker.json         # Save the amount of time user used in a session
├── logs/
│   ├── keylog.txt             # Keystroke log file
│   ├── screenshots/           # Captured screen images
└── ...
```

---

## ⚙️ Requirements
- Python 3.8+
- [Google Drive API](https://console.cloud.google.com/)
- Required packages:
```bash
pip install pydrive filelock pyautogui pynput
```

---

## 🚀 How to Run

### 📌 Step 1: Set up Google Drive API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Drive API**
3. Create **OAuth Client ID** → Choose type **Desktop app**
4. Download `credentials.json` and place it in project folder
5. Add your email to **Test Users**

### 👩‍💻 Step 2: Parent Program
```bash
python parent_program.py
```
- Modify schedule
- Upload to Google Drive

### 👦 Step 3: Child Program
```bash
python child_program.py
```
- Downloads schedule if updated
- Checks and enforces time limits
- Logs keystrokes and screenshots

---

## 🔐 Features
- Cloud-based shared schedule file (`schedule.txt`)
- File-locking to avoid race conditions
- Auto shutdown after time expires
- Auto startup at OS boot (with additional `.desktop` config or startup shortcut)
- Keylogging & screenshot every minute

---

## 📌 Example `schedule.txt`
```
F06:00 T07:00
F19:00 T21:30 D60 I20 S150
```
