import grpc
import raft_pb2
import raft_pb2_grpc

# ===== Danh sách địa chỉ của 5 node trong cluster =====
# Client sẽ chỉ cần gọi đến địa chỉ, không cần biết node_id
ADDRESSES = [
    "localhost:5001",
    "localhost:5002",
    "localhost:5003",
    "localhost:5004",
    "localhost:5005",
]

# ===== Hàm tiện ích: tạo stub để gọi RPC =====
def get_stub(addr):
    channel = grpc.insecure_channel(addr)
    return raft_pb2_grpc.RaftStub(channel)

# ===== Hàm tìm leader =====
# Client thử gọi ClientGet với key "__ping__"
# Node nào trả lời thành công → leader
def find_leader():
    for addr in ADDRESSES:
        try:
            stub = get_stub(addr)
            stub.ClientGet(
                raft_pb2.ClientGetRequest(key="__ping__"),
                timeout=1
            )
            print(f"[CLIENT] Leader found at {addr}")
            return addr
        except:
            continue

    print("[CLIENT] No leader found")
    return None

# ===== Hàm gửi lệnh set (ghi key=value) =====
def set_value(key, value):
    leader = find_leader()
    if not leader:
        return

    stub = get_stub(leader)
    resp = stub.ClientSet(
        raft_pb2.ClientSetRequest(
            key=key,
            value=str(value)   # gRPC proto khai báo value là string → ép kiểu
        )
    )

    print(f"[CLIENT] SET {key}={value} success={resp.success}")

# ===== Hàm gửi lệnh get (lấy giá trị key) =====
def get_value(key):
    leader = find_leader()
    if not leader:
        return

    stub = get_stub(leader)
    resp = stub.ClientGet(
        raft_pb2.ClientGetRequest(key=key)
    )

    if resp.found:
        print(f"[CLIENT] GET {key}={resp.value}")
    else:
        print(f"[CLIENT] GET {key} not found")

# ===== In hướng dẫn sử dụng CLI =====
def print_help():
    print("""
Commands:
  getleader          # Tìm leader hiện tại
  set <key> <value>  # Ghi giá trị key=value
  get <key>          # Đọc giá trị key
  exit               # Thoát client
""")

# ===== Main CLI =====
if __name__ == "__main__":
    print("RAFT Client CLI")
    print_help()

    # Vòng lặp đọc lệnh từ người dùng
    while True:
        try:
            cmd = input("> ").strip().split()  # đọc lệnh và tách thành danh sách
        except KeyboardInterrupt:
            break  # Ctrl+C thoát

        if not cmd:
            continue

        if cmd[0] == "exit":
            break

        elif cmd[0] == "getleader":
            find_leader()  # tìm leader và in ra

        elif cmd[0] == "set":
            if len(cmd) != 3:
                print("Usage: set <key> <value>")
                continue
            set_value(cmd[1], cmd[2])  # gửi lệnh set

        elif cmd[0] == "get":
            if len(cmd) != 2:
                print("Usage: get <key>")
                continue
            get_value(cmd[1])  # gửi lệnh get

        else:
            print("Unknown command")
            print_help()  # in hướng dẫn nếu lệnh không hợp lệ
