import grpc
import raft_pb2
import raft_pb2_grpc
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--nodes",
    nargs="+",
    required=True,
    help="List of node addresses, e.g. localhost:5001 localhost:5002"
)
args = parser.parse_args()

ADDRESSES = args.nodes

# ===== Hàm tiện ích: tạo stub để gọi RPC =====
def get_stub(addr):
    channel = grpc.insecure_channel(addr)
    return raft_pb2_grpc.RaftStub(channel)

# ===== Hàm tìm leader =====
# Client thử gọi ClientGet với key "__ping__"
# Node nào trả lời thành công → leader
def find_leader():
    # First, try GetLeader RPC which explicitly returns whether the node is leader
    node_map = {
        "node1": "localhost:5001",
        "node2": "localhost:5002",
        "node3": "localhost:5003",
        "node4": "localhost:5004",
        "node5": "localhost:5005",
    }

    for addr in ADDRESSES:
        try:
            stub = get_stub(addr)
            resp = stub.GetLeader(raft_pb2.Empty(), timeout=1)
            if resp.is_leader:
                print(f"[CLIENT] Leader found at {addr}")
                return addr
            # If the node knows who the leader is, resolve and return that address
            if resp.leader_id:
                leader_addr = node_map.get(resp.leader_id)
                if leader_addr:
                    print(f"[CLIENT] Leader found at {leader_addr} || Reported by {addr} ")
                    return leader_addr
        except Exception:
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

# ===== Hàm thiết lập partition (block peer) =====
def set_partition(target_addr, blocked_list):
    stub = get_stub(target_addr)
    try:
        resp = stub.SetPartition(
            raft_pb2.PartitionRequest(blocked_addresses=blocked_list)
        )
        print(f"[CLIENT] Partition set on {target_addr}. Blocked: {blocked_list}")
    except Exception as e:
        print(f"[CLIENT] Error setting partition on {target_addr}: {e}")

# ===== In hướng dẫn sử dụng CLI =====
def print_help():
    print("""
Commands:
  getleader          # Tìm leader hiện tại
  set <key> <value>  # Ghi giá trị key=value
  get <key>          # Đọc giá trị key
  partition <target_port> <blocked_ports...> 
                     # Block các port trên node target. 
                     # VD: partition 5001 5002 5003 (Node 5001 sẽ block 5002 và 5003)
  clear_partition <target_port>
                     # Xóa partition trên node target
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

        elif cmd[0] == "partition":
            if len(cmd) < 3:
                print("Usage: partition <target_port> <blocked_port1> [blocked_port2 ...]")
                continue
            
            target_port = cmd[1]
            blocked_ports = cmd[2:]
            
            # Convert ports to full addresses
            target_addr = f"localhost:{target_port}"
            blocked_addrs = [f"localhost:{p}" for p in blocked_ports]
            
            set_partition(target_addr, blocked_addrs)

        elif cmd[0] == "clear_partition":
            if len(cmd) != 2:
                print("Usage: clear_partition <target_port>")
                continue
            
            target_port = cmd[1]
            target_addr = f"localhost:{target_port}"
            set_partition(target_addr, [])

        else:
            print("Unknown command")
            print_help()  # in hướng dẫn nếu lệnh không hợp lệ
