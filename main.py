
import os
import time
import shutil
import json
from datetime import datetime

import verify
import requests
from web3 import Web3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Pinata
PINATA_KEY = '7f2ace831622cfae6eb3'
PINATA_SECRET_KEY = '794a72da35b4dc91c8f6a1ce5378b215c45311c959778819eb13d8483da4de6b'
PINATA_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
GROUP_ID_UPLOAD = "d6ac7e94-f7ca-41f3-b3c1-5e5a0f52da66"
GROUP_ID_VERIFY = "2bcfe6e8-b6e2-4333-ba4d-833becb89e83"

# Ganache
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = Web3.to_checksum_address("0x615228F0a42117FfEE2e86a071b289C085792cfA")  # Địa chỉ account deploy contract trên Ganache
DEVICE_ID = "Windows-PC-01"

# Folder
LOG_DIR = "D:\\SCHOOL PJ\\Log\\LOGS"
ARCHIVE_DIR = "D:\\SCHOOL PJ\\Log\\LOGS\\archive"

# ================= KHỞI TẠO WEB3 =================
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if w3.is_connected():
    print("Đã kết nối tới Ganache Blockchain")
else:
    print("Không thể kết nối tới Ganache")
    exit()
# Default account đầu tiên
w3.eth.default_account = w3.eth.accounts[1]
# Load ABI từ file
with open('contract_abi.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# print(w3.eth.chain_id)
# # Kiểm tra xem code đã tồn tại chưa
# target_addr = Web3.to_checksum_address(CONTRACT_ADDRESS)
# code = w3.eth.get_code(target_addr)
# print(f"Bytecode tìm thấy: {code.hex()}")
# # In ra danh sách các hàm mà Web3 nhận diện được từ ABI
# print([func.fn_name for func in contract.all_functions()])
#
# if code.hex() == "0x":
#     print("❌ Vẫn không thấy Contract. Khả năng cao Remix đang Deploy vào một mạng khác (như Remix VM)!")
# else:
#     print("🎉 Đã tìm thấy Smart Contract! Bạn có thể tiếp tục.")


# ================= UPLOAD LOG =================
def upload_to_pinata(file_path, group_id):
    """Tải file lên Pinata và trả về mã CID"""
    print(f"Đang upload {os.path.basename(file_path)} lên IPFS...")
    headers = {
        'pinata_api_key': PINATA_KEY,
        'pinata_secret_api_key': PINATA_SECRET_KEY
    }
    # Upload vào group Upload
    metadata = {
        "name": os.path.basename(file_path),
        "keyvalues": {
            "project": "LogProject"
        }
    }
    with open(file_path, 'rb') as f:
        payload = {
            'pinataMetadata': json.dumps(metadata),
            'pinataOptions': json.dumps({"groupId": group_id})
        }
        files = {
            'file': f
        }
        response = requests.post(PINATA_URL, files=files, data=payload, headers=headers)
        if response.status_code == 200:
            cid = response.json()['IpfsHash']
            print(f"Upload thành công. CID: {cid}")
            return cid
        else:
            print(f"Lỗi Upload Pinata: {response.text}")
            return None


def record_to_blockchain(device_id, file_name, cid):
    """Ghi CID vào Smart Contract"""
    print("Đang gửi transaction lên blockchain...")
    try:
        # Gọi hàm recordLog từ contract
        tx_hash = contract.functions.recordLog(device_id, file_name, cid).transact()
        # Đợi transaction được đào
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        print(f"Đã ghi lên block. TxHash: {tx_hash.hex()}")
        print(f"   Block Number: {receipt.blockNumber}")
        return True
    except Exception as e:
        print(f"Lỗi Blockchain: {e}")
        return False


# ================= XỬ lý file =================

class LogHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory:
            print(f"Phát hiện file mới: {os.path.basename(event.src_path)}. Chờ đóng gói...")

def run_automation():
    # Khởi tạo watcher
    event_handler = LogHandler()
    observer = Observer()
    observer.schedule(event_handler, path=LOG_DIR, recursive=False)
    observer.start()

    print(f"Đang giám sát thư mục '{LOG_DIR}'...")
    try:
        while True:
            # Lấy DS file trong folder logs
            files = [f for f in os.listdir(LOG_DIR) if f.endswith('.json')]
            current_minute = datetime.now().strftime("%Y%m%d%H%M")

            for file_name in files:
                file_path = os.path.join(LOG_DIR, file_name)
                print(os.path.join(LOG_DIR, file_name))
                # Chỉ xử lý nếu file_name 0 chứa phút hiện tại
                # đảm bảo Nxlog đã chuyển sang file mới
                if current_minute not in file_name:
                    print(f"\nFile {file_name} đã đóng gói xong. Bắt đầu đẩy lên Blockchain...")

                    # Upload lên IPFS
                    cid = upload_to_pinata(file_path, GROUP_ID_UPLOAD)
                    if cid:
                        # Upload lên blockchain

                        success = record_to_blockchain(DEVICE_ID, file_name, cid)
                        if success:
                            # Di chuyển vào archive
                            dest_path = os.path.join(ARCHIVE_DIR, file_name)
                            if not os.path.exists(ARCHIVE_DIR): os.makedirs(ARCHIVE_DIR)

                            # Thử lại nếu file vẫn bị lock nhẹ
                            try:
                                shutil.move(file_path, dest_path)
                                print(f"Hoàn tất lưu trữ: {file_name}")
                            except Exception as e:
                                print(f"Đợi thêm để di chuyển file: {e}")

            # Nghỉ trước khi quét lại DS file
            time.sleep(10)

    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ================= Main =================
# if __name__ == "__main__":
#     verify.verify_log()




