import os
import time
from datetime import datetime, timedelta
import hashlib
import json
import pyautogui
from pynput import keyboard
import sys
from filelock import FileLock
from cloud_sync import init_drive, download_if_updated

PARENT_PASSWORD = "parent123"
CHILD_PASSWORD = "child123"
SCHEDULE_FILE = "schedule.txt"
BLOCK_FILE = "block_until.txt"
USAGE_TRACKER_FILE = "usage_tracker.json"
key_log_path = os.path.join("logs", "keylog.txt")

def add_to_startup():
    path = os.path.realpath(sys.argv[0])
    startup_dir = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
    shortcut_path = os.path.join(startup_dir, "ChildMonitor.lnk")

    if not os.path.exists(shortcut_path):
        import winshell
        from win32com.client import Dispatch
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = path
        shortcut.WorkingDirectory = os.path.dirname(path)
        shortcut.save()

def get_password():
    try:
        import getpass
        return getpass.getpass("Nhập mật khẩu: ")
    except:
        return input("Nhập mật khẩu: ")

def is_in_allowed_time():
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    print(current_minutes)

    schedules = parse_schedule_file()

    print(schedules)

    for sch in schedules:
        start_m = int(sch["start"][:2]) * 60 + int(sch["start"][3:])
        end_m = int(sch["end"][:2]) * 60 + int(sch["end"][3:])

        if start_m <= current_minutes < end_m:
            # Đang trong khung F...T
            D = sch["D"]
            I = sch["I"]
            S = sch["S"]

            if not D and not I and not S:
                return True  # không có giới hạn thêm

            # Load usage tracking file
            if os.path.exists(USAGE_TRACKER_FILE):
                with open(USAGE_TRACKER_FILE, "r") as f:
                    data = json.load(f)
            else:
                return True  # chưa có file theo dõi ⇒ cho phép dùng

            total_today = data.get("total_minutes_today", 0)
            session_used = data.get("session_minutes_used", 0)
            last_start_str = data.get("last_session_start")
            last_start = datetime.strptime(last_start_str, "%Y-%m-%d %H:%M:%S") if last_start_str else None

            # 1. Check tổng thời gian dùng hôm nay
            if S and total_today >= S:
                return False

            # 2. Check nếu đã dùng quá D phút liên tục và chưa nghỉ đủ I phút
            if D and session_used >= D:
                if I and last_start:
                    mins_since_last_session = (now - last_start).total_seconds() / 60
                    if mins_since_last_session < D + I:
                        return False
            return True

    return False  # không nằm trong khung F...T

def get_d_i_s_limited_time():
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute
    today_str = now.strftime("%Y-%m-%d")
    schedules = parse_schedule_file()

    for sch in schedules:
        start_m = int(sch["start"][:2]) * 60 + int(sch["start"][3:])
        end_m = int(sch["end"][:2]) * 60 + int(sch["end"][3:])

        if start_m <= current_minutes < end_m:
            # nằm trong khoảng hợp lệ, giờ xét đến D, I, S
            D = sch["D"]
            I = sch["I"]
            S = sch["S"]

            time_left_in_block = end_m - current_minutes

            if not D and not I and not S:
                return time_left_in_block  # không giới hạn thêm

            if not os.path.exists(USAGE_TRACKER_FILE):
                data = {
                    "last_session_start": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "session_minutes_used": 0,
                    "total_minutes_today": 0
                }
            else:
                with open(USAGE_TRACKER_FILE, "r") as f:
                    data = json.load(f)

            total_today = data["total_minutes_today"] if data.get("total_minutes_today") else 0
            if today_str not in data.get("last_session_start", ""):
                total_today = 0  # reset mỗi ngày

            # kiểm tra tổng thời gian
            if S and total_today >= S:
                return 0

            # kiểm tra thời lượng 1 phiên
            session_used = data["session_minutes_used"]
            if D and session_used >= D:
                # kiểm tra đã nghỉ đủ I chưa
                last_start = datetime.strptime(data["last_session_start"], "%Y-%m-%d %H:%M:%S")
                minutes_since_last = (now - last_start).total_seconds() / 60
                if I and minutes_since_last < D + I:
                    return 0
                else:
                    # reset session nếu nghỉ đủ
                    data["session_minutes_used"] = 0
                    data["last_session_start"] = now.strftime("%Y-%m-%d %H:%M:%S")

            # update file usage
            data["session_minutes_used"] += 1
            data["total_minutes_today"] = total_today + 1
            with open(USAGE_TRACKER_FILE, "w") as f:
                json.dump(data, f)

            # chọn thời gian còn lại nhỏ nhất trong các giới hạn
            limit_candidates = [time_left_in_block]

            if D is not None:
                limit_candidates.append(D - data["session_minutes_used"])
            if S is not None:
                limit_candidates.append(S - total_today)

            # trả về số phút còn lại (>= 0)
            return max(0, min(limit_candidates))

    return 0

def monitor_usage():
    print("🎯 Bắt đầu giám sát...")

    last_hash = None
    warned_1_min = False
    keylogger = start_keylogger()

    time_left = get_d_i_s_limited_time()
    print(f"Bạn còn {time_left} phút để sử dụng")

    while True:
        time_left = get_d_i_s_limited_time()

        if time_left <= 0:
            next_time = get_next_available_time()
            print(f"⛔ Hết thời gian. Bạn có thể bật máy lại lúc: {next_time}")
            keylogger.stop()
            time.sleep(3)
            shutdown_machine()
            break
        elif time_left == 1 and not warned_1_min:
            next_time = get_next_available_time()
            print(f"⚠ Còn 1 phút. Máy sẽ tắt sau đó. Bạn có thể bật lại lúc: {next_time}")
            warned_1_min = True

        # Chụp screenshot
        try:
            capture_screenshot()
        except Exception as e:
            print(f"❌ Lỗi screenshot: {e}")

        # Kiểm tra file lịch trình thay đổi
        try:
            with open(SCHEDULE_FILE, "rb") as f:
                content = f.read()
                current_hash = hashlib.md5(content).hexdigest()

            if current_hash != last_hash:
                print("🔄 File schedule đã thay đổi.")
                last_hash = current_hash
                warned_1_min = False
        except Exception as e:
            print(f"⚠ Lỗi kiểm tra schedule.txt: {e}")

        time.sleep(60)

def capture_screenshot():
    now = datetime.now()
    folder = os.path.join("logs", "screenshots", now.strftime("%Y-%m-%d"))
    os.makedirs(folder, exist_ok=True)

    filename = now.strftime("%H-%M-%S") + ".png"
    path = os.path.join(folder, filename)

    screenshot = pyautogui.screenshot()
    screenshot.save(path)

def start_keylogger():
    os.makedirs("logs", exist_ok=True)
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener

def on_press(key):
    try:
        with open(key_log_path, "a", encoding="utf-8") as f:
            f.write(f"{key.char}")
    except AttributeError:
        with open(key_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{key.name}]")

def notify_and_shutdown():
    print("🚫 Bạn không được phép dùng máy lúc này!")
    print("💡 Nhập đúng mật khẩu phụ huynh để huỷ tắt máy...")
    for i in range(15, 0, -1):
        print(f"Tắt máy sau {i} giây...", end='\r')
        time.sleep(1)
    shutdown_machine()

def shutdown_machine():
    print("⚠ Máy sẽ tắt ngay...")
    os.system("shutdown /s /t 1")

def is_blocked_now():
    if os.path.exists(BLOCK_FILE):
        with open(BLOCK_FILE, "r") as f:
            block_time_str = f.read().strip()
        try:
            block_time = datetime.strptime(block_time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if now < block_time:
                remaining = block_time - now
                print(f"🚫 Máy đang bị khóa. Còn {int(remaining.total_seconds() // 60)} phút nữa mới được dùng lại.")
                time.sleep(5)
                shutdown_machine()
                return True
        except:
            pass
    return False

def block_for_10_minutes():
    unblock_time = datetime.now() + timedelta(minutes=10)
    with open(BLOCK_FILE, "w") as f:
        f.write(unblock_time.strftime("%Y-%m-%d %H:%M:%S"))
    print("⛔ Sai mật khẩu 3 lần. Máy sẽ bị khóa trong 10 phút.")
    shutdown_machine()

def get_next_available_time():
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute
    today_str = now.strftime("%Y-%m-%d")
    schedules = parse_schedule_file()

    # Kiểm tra từng khung giờ trong ngày
    for sch in schedules:
        start_m = int(sch["start"][:2]) * 60 + int(sch["start"][3:])
        end_m = int(sch["end"][:2]) * 60 + int(sch["end"][3:])
        D = sch["D"]
        I = sch["I"]
        S = sch["S"]

        # Nếu thời gian hiện tại chưa đến khung giờ tiếp theo
        if current_minutes < start_m:
            h, m = divmod(start_m, 60)
            return f"{h:02d}:{m:02d} (bắt đầu khung giờ tiếp theo)"

        # Nếu đang trong khung giờ nhưng bị chặn bởi D hoặc S
        if start_m <= current_minutes < end_m:
            try:
                with open(USAGE_TRACKER_FILE, "r") as f:
                    data = json.load(f)
            except:
                return "Ngay bây giờ (dữ liệu sử dụng chưa có)"

            total_today = data.get("total_minutes_today", 0)
            session_used = data.get("session_minutes_used", 0)
            last_start_str = data.get("last_session_start")
            last_start = datetime.strptime(last_start_str, "%Y-%m-%d %H:%M:%S") if last_start_str else None

            # Nếu đã dùng đủ tổng thời gian trong ngày
            if S is not None and total_today >= S:
                # chuyển sang khung giờ tiếp theo
                continue

            # Nếu đã dùng đủ thời lượng D, kiểm tra xem nghỉ I đủ chưa
            if D is not None and session_used >= D:
                if I is not None and last_start:
                    resume_time = last_start + timedelta(minutes=D+I)
                    if resume_time > now:
                        return resume_time.strftime("%H:%M") + " (sau thời gian nghỉ bắt buộc)"
                    else:
                        return "Ngay bây giờ (đã nghỉ đủ)"
            return "Ngay bây giờ (trong khung giờ hợp lệ)"

    return "Không còn khung giờ sử dụng nào trong hôm nay"

def parse_schedule_file():
    schedules = []
    with open(SCHEDULE_FILE, "r") as f:
        for line in f:
            if line.startswith("F"):
                parts = line.strip().split()
                start = parts[0][1:]  # Fhh:mm
                end = parts[1][1:]    # Thh:mm
                schedule = {
                    "start": start,
                    "end": end,
                    "D": None,
                    "I": None,
                    "S": None
                }
                for part in parts[2:]:
                    if part.startswith("D"):
                        schedule["D"] = int(part[1:])
                    elif part.startswith("I"):
                        schedule["I"] = int(part[1:])
                    elif part.startswith("S"):
                        schedule["S"] = int(part[1:])
                schedules.append(schedule)
    return schedules

def main():
    add_to_startup()

    if is_blocked_now():
        return

    wrong_count = 0

    while True:
        pw = get_password()

        drive = init_drive()
        download_if_updated(drive)  # Lấy file lịch mới nếu có

        lock = FileLock("schedule.txt.lock")
        try:
            with lock.acquire(timeout=3):
                with open("schedule.txt", "r") as f:
                    schedule = f.read()
                    print("📄 Lịch trình:")
                    print(schedule)
        except:
            print("⚠️ Không thể đọc lịch trình (file bị khóa bởi chương trình khác).")
            break

        if pw == PARENT_PASSWORD:
            print("✅ Đăng nhập phụ huynh thành công! Cho phép dùng 60 phút.")
            time.sleep(3600)
            wrong_count = 0
        elif not is_in_allowed_time():
            notify_and_shutdown()
        elif pw == CHILD_PASSWORD:
            print("🎮 Mật khẩu trẻ hợp lệ. Vào chế độ giám sát...")
            wrong_count = 0
            monitor_usage()
            break
        else:
            wrong_count += 1
            print(f"❌ Sai mật khẩu. ({wrong_count}/3)")
            if wrong_count >= 3:
                block_for_10_minutes()

if __name__ == "__main__":
    main()
