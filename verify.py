# Pinata
import os
from hashlib import sha256

import requests
from web3 import Web3
import json
from ipfs_cid import cid_sha256_hash

from main import upload_to_pinata

PINATA_KEY = '7f2ace831622cfae6eb3'
PINATA_SECRET_KEY = '794a72da35b4dc91c8f6a1ce5378b215c45311c959778819eb13d8483da4de6b'
PINATA_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
GROUP_ID_VERIFY = "2bcfe6e8-b6e2-4333-ba4d-833becb89e83"

# Ganache
GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = Web3.to_checksum_address("0x41CA0Ef7d9DDB2fc994eAE51dAa40099c9847F8d")  # Địa chỉ account deploy trên Ganache
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
w3.eth.default_account = w3.eth.accounts[1]
# Load ABI từ file
with open('contract_abi.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)


def add_to_ipfs_group(cid, group_id):
    url = f"https://api.pinata.cloud/groups/{group_id}/hash/{cid}"
    headers = {
        'pinata_api_key': PINATA_KEY,
        'pinata_secret_api_key': PINATA_SECRET_KEY
    }
    response = requests.put(url, headers=headers)

"""Băm hash 1 file"""

def verify_log():
    blockchain_records = contract.functions.getLogs(DEVICE_ID).call()

    for entry in blockchain_records:
        file_name = entry[1]  # fileName
        cid_og = entry[0]  # ipfsHash
        timestamp = entry[2]  # timestamp
        recorder = entry[3]  # recorder address
        # Lấy link file archive (đã upload) bằng filename
        file_path = os.path.join(ARCHIVE_DIR, file_name)
        print(file_path)
        if os.path.exists(file_path):
            # Băm file local để lấy CID hiện tại
            cid_now = upload_to_pinata(file_path, GROUP_ID_VERIFY)

            # ==SO KHỚP==
            if cid_now == cid_og:
                print(f"{file_name}: Toàn vẹn")
                return "Toàn vẹn"
            else:
                print(f"{file_name}: PHÁT HIỆN THAY ĐỔI!")
                print(f"   BC: {cid_og} vs Local: {cid_now}")
                return "Bị sửa đổi"
        else:
            print(f"{file_name}: đã bị xóa/đổi tên trên máy local.")
            return "Không có trên blockchain"