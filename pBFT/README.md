# pBFT (Practical Byzantine Fault Tolerance) Implementation

## Tổng quan

Đây là implementation của thuật toán **Practical Byzantine Fault Tolerance (pBFT)** cho blockchain, được xây dựng dựa trên cơ sở hạ tầng gRPC tương tự như RAFT.

### Đặc điểm chính

- **Byzantine Fault Tolerance**: Chịu được tối đa `f` node lỗi/độc hại trong tổng số `3f+1` nodes
  - Với 5 nodes: `f=1`, có thể chịu được 1 node Byzantine
- **Three-Phase Commit Protocol**:
  1. **Pre-prepare**: Primary broadcast block proposal
  2. **Prepare**: Replicas verify và broadcast prepare messages
  3. **Commit**: Sau khi nhận đủ 2f+1 prepare messages, broadcast commit
  4. **Execute**: Sau khi nhận đủ 2f+1 commit messages, thêm block vào blockchain
- **Block Structure**: Bao gồm `block_height`, `previous_hash`, `block_hash`, `timestamp`, `data`
- **Byzantine Fault Simulation**: Hỗ trợ mô phỏng các node độc hại với nhiều loại hành vi khác nhau

## Cấu trúc thư mục

```
pBFT/
├── pbft.proto           # Protocol Buffers definition
├── pbft_node.py         # Core pBFT implementation
├── pbft_server.py       # Server để chạy pBFT nodes
├── pbft_client.py       # CLI client để tương tác với cluster
└── README.md            # File này
```

## Cài đặt

### 1. Generate gRPC code

```bash
cd pBFT
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. pbft.proto
```

Lệnh này sẽ tạo ra:
- `pbft_pb2.py` - Message definitions
- `pbft_pb2_grpc.py` - Service stubs

### 2. Cài đặt dependencies

```bash
pip install grpcio grpcio-tools
```

## Chạy hệ thống

### Bước 1: Start 5 nodes (mỗi node trên 1 terminal riêng)

**Node 1 (Primary):**
```bash
python pbft_server.py --id node1 --port 6001 --primary
```

**Node 2-5 (Replicas):**
```bash
python pbft_server.py --id node2 --port 6002
python pbft_server.py --id node3 --port 6003
python pbft_server.py --id node4 --port 6004
python pbft_server.py --id node5 --port 6005
```

**Lưu ý**: 
- Node1 được chỉ định là primary với flag `--primary`
- Ports: 6001-6005 (khác với RAFT để tránh conflict)

### Bước 2: Chạy client

```bash
python pbft_client.py
```

## Sử dụng Client

### Các lệnh cơ bản

```bash
# Tìm primary node
> primary

# Submit một block mới
> submit "Transaction 1"
> submit "Alice sends 10 BTC to Bob"

# Xem blockchain
> blockchain          # Xem blockchain của node 1
> blockchain 3        # Xem blockchain của node 3

# Xem status của tất cả nodes
> status

# Help
> help

# Thoát
> exit
```

### Byzantine Fault Testing

#### 1. Silent Node (Node không phản hồi)

```bash
# Set node 3 thành silent mode
> malicious 3 silent

# Submit block - sẽ thấy node 3 không phản hồi
> submit "Test with silent node"

# Disable malicious mode
> honest 3
```

#### 2. Wrong Hash Attack (Node gửi hash sai)

```bash
# Set node 2 gửi hash sai
> malicious 2 wrong_hash

# Submit block - node 2 sẽ gửi hash sai nhưng consensus vẫn thành công
> submit "Test with wrong hash"

# Kiểm tra blockchain - block vẫn được commit chính xác
> blockchain

# Disable malicious mode
> honest 2
```

#### 3. Test với nhiều malicious nodes

```bash
# Set 2 nodes thành malicious (vẫn < f+1 = 2)
> malicious 2 silent
> malicious 3 wrong_hash

# Submit block - vẫn thành công vì chỉ có 2 malicious nodes
> submit "Test with 2 malicious nodes"

# Set thêm node thứ 3 (>= f+1 = 2) - consensus sẽ fail
> malicious 4 silent
> submit "This should fail"
```

## Kiến trúc pBFT

### State Machine

Mỗi `PBFTNode` duy trì:

**pBFT State:**
- `view_number`: View hiện tại (cho view change)
- `sequence_number`: Sequence number của block tiếp theo
- `is_primary`: Node có phải primary không
- `primary_id`: ID của primary node

**Blockchain State:**
- `blockchain[]`: List các blocks đã commit
- `pending_block`: Block đang trong quá trình consensus

**Message Logs:**
- `pre_prepare_log{}`: Log các pre-prepare messages
- `prepare_log{}`: Log các prepare messages (theo sequence và hash)
- `commit_log{}`: Log các commit messages (theo sequence và hash)

### Three-Phase Protocol Flow

```
Client → Primary: ClientSubmitBlock(data)
    ↓
Primary → All Replicas: PrePrepare(block)
    ↓
Each Replica → All Nodes: Prepare(block_hash)
    ↓
[Wait for 2f+1 Prepare messages]
    ↓
Each Node → All Nodes: Commit(block_hash)
    ↓
[Wait for 2f+1 Commit messages]
    ↓
Execute: Add block to blockchain
```

### Byzantine Fault Tolerance

**Quorum Requirements:**
- **Pre-prepare**: Chỉ primary gửi
- **Prepare**: Cần 2f+1 messages (bao gồm cả node tự gửi)
- **Commit**: Cần 2f+1 messages

**Với 5 nodes (f=1):**
- Cần 3 nodes đồng ý (2*1+1 = 3)
- Có thể chịu được 1 node Byzantine
- Nếu 2+ nodes Byzantine → consensus fail

### Block Structure

```protobuf
message Block {
  int32 block_height;      // Chiều cao block
  string previous_hash;    // Hash của block trước
  string block_hash;       // Hash của block này
  int64 timestamp;         // Timestamp
  string data;             // Dữ liệu/transaction
  int32 view_number;       // pBFT view number
  int32 sequence_number;   // pBFT sequence number
}
```

**Hash Computation:**
```python
hash = SHA256(data + previous_hash + block_height)
```

## Testing Scenarios

### Scenario 1: Normal Operation

```bash
# Start all 5 nodes
# Run client
> status                          # Verify all nodes online
> submit "Block 1"                # Submit first block
> blockchain                      # Verify block committed
> submit "Block 2"                # Submit second block
> blockchain                      # Verify chain has 3 blocks (genesis + 2)
```

### Scenario 2: Single Byzantine Node

```bash
> malicious 3 silent              # Set node 3 silent
> submit "Test Byzantine"         # Should succeed (4 honest nodes)
> status                          # Verify node 3 is malicious
> blockchain 1                    # Check blockchain on honest node
> blockchain 3                    # Check blockchain on malicious node
> honest 3                        # Restore node 3
```

### Scenario 3: Multiple Byzantine Nodes (At Threshold)

```bash
> malicious 2 wrong_hash
> malicious 3 silent
> submit "At threshold"           # Should still work (3 honest nodes)
> malicious 4 silent              # Now only 2 honest nodes
> submit "Should fail"            # Consensus will fail
```

### Scenario 4: Primary is Byzantine

```bash
> malicious 1 wrong_hash          # Primary sends wrong hash
> submit "Byzantine primary"      # Replicas will reject
# Note: View change not implemented yet, so this will fail
```

## So sánh với RAFT

| Aspect | RAFT | pBFT |
|--------|------|------|
| **Fault Model** | Crash faults only | Byzantine faults |
| **Fault Tolerance** | f failures in 2f+1 nodes | f Byzantine in 3f+1 nodes |
| **Leader** | Single leader (elected) | Primary (fixed/rotated) |
| **Consensus Phases** | 2 (AppendEntries, Commit) | 3 (Pre-prepare, Prepare, Commit) |
| **Message Complexity** | O(n) | O(n²) |
| **Use Case** | Distributed systems | Blockchain, untrusted environments |
| **Performance** | Faster | Slower (more messages) |

## Hạn chế và cải tiến

### Hạn chế hiện tại

1. **No View Change**: Chưa implement view change khi primary fail
2. **No Checkpointing**: Chưa có garbage collection cho message logs
3. **Simplified Signatures**: Dùng node_id thay vì cryptographic signatures
4. **No Persistence**: State chỉ lưu trong memory
5. **Fixed Primary**: Primary được chỉ định lúc start, không rotate

### Cải tiến có thể làm

1. **View Change Protocol**: Cho phép thay primary khi primary fail
2. **Checkpointing**: Định kỳ checkpoint và xóa old logs
3. **Real Signatures**: Sử dụng RSA/ECDSA signatures
4. **Persistence**: Lưu blockchain và state vào disk
5. **Dynamic Membership**: Thêm/xóa nodes động
6. **Optimizations**: Batching, pipelining requests

## Tham khảo

- [Practical Byzantine Fault Tolerance (Castro & Liskov, 1999)](http://pmg.csail.mit.edu/papers/osdi99.pdf)
- [pBFT Explained](https://medium.com/coinmonks/pbft-understanding-the-algorithm-b7a7869650ae)

## Troubleshooting

**Problem**: `ModuleNotFoundError: No module named 'pbft_pb2'`
- **Solution**: Chạy lệnh generate gRPC code (xem phần Cài đặt)

**Problem**: Consensus không hoàn thành
- **Solution**: 
  - Kiểm tra tất cả 5 nodes đang chạy
  - Kiểm tra không có quá f nodes malicious
  - Xem logs để debug

**Problem**: Port already in use
- **Solution**: Kill process đang dùng port hoặc đổi port trong code

## License

Educational project for Blockchain course at HCMUS.
