// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LogProvider{
    // Struct của log
    struct LogEntry {
        string ipfsHash; // CID
        uint256 timestamp;  // thgian lưu vào block
        address recorder; // IP lưu block
    }
    // DS các thiết bị đẩy lên => DS log của nó
    mapping(string => LogEntry[]) private deviceLogs;
    // Event báo có log mới (app lắng nghe)
    event LogRecorded(string indexed deviceId, string ipfsHash, uint256 timestamp); 
    // indexed: make var filterable in event logs. Used for fixed types (addr, bool, uint)
    
    /*
     * @dev Lưu hash của file log lên Blockchain
     * @param _deviceId
     * @param _ipfsHash
     */
    function recordLog(string memory _deviceId, string memory _ipfsHash) public{
        // memory: store var in memory, not BC's persistent storage. Used for dynamic types (string, bytes)
        LogEntry memory newEntry = LogEntry({
            ipfsHash: _ipfsHash,
            timestamp: block.timestamp,
            recorder: msg.sender
        });
        deviceLogs[_deviceId].push(newEntry);
        // Bắn ra event realtime
        emit LogRecorded(_deviceId, _ipfsHash, block.timestamp);
    }
    /**
     * @dev Lấy DS các hash của 1 device
     */
    function getLogs(string memory _deviceId) public view returns (LogEntry[] memory){
        // view: read-only, returns: specify return type
        return deviceLogs[_deviceId];
    }
    /**
     * @dev Lấy entry mới nhất của 1 device
     */
    function getLatestLog(string memory _deviceId) public view returns (string memory, uint256) {
        require(deviceLogs[_deviceId].length > 0, "No logs found for this device.");
        LogEntry memory lastEntry = deviceLogs[_deviceId][deviceLogs[_deviceId].length - 1];
        return (lastEntry.ipfsHash, lastEntry.timestamp);
    }

}