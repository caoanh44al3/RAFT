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

def serve(node_id, port, peers):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServicer_to_server(
        RaftNode(node_id, peers),
        server
    )

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"{node_id} running on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--peers", nargs="*", default=[])

    args = parser.parse_args()

    peers = {
        f"node{i+1}": addr
        for i, addr in enumerate(args.peers)
    }

    serve(args.id, args.port, peers)
