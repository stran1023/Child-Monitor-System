from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import datetime
import os

# Khởi tạo Google Drive API

def init_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)

# Tải file schedule.txt nếu có thay đổi

def download_if_updated(drive):
    file_list = drive.ListFile({'q': "title = 'schedule.txt'"}).GetList()
    if not file_list:
        print("❌ Không tìm thấy schedule.txt trên Google Drive.")
        return False

    file = file_list[0]
    cloud_time = datetime.datetime.strptime(file['modifiedDate'], "%Y-%m-%dT%H:%M:%S.%fZ")

    local_time = None
    if os.path.exists("last_modified.txt"):
        with open("last_modified.txt", "r") as f:
            try:
                local_time = datetime.datetime.strptime(f.read().strip(), "%Y-%m-%dT%H:%M:%S.%fZ")
            except:
                local_time = None

    if not local_time or cloud_time > local_time:
        file.GetContentFile("schedule.txt")
        with open("last_modified.txt", "w") as f:
            f.write(file['modifiedDate'])
        print("📥 Đã tải file mới từ cloud.")
        return True
    else:
        print("✅ schedule.txt không thay đổi.")
        return False

# Upload file schedule.txt lên Drive

def upload_schedule_to_drive(drive):
    file_list = drive.ListFile({'q': "title = 'schedule.txt'"}).GetList()
    if file_list:
        file = file_list[0]
    else:
        file = drive.CreateFile({'title': 'schedule.txt'})

    file.SetContentFile("schedule.txt")
    file.Upload()
    print("✅ Đã cập nhật schedule.txt lên Drive")
