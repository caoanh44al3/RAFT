"""
File này chỉ có nhiệm vụ:
- Tạo gRPC server
- Gắn RaftNode vào server
"""

import grpc
import argparse
from concurrent import futures

import raft_pb2_grpc
from raft_node import RaftNode


def serve(node_id, port):
    # Danh sách tất cả node
    all_nodes = {
        "node1": "localhost:5001",
        "node2": "localhost:5002",
        "node3": "localhost:5003",
        "node4": "localhost:5004",
        "node5": "localhost:5005",
    }

    # Peer = các node còn lại
    peers = {k: v for k, v in all_nodes.items() if k != node_id}

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServicer_to_server(
        RaftNode(node_id, peers),
        server
    )

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    print(f"{node_id} chạy tại port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    serve(args.id, args.port)
