"""
pBFT Server
Starts a pBFT node with gRPC server
"""

import grpc
import argparse
from concurrent import futures

import pbft_pb2_grpc
from pbft_node import PBFTNode


def serve(node_id, port, is_primary=False):
    """
    Start a pBFT node
    
    Args:
        node_id: Node identifier (node1, node2, ...)
        port: Port to listen on
        is_primary: Whether this node is the primary (leader)
    """
    # All nodes in the network
    all_nodes = {
        "node1": "localhost:6001",
        "node2": "localhost:6002",
        "node3": "localhost:6003",
        "node4": "localhost:6004",
        "node5": "localhost:6005",
    }
    
    # Peers = all nodes except self
    peers = {k: v for k, v in all_nodes.items() if k != node_id}
    
    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pbft_pb2_grpc.add_PBFTServicer_to_server(
        PBFTNode(node_id, peers, is_primary),
        server
    )
    
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    
    role = "PRIMARY" if is_primary else "REPLICA"
    print(f"[{node_id}] pBFT {role} running on port {port}")
    print(f"[{node_id}] Press Ctrl+C to stop")
    
    server.wait_for_termination()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a pBFT node")
    parser.add_argument("--id", required=True, help="Node ID (node1, node2, ...)")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--primary", action="store_true", help="Set this node as primary")
    args = parser.parse_args()
    
    serve(args.id, args.port, args.primary)
