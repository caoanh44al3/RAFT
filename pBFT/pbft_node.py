import time
import threading
import hashlib
import grpc
from collections import defaultdict

import pbft_pb2
import pbft_pb2_grpc


class PBFTNode(pbft_pb2_grpc.PBFTServicer):
    """
    Practical Byzantine Fault Tolerance Node Implementation
    
    Implements the three-phase commit protocol:
    1. Pre-prepare: Primary broadcasts block proposal
    2. Prepare: Replicas verify and broadcast prepare messages
    3. Commit: After 2f+1 prepare messages, broadcast commit
    4. Execute: After 2f+1 commit messages, add block to chain
    
    Byzantine fault tolerance: Can tolerate f faulty nodes in 3f+1 total nodes
    For 5 nodes: f=1, can tolerate 1 Byzantine node
    """
    
    def __init__(self, node_id, peers, is_primary=False):
        """
        node_id: ID của node (node1, node2, ...)
        peers: dict {peer_id: "host:port"}
        is_primary: True nếu node này là primary ban đầu
        """
        self.node_id = node_id
        self.peers = peers
        self.total_nodes = len(peers) + 1  # Include self
        self.f = (self.total_nodes - 1) // 3  # Byzantine fault tolerance
        
        # ===== pBFT State =====
        self.view_number = 0
        self.sequence_number = 0
        self.is_primary = is_primary
        self.primary_id = node_id if is_primary else None
        
        # ===== Blockchain State =====
        self.blockchain = []  # List of committed blocks
        self.pending_block = None  # Block in consensus
        
        # ===== Message Logs (for each sequence number) =====
        # Format: {seq_num: {block_hash: [node_ids]}}
        self.pre_prepare_log = {}
        self.prepare_log = defaultdict(lambda: defaultdict(list))
        self.commit_log = defaultdict(lambda: defaultdict(list))
        
        # ===== Byzantine Fault Simulation =====
        self.is_malicious = False
        self.malicious_type = None  # "silent", "wrong_hash", "double_send", "random"
        
        # ===== Synchronization =====
        self.lock = threading.Lock()
        
        # Initialize genesis block
        self._create_genesis_block()
        
        print(f"[{self.node_id}] pBFT node initialized (primary={self.is_primary}, f={self.f})")
    
    def _create_genesis_block(self):
        """Create the genesis block (block 0)"""
        genesis = pbft_pb2.Block(
            block_height=0,
            previous_hash="0" * 64,
            block_hash=self._compute_hash("genesis", "0" * 64, 0),
            timestamp=int(time.time()),
            data="Genesis Block",
            view_number=0,
            sequence_number=0
        )
        self.blockchain.append(genesis)
        print(f"[{self.node_id}] Genesis block created: {genesis.block_hash[:8]}...")
    
    def _compute_hash(self, data, prev_hash, height):
        """Compute SHA-256 hash for a block"""
        content = f"{data}{prev_hash}{height}".encode()
        return hashlib.sha256(content).hexdigest()
    
    def _get_last_block(self):
        """Get the last committed block"""
        return self.blockchain[-1] if self.blockchain else None
    
    def _verify_block(self, block):
        """Verify block integrity"""
        last_block = self._get_last_block()
        
        # Check height
        if block.block_height != last_block.block_height + 1:
            return False, f"Invalid height: expected {last_block.block_height + 1}, got {block.block_height}"
        
        # Check previous hash
        if block.previous_hash != last_block.block_hash:
            return False, f"Invalid previous hash"
        
        # Verify hash computation
        expected_hash = self._compute_hash(block.data, block.previous_hash, block.block_height)
        if block.block_hash != expected_hash:
            return False, f"Invalid block hash"
        
        return True, "Block valid"
    
    # =====================================================
    # ================ PRE-PREPARE PHASE ==================
    # =====================================================
    
    def PrePrepare(self, request, context):
        """
        Replica receives Pre-prepare message from primary
        Validates and moves to Prepare phase
        """
        with self.lock:
            # Byzantine behavior: Silent node
            if self.is_malicious and self.malicious_type == "silent":
                print(f"[{self.node_id}] MALICIOUS: Ignoring pre-prepare")
                return pbft_pb2.PrePrepareResponse(
                    accepted=False,
                    node_id=self.node_id,
                    reason="Silent node"
                )
            
            # Verify view number
            if request.view_number != self.view_number:
                return pbft_pb2.PrePrepareResponse(
                    accepted=False,
                    node_id=self.node_id,
                    reason=f"View mismatch: expected {self.view_number}, got {request.view_number}"
                )
            
            # Verify sequence number
            if request.sequence_number != self.sequence_number + 1:
                return pbft_pb2.PrePrepareResponse(
                    accepted=False,
                    node_id=self.node_id,
                    reason=f"Sequence mismatch"
                )
            
            # Verify block
            valid, reason = self._verify_block(request.block)
            if not valid:
                return pbft_pb2.PrePrepareResponse(
                    accepted=False,
                    node_id=self.node_id,
                    reason=reason
                )
            
            # Store pre-prepare
            self.pre_prepare_log[request.sequence_number] = request.block
            self.pending_block = request.block
            self.sequence_number = request.sequence_number
            
            print(f"[{self.node_id}] PRE-PREPARE accepted (seq={request.sequence_number}, hash={request.block.block_hash[:8]}...)")
            
            # Move to Prepare phase
            threading.Thread(target=self._broadcast_prepare, args=(request.block,), daemon=True).start()
            
            return pbft_pb2.PrePrepareResponse(
                accepted=True,
                node_id=self.node_id,
                reason="Accepted"
            )
    
    def _broadcast_prepare(self, block):
        """Broadcast Prepare message to all peers"""
        time.sleep(0.1)  # Small delay to simulate network
        
        # Byzantine behavior: Wrong hash
        block_hash = block.block_hash
        if self.is_malicious and self.malicious_type == "wrong_hash":
            block_hash = "0" * 64
            print(f"[{self.node_id}] MALICIOUS: Sending wrong hash in prepare")
        
        prepare_msg = pbft_pb2.PrepareRequest(
            view_number=self.view_number,
            sequence_number=block.sequence_number,
            block_hash=block_hash,
            node_id=self.node_id,
            signature=self.node_id
        )
        
        # Send to all peers
        for peer_id, addr in self.peers.items():
            try:
                channel = grpc.insecure_channel(addr)
                stub = pbft_pb2_grpc.PBFTStub(channel)
                stub.Prepare(prepare_msg, timeout=1)
            except Exception as e:
                print(f"[{self.node_id}] Failed to send prepare to {peer_id}: {e}")
        
        # Also process own prepare
        self.Prepare(prepare_msg, None)
    
    # =====================================================
    # ================== PREPARE PHASE ====================
    # =====================================================
    
    def Prepare(self, request, context):
        """
        Receive Prepare message from replicas
        When 2f+1 prepare messages received, move to Commit phase
        """
        with self.lock:
            # Verify view and sequence
            if request.view_number != self.view_number:
                return pbft_pb2.PrepareResponse(accepted=False, node_id=self.node_id)
            
            if request.sequence_number != self.sequence_number:
                return pbft_pb2.PrepareResponse(accepted=False, node_id=self.node_id)
            
            # Store prepare message
            block_hash = request.block_hash
            if request.node_id not in self.prepare_log[request.sequence_number][block_hash]:
                self.prepare_log[request.sequence_number][block_hash].append(request.node_id)
            
            prepare_count = len(self.prepare_log[request.sequence_number][block_hash])
            
            print(f"[{self.node_id}] PREPARE received from {request.node_id} ({prepare_count}/{2*self.f+1})")
            
            # Check if we have 2f+1 prepare messages (including self)
            if prepare_count >= 2 * self.f + 1:
                # Move to Commit phase
                if self.pending_block and self.pending_block.block_hash == block_hash:
                    threading.Thread(target=self._broadcast_commit, args=(self.pending_block,), daemon=True).start()
            
            return pbft_pb2.PrepareResponse(accepted=True, node_id=self.node_id)
    
    def _broadcast_commit(self, block):
        """Broadcast Commit message to all peers"""
        time.sleep(0.1)
        
        commit_msg = pbft_pb2.CommitRequest(
            view_number=self.view_number,
            sequence_number=block.sequence_number,
            block_hash=block.block_hash,
            node_id=self.node_id,
            signature=self.node_id
        )
        
        # Send to all peers
        for peer_id, addr in self.peers.items():
            try:
                channel = grpc.insecure_channel(addr)
                stub = pbft_pb2_grpc.PBFTStub(channel)
                stub.Commit(commit_msg, timeout=1)
            except Exception as e:
                print(f"[{self.node_id}] Failed to send commit to {peer_id}: {e}")
        
        # Also process own commit
        self.Commit(commit_msg, None)
    
    # =====================================================
    # =================== COMMIT PHASE ====================
    # =====================================================
    
    def Commit(self, request, context):
        """
        Receive Commit message from replicas
        When 2f+1 commit messages received, execute block
        """
        with self.lock:
            # Verify view and sequence
            if request.view_number != self.view_number:
                return pbft_pb2.CommitResponse(accepted=False, node_id=self.node_id)
            
            if request.sequence_number != self.sequence_number:
                return pbft_pb2.CommitResponse(accepted=False, node_id=self.node_id)
            
            # Store commit message
            block_hash = request.block_hash
            if request.node_id not in self.commit_log[request.sequence_number][block_hash]:
                self.commit_log[request.sequence_number][block_hash].append(request.node_id)
            
            commit_count = len(self.commit_log[request.sequence_number][block_hash])
            
            print(f"[{self.node_id}] COMMIT received from {request.node_id} ({commit_count}/{2*self.f+1})")
            
            # Check if we have 2f+1 commit messages
            if commit_count >= 2 * self.f + 1:
                # Execute: Add block to blockchain
                if self.pending_block and self.pending_block.block_hash == block_hash:
                    self._execute_block(self.pending_block)
            
            return pbft_pb2.CommitResponse(accepted=True, node_id=self.node_id)
    
    def _execute_block(self, block):
        """Execute block: Add to blockchain"""
        # Check if already executed
        if any(b.block_hash == block.block_hash for b in self.blockchain):
            return
        
        self.blockchain.append(block)
        self.pending_block = None
        
        print(f"[{self.node_id}] ✓ BLOCK COMMITTED: height={block.block_height}, hash={block.block_hash[:8]}..., data='{block.data}'")
        print(f"[{self.node_id}] Blockchain length: {len(self.blockchain)}")
    
    # =====================================================
    # ==================== CLIENT API =====================
    # =====================================================
    
    def ClientSubmitBlock(self, request, context):
        """
        Client submits a new block/transaction
        Only primary can initiate consensus
        """
        with self.lock:
            if not self.is_primary:
                return pbft_pb2.ClientBlockResponse(
                    success=False,
                    message=f"Not primary. Primary is {self.primary_id}",
                    block_height=-1
                )
            
            # Create new block
            last_block = self._get_last_block()
            new_block = pbft_pb2.Block(
                block_height=last_block.block_height + 1,
                previous_hash=last_block.block_hash,
                block_hash="",  # Will be computed
                timestamp=int(time.time()),
                data=request.data,
                view_number=self.view_number,
                sequence_number=self.sequence_number + 1
            )
            
            # Compute hash
            new_block.block_hash = self._compute_hash(
                new_block.data,
                new_block.previous_hash,
                new_block.block_height
            )
            
            # Byzantine behavior: Wrong hash
            if self.is_malicious and self.malicious_type == "wrong_hash":
                new_block.block_hash = "malicious_hash_" + new_block.block_hash[:40]
                print(f"[{self.node_id}] MALICIOUS: Creating block with wrong hash")
            
            self.sequence_number += 1
            self.pending_block = new_block
            
            print(f"[{self.node_id}] PRIMARY: Initiating consensus for block {new_block.block_height}")
            
        # Broadcast Pre-prepare
        threading.Thread(target=self._broadcast_pre_prepare, args=(new_block,), daemon=True).start()
        
        return pbft_pb2.ClientBlockResponse(
            success=True,
            message="Consensus initiated",
            block_height=new_block.block_height
        )
    
    def _broadcast_pre_prepare(self, block):
        """Primary broadcasts Pre-prepare message"""
        time.sleep(0.1)
        
        pre_prepare_msg = pbft_pb2.PrePrepareRequest(
            view_number=self.view_number,
            sequence_number=block.sequence_number,
            block=block,
            primary_id=self.node_id,
            signature=self.node_id
        )
        
        # Send to all replicas
        for peer_id, addr in self.peers.items():
            try:
                channel = grpc.insecure_channel(addr)
                stub = pbft_pb2_grpc.PBFTStub(channel)
                resp = stub.PrePrepare(pre_prepare_msg, timeout=2)
                if resp.accepted:
                    print(f"[{self.node_id}] Pre-prepare accepted by {peer_id}")
                else:
                    print(f"[{self.node_id}] Pre-prepare rejected by {peer_id}: {resp.reason}")
            except Exception as e:
                print(f"[{self.node_id}] Failed to send pre-prepare to {peer_id}: {e}")
        
        # Primary also participates in prepare phase
        threading.Thread(target=self._broadcast_prepare, args=(block,), daemon=True).start()
    
    def GetBlockchain(self, request, context):
        """Return the entire blockchain"""
        return pbft_pb2.BlockchainResponse(
            blocks=self.blockchain,
            chain_length=len(self.blockchain)
        )
    
    def GetNodeStatus(self, request, context):
        """Return node status"""
        return pbft_pb2.NodeStatusResponse(
            node_id=self.node_id,
            is_primary=self.is_primary,
            view_number=self.view_number,
            current_sequence=self.sequence_number,
            blockchain_height=len(self.blockchain) - 1,
            is_malicious=self.is_malicious,
            malicious_type=self.malicious_type or "none"
        )
    
    # =====================================================
    # ============= BYZANTINE FAULT SIMULATION ============
    # =====================================================
    
    def SetMaliciousBehavior(self, request, context):
        """
        Configure malicious behavior for testing
        Types:
        - silent: Node doesn't respond to messages
        - wrong_hash: Node sends incorrect block hashes
        - double_send: Node sends conflicting messages (not implemented yet)
        - random: Random malicious behavior
        """
        with self.lock:
            self.is_malicious = request.enable_malicious
            self.malicious_type = request.malicious_type if request.enable_malicious else None
            
            status = "ENABLED" if self.is_malicious else "DISABLED"
            msg = f"Malicious behavior {status}"
            if self.is_malicious:
                msg += f" (type: {self.malicious_type})"
            
            print(f"[{self.node_id}] {msg}")
            
            return pbft_pb2.MaliciousConfigResponse(
                success=True,
                message=msg
            )
