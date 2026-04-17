import hashlib
import threading
from datetime import datetime
import shutil
import time
from threading import Thread

import base58
import requests
import streamlit as st
import pandas as pd
import os
import json

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from web3 import Web3

# Pinata
PINATA_KEY = '7f2ace831622cfae6eb3'
PINATA_SECRET_KEY = '794a72da35b4dc91c8f6a1ce5378b215c45311c959778819eb13d8483da4de6b'
PINATA_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
JWT_TOKEN = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySW5mb3JtYXRpb24iOnsiaWQiOiI4NTRjMj"
             "M2Ni00NTE1LTRiYWQtYmVlMi01ZDU4NGViMTczMmQiLCJlbWFpbCI6Im5ndXllbm5naGk1NDIwQGdtYW"
             "lsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaW5fcG9saWN5Ijp7InJlZ2lvbnMiOlt7ImRlc2l"
             "yZWRSZXBsaWNhdGlvbkNvdW50IjoxLCJpZCI6IkZSQTEifSx7ImRlc2lyZWRSZXBsaWNhdGlvbkNvdW50I"
             "joxLCJpZCI6Ik5ZQzEifV0sInZlcnNpb24iOjF9LCJtZmFfZW5hYmxlZCI6ZmFsc2UsInN0YXR1cyI6IkFD"
             "VElWRSJ9LCJhdXRoZW50aWNhdGlvblR5cGUiOiJzY29wZWRLZXkiLCJzY29wZWRLZXlLZXkiOiI3ZjJhY2U4"
             "MzE2MjJjZmFlNmViMyIsInNjb3BlZEtleVNlY3JldCI6Ijc5NGE3MmRhMzViNGRjOTFjOGY2YTFjZTUzNzhiM"
             "jE1YzQ1MzExYzk1OTc3ODgxOWViMTNkODQ4M2RhNGRlNmIiLCJleHAiOjE4MDY2MzkwMzF9.ypCU4771cXCykLI"
             "B63MLO0qCaGztD4zM5hsHTgWkWs0")
GROUP_ID_UPLOAD = "d6ac7e94-f7ca-41f3-b3c1-5e5a0f52da66"
GROUP_ID_VERIFY = "2bcfe6e8-b6e2-4333-ba4d-833becb89e83"

# Ganache
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0xB197825829D62c4001614939237Da35965F2Eb63"
DEVICE_ID = "Windows-PC-01"

# Folder logs
LOG_DIR = "D:\\SCHOOL PJ\\Log\\LOGS"
ARCHIVE_DIR = "D:\\SCHOOL PJ\\Log\\LOGS\\archive"

# Kết nối Blockchain
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
w3.eth.default_account = w3.eth.accounts[1]
with open('contract_abi.json', 'r') as f:
    abi = json.load(f)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

# ================= BĂM HASH =================
def varint_encode(n):
    #Mã hóa số nguyên theo chuẩn Protobuf Varint
    res = []
    while n > 0:
        res.append((n & 0x7F) | 0x80)
        n >>= 7
    if not res:
        return b'\x00'
    res[-1] &= 0x7F
    return bytes(res)

def get_local_cid(file_path):
    """
    Tính CID v0 (Qm...) khớp với Pinata.
    Áp dụng cấu trúc UnixFS DAG-PB Protobuf.
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    data_len = len(data)

    # 1. Tạo UnixFS (Data Message)
    # Field 1: Type = 2 (File) -> \x08\x02
    # Field 2: Data = nội dung -> \x12 + varint(chiều dài) + data
    # Field 3: FileSize = chiều dài -> \x18 + varint(chiều dài)
    inner_payload = b'\x08\x02\x12' + varint_encode(data_len) + data + b'\x18' + varint_encode(data_len)

    # 2. Tạo vỏ (PBNode Message)
    # Field 1: Data = Lõi UnixFS -> \x0a + varint(chiều dài lõi) + lõi
    outer_payload = b'\x0a' + varint_encode(len(inner_payload)) + inner_payload

    # 3. Băm SHA-256 toàn gói tin
    sha256_hash = hashlib.sha256(outer_payload).digest()

    # 4. Bọc Multihash: \x12 (SHA2-256) + \x20 (chiều dài 32 bytes) + mã băm
    multihash = b'\x12\x20' + sha256_hash

    # 5. Mã hóa Base58 để ra chuỗi Qm...
    cid_v0 = base58.b58encode(multihash).decode('utf-8')
    return cid_v0

# ================= UPLOAD LOG =================
def upload_to_pinata(file_path, group_id, og_name):
    headers = {'pinata_api_key': PINATA_KEY, 'pinata_secret_api_key': PINATA_SECRET_KEY}
    metadata = {
        "name": og_name, # tên gốc của file sau khi nxlog process xong
        "keyvalues": {"project": "LogProject"}
    }
    with open(file_path, 'rb') as f:
        payload = {
            'pinataMetadata': json.dumps(metadata),
            'pinataOptions': json.dumps({"groupId": group_id})
        }
        # requests.post cho đặt tên ảo cho file stream
        files = {
            'file': (og_name, f, 'application/json')
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
    # Ghi CID vào Smart Contract
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


# --- BACKGROUND PROCESS (theo dõi local folder) ---
# Sidebar thông báo
bg_info = st.sidebar.empty()

# Tạo event kiểm soát dừng luồng
if 'stop_event' not in st.session_state:
    st.session_state.stop_event = threading.Event()

def background_worker(stop_event):
    #chạy ngầm canh chừng folder
    while not stop_event.is_set():
        files = [f for f in os.listdir(LOG_DIR) if f.endswith('.json')]

        for file_name in files:
            file_path = os.path.join(LOG_DIR, file_name)
            processing_path = file_path + ".processing"  # Đuôi tạm thời

            try:
                # 1. Thử đổi tên file
                # Nếu Nxlog đang ghi -> PermissionError
                os.rename(file_path, processing_path)

                # Nxlog đã nhả file
                with open(".status_msg", "w", encoding="utf-8") as f:
                    f.write(f"Đang xử lý: {file_name}")

                # 2. Xử lý file
                cid = upload_to_pinata(processing_path, GROUP_ID_UPLOAD)

                if cid:
                    tx = record_to_blockchain(DEVICE_ID, file_name, cid)
                    if tx:
                        # 3. Chuyển vào archive đổi lại tên gốc
                        dest_path = os.path.join(ARCHIVE_DIR, file_name)
                        if not os.path.exists(ARCHIVE_DIR): os.makedirs(ARCHIVE_DIR) #tạo path nếu thiếu
                        shutil.move(processing_path, dest_path)

                        with open(".status_msg", "w", encoding="utf-8") as f:
                            f.write(f"Đã lưu trữ thành công: {file_name}")

            except PermissionError:
                # File đang bị Nxlog khóa -> bỏ qua chờ 10s
                pass
            except Exception as e:
                # Các lỗi khác, đổi tên lại để lần sau xử lý tiếp
                if os.path.exists(processing_path):
                    os.rename(processing_path, file_path)

        stop_event.wait(10)


# Khởi chạy luồng ngầm duy nhất một lần
if 'bg_thread' not in st.session_state:
    st.session_state.stop_event.clear() # Đảm bảo cờ đang tắt
    st.session_state.bg_thread = Thread(target=background_worker, args=(st.session_state.stop_event,), daemon=True)
    st.session_state.bg_thread.start()

# ========= UI STREAMLIT ========
st.set_page_config(page_title="Blockchain Log Integrity Monitor", layout="wide")
st.title("Hệ thống giám sát toàn vẹn log")
st.markdown("""
    <style>
    .stTable { font-size: 0.9rem; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar info
st.sidebar.header("Thông số kết nối")
st.sidebar.info(f"Mạng: {GANACHE_URL}\n\nDevice: {DEVICE_ID}")

# Sidebar trạng thái canh chừng
with st.sidebar:
    st.header("Trạng thái Background")
    status_area = st.empty()
    if os.path.exists(".status_msg"):
        with open(".status_msg", "r", encoding="utf-8") as f:
            status_area.caption(f.read())
    else:
        status_area.caption("Đang canh chừng folder LOG...")

# Layout chính
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Kiểm tra toàn vẹn dữ liệu")
    if st.button('QUÉT & ĐỐI SOÁT (VERIFY)'):
        with st.spinner('Đang lấy CID thực tế và so khớp Blockchain...'):
            # Lấy data từ Blockchain
            bc_logs = contract.functions.getLogs(DEVICE_ID).call()
            bc_dict = {item[1]: item[0] for item in bc_logs}

            # Quét /archive
            data_rows = []
            for fname in os.listdir(ARCHIVE_DIR):
                fpath = os.path.join(ARCHIVE_DIR, fname)
                # Băm hash file local
                curr_cid = get_local_cid(fpath)

                bc_hash = bc_dict.get(fname)  # Lấy CID gốc dựa trên tên file
                status = "An toàn ✅"
                if bc_hash is None:
                    status = "Không có trên Blockchain ❌"
                elif bc_hash != curr_cid:
                    status = "Bị sửa đổi ⚠️"

                data_rows.append({
                    "File": fname,
                    "CID Local": curr_cid,
                    "BC Hash": bc_hash if bc_hash else "N/A",
                    "Trạng thái": status
                })
            # Hiển thị bảng màu
            df = pd.DataFrame(data_rows)


            def color_st(val):
                if "⚠️" in val: return 'background-color: #ffffcc; color: black'
                if "❌" in val: return 'background-color: #ffcccc; color: black'
                return 'background-color: #c8e6c9; color: black'


            if not df.empty:
                st.dataframe(df.style.map(color_st, subset=['Trạng thái']), width='stretch')
            else:
                st.info("Thư mục Archive hiện đang trống.")

with col2:
    st.subheader("Thống kê Folder")
    files_in_logs = [f for f in os.listdir(LOG_DIR) if f.endswith('.json')]
    st.metric("Log đang đợi (LOGS)", len(files_in_logs))

    files_in_archive = os.listdir(ARCHIVE_DIR)
    st.metric("Log đã xử lý (Archive)", len(files_in_archive))

    if st.checkbox("Xem danh sách log đã lưu"):
        st.write(files_in_archive)

# Refresh UI để cập nhật sidebar status
time.sleep(1)
if len(files_in_logs) > 0: st.rerun()

st.subheader("Lịch sử blockchain")
try:
    # Lấy 5 block cuối cùng để xem các transaction mới nhất
    latest_block = w3.eth.block_number
    recent_txs = []
    for i in range(latest_block, max(0, latest_block - 5), -1):
        block = w3.eth.get_block(i, full_transactions=True)
        for tx in block.transactions:
            recent_txs.append({"Block": i, "Hash": tx.hash.hex(), "From": tx['from']})

    st.table(recent_txs)
except:
    st.write("Chưa có giao dịch nào được thực hiện.")