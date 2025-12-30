import grpc
import pbft_pb2
import pbft_pb2_grpc
import time

# ===== Node addresses =====
ADDRESSES = [
    "localhost:6001",
    "localhost:6002",
    "localhost:6003",
    "localhost:6004",
    "localhost:6005",
]


def get_stub(addr):
    """Create gRPC stub for a node"""
    channel = grpc.insecure_channel(addr)
    return pbft_pb2_grpc.PBFTStub(channel)


def find_primary():
    """Find the primary node"""
    for addr in ADDRESSES:
        try:
            stub = get_stub(addr)
            status = stub.GetNodeStatus(pbft_pb2.Empty(), timeout=1)
            if status.is_primary:
                print(f"[CLIENT] Primary found: {status.node_id} at {addr}")
                return addr, status.node_id
        except Exception as e:
            continue
    
    print("[CLIENT] No primary found")
    return None, None


def submit_block(data):
    """Submit a new block to the primary"""
    primary_addr, primary_id = find_primary()
    if not primary_addr:
        print("[CLIENT] Cannot submit block: no primary available")
        return
    
    try:
        stub = get_stub(primary_addr)
        resp = stub.ClientSubmitBlock(
            pbft_pb2.ClientBlockRequest(data=data),
            timeout=5
        )
        
        if resp.success:
            print(f"[CLIENT] ✓ Block submitted successfully")
            print(f"[CLIENT]   Message: {resp.message}")
            print(f"[CLIENT]   Block height: {resp.block_height}")
            print(f"[CLIENT]   Waiting for consensus...")
            time.sleep(2)  # Wait for consensus to complete
        else:
            print(f"[CLIENT] ✗ Failed to submit block: {resp.message}")
    except Exception as e:
        print(f"[CLIENT] Error submitting block: {e}")


def get_blockchain(node_addr=None):
    """Get blockchain from a node"""
    if node_addr is None:
        node_addr = ADDRESSES[0]
    
    try:
        stub = get_stub(node_addr)
        resp = stub.GetBlockchain(pbft_pb2.Empty(), timeout=2)
        
        print(f"\n[CLIENT] Blockchain from {node_addr} (length: {resp.chain_length})")
        print("=" * 80)
        for block in resp.blocks:
            print(f"Block #{block.block_height}")
            print(f"  Hash: {block.block_hash[:16]}...")
            print(f"  Previous: {block.previous_hash[:16]}...")
            print(f"  Data: {block.data}")
            print(f"  Timestamp: {block.timestamp}")
            print(f"  View: {block.view_number}, Seq: {block.sequence_number}")
            print("-" * 80)
    except Exception as e:
        print(f"[CLIENT] Error getting blockchain: {e}")


def get_all_statuses():
    """Get status from all nodes"""
    print("\n[CLIENT] Node Statuses:")
    print("=" * 80)
    for i, addr in enumerate(ADDRESSES, 1):
        try:
            stub = get_stub(addr)
            status = stub.GetNodeStatus(pbft_pb2.Empty(), timeout=1)
            
            role = "PRIMARY" if status.is_primary else "REPLICA"
            malicious = f"⚠ MALICIOUS ({status.malicious_type})" if status.is_malicious else "✓ Honest"
            
            print(f"Node {i} ({status.node_id}) - {addr}")
            print(f"  Role: {role}")
            print(f"  View: {status.view_number}, Sequence: {status.current_sequence}")
            print(f"  Blockchain height: {status.blockchain_height}")
            print(f"  Status: {malicious}")
            print("-" * 80)
        except Exception as e:
            print(f"Node {i} - {addr}")
            print(f"  Status: ✗ OFFLINE or UNREACHABLE")
            print("-" * 80)


def set_malicious(node_num, malicious_type):
    """
    Set a node to behave maliciously
    
    Args:
        node_num: Node number (1-5)
        malicious_type: Type of malicious behavior
            - silent: Don't respond to messages
            - wrong_hash: Send incorrect hashes
    """
    if node_num < 1 or node_num > len(ADDRESSES):
        print(f"[CLIENT] Invalid node number: {node_num}")
        return
    
    addr = ADDRESSES[node_num - 1]
    
    try:
        stub = get_stub(addr)
        resp = stub.SetMaliciousBehavior(
            pbft_pb2.MaliciousConfigRequest(
                enable_malicious=True,
                malicious_type=malicious_type
            ),
            timeout=1
        )
        
        if resp.success:
            print(f"[CLIENT] ✓ Node {node_num} set to malicious mode: {malicious_type}")
            print(f"[CLIENT]   {resp.message}")
        else:
            print(f"[CLIENT] ✗ Failed to set malicious mode")
    except Exception as e:
        print(f"[CLIENT] Error: {e}")


def disable_malicious(node_num):
    """Disable malicious behavior on a node"""
    if node_num < 1 or node_num > len(ADDRESSES):
        print(f"[CLIENT] Invalid node number: {node_num}")
        return
    
    addr = ADDRESSES[node_num - 1]
    
    try:
        stub = get_stub(addr)
        resp = stub.SetMaliciousBehavior(
            pbft_pb2.MaliciousConfigRequest(
                enable_malicious=False,
                malicious_type=""
            ),
            timeout=1
        )
        
        if resp.success:
            print(f"[CLIENT] ✓ Node {node_num} malicious mode disabled")
        else:
            print(f"[CLIENT] ✗ Failed to disable malicious mode")
    except Exception as e:
        print(f"[CLIENT] Error: {e}")


def print_help():
    """Print help message"""
    print("""
pBFT Client Commands:
  primary                      - Find the primary node
  submit <data>                - Submit a new block with data
  blockchain [node_num]        - Get blockchain (default: node 1)
  status                       - Get status of all nodes
  malicious <node_num> <type>  - Set node to malicious mode
                                 Types: silent, wrong_hash
  honest <node_num>            - Disable malicious mode on node
  help                         - Show this help
  exit                         - Exit client

Examples:
  submit "Transaction 1"
  blockchain 2
  malicious 3 wrong_hash
  honest 3
""")


if __name__ == "__main__":
    print("=" * 80)
    print("pBFT Client CLI")
    print("=" * 80)
    print_help()
    
    while True:
        try:
            cmd = input("> ").strip().split(maxsplit=1)
        except KeyboardInterrupt:
            print("\n[CLIENT] Exiting...")
            break
        
        if not cmd:
            continue
        
        command = cmd[0].lower()
        
        if command == "exit":
            break
        
        elif command == "help":
            print_help()
        
        elif command == "primary":
            find_primary()
        
        elif command == "submit":
            if len(cmd) < 2:
                print("Usage: submit <data>")
                continue
            submit_block(cmd[1])
        
        elif command == "blockchain":
            if len(cmd) == 2:
                try:
                    node_num = int(cmd[1])
                    if 1 <= node_num <= len(ADDRESSES):
                        get_blockchain(ADDRESSES[node_num - 1])
                    else:
                        print(f"Invalid node number. Use 1-{len(ADDRESSES)}")
                except ValueError:
                    print("Invalid node number")
            else:
                get_blockchain()
        
        elif command == "status":
            get_all_statuses()
        
        elif command == "malicious":
            if len(cmd) < 2:
                print("Usage: malicious <node_num> <type>")
                print("Types: silent, wrong_hash")
                continue
            
            parts = cmd[1].split()
            if len(parts) != 2:
                print("Usage: malicious <node_num> <type>")
                continue
            
            try:
                node_num = int(parts[0])
                malicious_type = parts[1]
                set_malicious(node_num, malicious_type)
            except ValueError:
                print("Invalid node number")
        
        elif command == "honest":
            if len(cmd) < 2:
                print("Usage: honest <node_num>")
                continue
            
            try:
                node_num = int(cmd[1])
                disable_malicious(node_num)
            except ValueError:
                print("Invalid node number")
        
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")
