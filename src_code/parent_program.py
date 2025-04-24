from filelock import FileLock, Timeout
from cloud_sync import init_drive, upload_schedule_to_drive

def get_password():
    try:
        import getpass
        return getpass.getpass("🔐 Nhập mật khẩu phụ huynh: ")
    except:
        return input("🔐 Nhập mật khẩu phụ huynh: ")

def check_parent_password():
    pw = get_password()
    return pw == "parent123"

def load_schedule():
    print("\n📆 Lịch trình hiện tại:\n")
    with open("schedule.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            print(f"{i}. {line.strip()}")

def edit_schedule():
    print("\n📝 Bắt đầu chỉnh sửa lịch trình:")
    load_schedule()
    choice = input("Bạn có muốn (a) thêm dòng mới, (b) sửa dòng, (c) xóa dòng, hay (enter) để thoát? ")
    
    with open("schedule.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    if choice.lower() == "a":
        new_line = input("👉 Nhập dòng mới (VD: F07:00 T10:00 D60 I10 S120): ")
        lines.append(new_line + "\n")
    elif choice.lower() == "b":
        idx = int(input("🔢 Chọn dòng cần sửa (số thứ tự): ")) - 1
        if 0 <= idx < len(lines):
            lines[idx] = input("✏️ Nhập dòng mới: ") + "\n"
    elif choice.lower() == "c":
        idx = int(input("🗑️ Chọn dòng cần xóa: ")) - 1
        if 0 <= idx < len(lines):
            lines.pop(idx)

    with open("schedule.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("✅ Đã cập nhật file thành công.")

def safe_edit_schedule():
    drive = init_drive()
    lock = FileLock("schedule.txt.lock")

    try:
        # chờ tối đa 5 giây để có quyền sửa file
        with lock.acquire(timeout=5):
            print("🔐 Đã vào miền găng – bạn có quyền chỉnh sửa.")
            edit_schedule()
            print("✅ Đã chỉnh sửa file lịch trình.")
            upload_schedule_to_drive(drive)
    except Timeout:
        print("⛔ File đang được chỉnh bởi người khác. Vui lòng thử lại sau.")

def view_keylog():
    print("\n🧠 Nội dung phím đã gõ:\n")
    try:
        with open("logs/keylog.txt", "r", encoding="utf-8") as f:
            print(f.read())
    except:
        print("🚫 Không tìm thấy log phím.")

def view_screenshots():
    import os
    from PIL import Image

    folder = "logs/screenshots"
    if not os.path.exists(folder):
        print("🚫 Không có ảnh chụp nào.")
        return

    for root, _, files in os.walk(folder):
        for file in sorted(files):
            if file.endswith(".png"):
                path = os.path.join(root, file)
                print(f"🖼️ Ảnh: {path}")
                try:
                    img = Image.open(path)
                    img.show()
                except:
                    print("❌ Không thể mở ảnh.")

def main():
    if not check_parent_password():
        print("❌ Sai mật khẩu")
        return
    
    while True:
        print("\n🎛️ MENU CHƯƠNG TRÌNH PHỤ HUYNH")
        print("1. Xem lịch trình sử dụng")
        print("2. Chỉnh sửa lịch trình")
        print("3. Xem log bàn phím")
        print("4. Xem ảnh chụp màn hình")
        print("5. Thoát")
        
        choice = input("👉 Chọn chức năng: ")
        if choice == "1":
            load_schedule()
        elif choice == "2":
            safe_edit_schedule()
        elif choice == "3":
            view_keylog()
        elif choice == "4":
            view_screenshots()
        elif choice == "5":
            print("👋 Tạm biệt phụ huynh!")
            break
        else:
            print("⚠️ Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()