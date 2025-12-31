import time
import threading
import random
import grpc

import raft_pb2
import raft_pb2_grpc


FOLLOWER = "FOLLOWER"
CANDIDATE = "CANDIDATE"
LEADER = "LEADER"


class RaftNode(raft_pb2_grpc.RaftServicer):
    def __init__(self, node_id, peers):
        """
        node_id : ID của node (node1, node2, ...)
        peers   : dict {peer_id: "host:port"}
        """
        self.node_id = node_id
        self.peers = peers

        # ===== Persistent state (RAFT) =====
        self.current_term = 0
        self.voted_for = None
        self.log = []  # danh sách LogEntry

        # ===== Volatile state (RAFT) =====
        self.commit_index = -1
        self.last_applied = -1

        # ===== Leader-only volatile state =====
        self.next_index = {}    # peer_id -> next log index
        self.match_index = {}   # peer_id -> highest replicated index

        # ===== Node state =====
        self.state = FOLLOWER
        self.leader_id = None

        # ===== State machine (key-value store) =====
        self.kv_store = {}

        # ===== Heartbeat & election =====
        self.last_heartbeat = time.time()
        self.heartbeat_count = 0

        self.lock = threading.Lock()

        self.start_time = time.time() 
        
        # ===== Fault Simulation =====
        self.blocked_peers = set() # Set of "host:port" to block

        # Start election timeout thread
        threading.Thread(target=self.election_loop, daemon=True).start()

    # =====================================================
    # =============== FAULT SIMULATION ====================
    # =====================================================
    def SetPartition(self, request, context):
        with self.lock:
            self.blocked_peers = set(request.blocked_addresses)
            print(f"[{self.node_id}] Partition set. Blocking: {self.blocked_peers}")
        return raft_pb2.PartitionResponse(success=True)

    # =====================================================
    # =============== ELECTION & HEARTBEAT ================
    # =====================================================

    def election_loop(self):
        """
        Theo dõi timeout, nếu follower quá lâu không nhận heartbeat
        thì trở thành candidate và bắt đầu bầu leader
        """
        while True:
            time.sleep(0.1)

            if time.time() - self.start_time < 10:
                continue # Chờ khởi động ổn định
            with self.lock:
                if self.state == LEADER:
                    continue

                timeout = random.uniform(5, 10)
                if time.time() - self.last_heartbeat < timeout:
                    continue

                # Timeout → start election
                print(f"[{self.node_id}] Election timeout after {timeout:.2f}s, starting election")
                self.state = CANDIDATE
                self.current_term += 1
                self.voted_for = self.node_id
                votes = 1

                print(f"[{self.node_id}] Start election (term {self.current_term})")

            # Gửi RequestVote tới các peer
            for peer_id, addr in self.peers.items():
                if addr in self.blocked_peers:
                    continue
                try:
                    channel = grpc.insecure_channel(addr)
                    stub = raft_pb2_grpc.RaftStub(channel)

                    last_index = len(self.log) - 1
                    last_term = self.log[last_index].term if last_index >= 0 else 0

                    resp = stub.RequestVote(
                        raft_pb2.RequestVoteRequest(
                            term=self.current_term,
                            candidate_id=self.node_id,
                            last_log_index=last_index,
                            last_log_term=last_term,
                        ),
                        timeout=1,
                    )

                    with self.lock:
                        # If peer reports a higher term, step down
                        if resp.term > self.current_term:
                            print(f"[{self.node_id}] Seen higher term {resp.term} from {peer_id}, stepping down")
                            self.current_term = resp.term
                            self.state = FOLLOWER
                            self.voted_for = None
                        elif resp.vote_granted:
                            votes += 1

                except:
                    pass

            with self.lock:
                if votes > (len(self.peers) + 1) // 2:
                    self.become_leader()
                else:
                    print(f"[{self.node_id}] Election failed: got {votes} votes, need >{(len(self.peers) + 1) // 2}")

    def become_leader(self):
        """
        Node trở thành leader
        """
        self.state = LEADER
        self.leader_id = self.node_id

        # Khởi tạo leader state
        for peer_id in self.peers:
            self.next_index[peer_id] = len(self.log)
            self.match_index[peer_id] = -1

        print(f"[{self.node_id}] Become LEADER (term {self.current_term})")

        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    def heartbeat_loop(self):
        """
        Leader gửi heartbeat và replicate log
        """
        while self.state == LEADER:
            self.heartbeat_count += 1
            print(f"[{self.node_id}] HEARTBEAT #{self.heartbeat_count}")

            for peer_id, addr in self.peers.items():
                if addr in self.blocked_peers:
                    continue
                self.send_append_entries(peer_id, addr)

            time.sleep(1)

    # =====================================================
    # ================== APPEND ENTRIES ===================
    # =====================================================

    def send_append_entries(self, peer_id, addr):
        """
        Leader gửi AppendEntries cho follower
        """
        try:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftStub(channel)

            next_idx = self.next_index[peer_id]
            prev_idx = next_idx - 1
            prev_term = self.log[prev_idx].term if prev_idx >= 0 else 0
            entries = self.log[next_idx:]

            resp = stub.AppendEntries(
                raft_pb2.AppendEntriesRequest(
                    term=self.current_term,
                    leader_id=self.node_id,
                    prev_log_index=prev_idx,
                    prev_log_term=prev_term,
                    entries=entries,
                    leader_commit=self.commit_index,
                ),
                timeout=1,
            )

            with self.lock:
                if resp.success:
                    self.match_index[peer_id] = prev_idx + len(entries)
                    self.next_index[peer_id] = self.match_index[peer_id] + 1
                    self.update_commit_index()
                else:
                    self.next_index[peer_id] = max(0, self.next_index[peer_id] - 1)

        except:
            pass

    def AppendEntries(self, request, context):
        """
        Follower nhận heartbeat hoặc log từ leader
        """
        with self.lock:
            # Check partition
            if request.leader_id in self.peers:
                addr = self.peers[request.leader_id]
                if addr in self.blocked_peers:
                    return raft_pb2.AppendEntriesResponse(
                        term=self.current_term, success=False
                    )

            if request.term < self.current_term:
                return raft_pb2.AppendEntriesResponse(
                    term=self.current_term, success=False
                )

            # Update leader info
            self.state = FOLLOWER
            self.leader_id = request.leader_id
            self.current_term = request.term
            self.last_heartbeat = time.time()

            # 1. Check prev_log_index & prev_log_term
            if request.prev_log_index >= 0:
                if request.prev_log_index >= len(self.log):
                    return raft_pb2.AppendEntriesResponse(
                        term=self.current_term, success=False
                    )

                if self.log[request.prev_log_index].term != request.prev_log_term:
                    return raft_pb2.AppendEntriesResponse(
                        term=self.current_term, success=False
                    )

            # 2. Append / overwrite log
            idx = request.prev_log_index + 1
            for entry in request.entries:
                if idx < len(self.log):
                    if self.log[idx].term != entry.term:
                        self.log = self.log[:idx]
                        self.log.append(entry)
                else:
                    self.log.append(entry)
                idx += 1

            # 3. Update commit index
            if request.leader_commit > self.commit_index:
                self.commit_index = min(
                    request.leader_commit, len(self.log) - 1
                )
                self.apply_committed_logs()

            return raft_pb2.AppendEntriesResponse(
                term=self.current_term, success=True
            )

    # =====================================================
    # ================== REQUEST VOTE =====================
    # =====================================================

    def RequestVote(self, request, context):
        """
        Xử lý RequestVote từ candidate
        """
        with self.lock:
            # Check partition
            if request.candidate_id in self.peers:
                addr = self.peers[request.candidate_id]
                if addr in self.blocked_peers:
                    return raft_pb2.RequestVoteResponse(
                        term=self.current_term, vote_granted=False
                    )
            # If the request has a higher term, update our term and reset previous vote
            if request.term > self.current_term:
                print(f"[{self.node_id}] RequestVote with higher term {request.term} (was {self.current_term}); updating term and clearing vote")
                self.current_term = request.term
                self.voted_for = None
                self.state = FOLLOWER

            if request.term < self.current_term:
                print(f"[{self.node_id}] Deny vote to {request.candidate_id}: term {request.term} < {self.current_term}")
                return raft_pb2.RequestVoteResponse(
                    term=self.current_term, vote_granted=False
                )

            if (
                self.voted_for is None
                or self.voted_for == request.candidate_id
            ):
                self.voted_for = request.candidate_id
                # current_term already updated above when necessary
                print(f"[{self.node_id}] Grant vote to {request.candidate_id} (term {request.term})")
                return raft_pb2.RequestVoteResponse(
                    term=self.current_term, vote_granted=True
                )

            print(f"[{self.node_id}] Deny vote to {request.candidate_id}: already voted for {self.voted_for}")
            return raft_pb2.RequestVoteResponse(
                term=self.current_term, vote_granted=False
            )

    # =====================================================
    # =================== COMMIT LOG ======================
    # =====================================================

    def update_commit_index(self):
        """
        Leader commit log khi được replicate trên majority
        """
        for i in range(len(self.log) - 1, self.commit_index, -1):
            count = 1  # leader itself
            for peer in self.match_index:
                if self.match_index[peer] >= i:
                    count += 1

            if (
                count > (len(self.peers) + 1) // 2
                and self.log[i].term == self.current_term
            ):
                self.commit_index = i
                self.apply_committed_logs()
                break

    def apply_committed_logs(self):
        """
        Apply log đã commit vào key-value store
        """
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self.kv_store[entry.key] = entry.value
            print(
                f"[{self.node_id}] COMMIT {entry.key}={entry.value}"
            )

    # =====================================================
    # ===================== CLIENT API ====================
    # =====================================================

    def GetLeader(self, request, context):
        return raft_pb2.LeaderResponse(
            is_leader=self.state == LEADER,
            leader_id=self.leader_id or self.node_id,
        )

    def ClientSet(self, request, context):
        """
        Client gửi SET key=value (chỉ leader xử lý)
        """
        with self.lock:
            if self.state != LEADER:
                return raft_pb2.ClientSetResponse(success=False)

            entry = raft_pb2.LogEntry(
                term=self.current_term,
                key=request.key,
                value=request.value,
            )
            self.log.append(entry)

            print(
                f"[{self.node_id}] RECEIVE CLIENT SET {request.key}={request.value}"
            )

            return raft_pb2.ClientSetResponse(success=True)

    def ClientGet(self, request, context):
        """
        Client GET từ state machine
        """
        if self.state != LEADER:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "Not leader"
            )
        if request.key in self.kv_store:
            return raft_pb2.ClientGetResponse(
                found=True, value=self.kv_store[request.key]
            )
        return raft_pb2.ClientGetResponse(found=False)
