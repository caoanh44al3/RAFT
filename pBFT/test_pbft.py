"""
pBFT Testing Script
Automated tests for pBFT implementation
"""

import time
import subprocess
import sys


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_normal_consensus():
    """Test normal consensus with all honest nodes"""
    print_section("TEST 1: Normal Consensus")
    print("This test verifies that blocks can be committed with all honest nodes.")
    print("\nSteps:")
    print("1. Start all 5 nodes")
    print("2. Submit 3 blocks")
    print("3. Verify blockchain on all nodes")
    print("\nExpected: All blocks committed successfully on all nodes")
    print("\nManual verification required - check that:")
    print("- All nodes show the same blockchain")
    print("- Blockchain has 4 blocks (genesis + 3 submitted)")


def test_single_byzantine():
    """Test with single Byzantine node"""
    print_section("TEST 2: Single Byzantine Node")
    print("This test verifies Byzantine fault tolerance with 1 malicious node.")
    print("\nSteps:")
    print("1. Set node 3 to 'silent' mode")
    print("2. Submit a block")
    print("3. Verify consensus still succeeds")
    print("\nExpected: Block committed despite 1 Byzantine node (f=1)")
    print("\nClient commands:")
    print("  > malicious 3 silent")
    print("  > submit \"Test with 1 Byzantine\"")
    print("  > blockchain")
    print("  > status")


def test_wrong_hash_attack():
    """Test wrong hash Byzantine attack"""
    print_section("TEST 3: Wrong Hash Attack")
    print("This test verifies that wrong hashes are detected and ignored.")
    print("\nSteps:")
    print("1. Set node 2 to 'wrong_hash' mode")
    print("2. Submit a block")
    print("3. Verify correct block is committed")
    print("\nExpected: Honest nodes ignore wrong hash, commit correct block")
    print("\nClient commands:")
    print("  > malicious 2 wrong_hash")
    print("  > submit \"Test wrong hash\"")
    print("  > blockchain")
    print("  > honest 2")


def test_threshold_byzantine():
    """Test at Byzantine threshold"""
    print_section("TEST 4: At Byzantine Threshold (f nodes)")
    print("This test verifies behavior at the Byzantine threshold.")
    print("\nSteps:")
    print("1. Set 1 node to malicious (at threshold f=1)")
    print("2. Submit a block")
    print("3. Verify consensus still works")
    print("\nExpected: Consensus succeeds with exactly f Byzantine nodes")
    print("\nClient commands:")
    print("  > malicious 3 silent")
    print("  > submit \"At threshold\"")
    print("  > status")


def test_beyond_threshold():
    """Test beyond Byzantine threshold"""
    print_section("TEST 5: Beyond Byzantine Threshold (>f nodes)")
    print("This test verifies that consensus fails with too many Byzantine nodes.")
    print("\nSteps:")
    print("1. Set 2 nodes to malicious (beyond threshold f=1)")
    print("2. Submit a block")
    print("3. Verify consensus fails")
    print("\nExpected: Consensus fails (cannot get 2f+1 = 3 honest responses)")
    print("\nClient commands:")
    print("  > malicious 2 silent")
    print("  > malicious 3 silent")
    print("  > submit \"Should fail\"")
    print("  > status")


def test_byzantine_primary():
    """Test with Byzantine primary"""
    print_section("TEST 6: Byzantine Primary")
    print("This test shows what happens when the primary is Byzantine.")
    print("\nSteps:")
    print("1. Set node 1 (primary) to 'wrong_hash' mode")
    print("2. Submit a block")
    print("3. Observe that replicas reject the block")
    print("\nExpected: Consensus fails (view change needed, not implemented)")
    print("\nClient commands:")
    print("  > malicious 1 wrong_hash")
    print("  > submit \"Byzantine primary\"")
    print("\nNote: View change is not implemented, so this will fail.")


def test_recovery():
    """Test recovery from Byzantine behavior"""
    print_section("TEST 7: Recovery from Byzantine Behavior")
    print("This test verifies that nodes can recover after being Byzantine.")
    print("\nSteps:")
    print("1. Set node 3 to malicious")
    print("2. Submit a block (should succeed)")
    print("3. Restore node 3 to honest")
    print("4. Submit another block")
    print("5. Verify both blocks committed")
    print("\nExpected: Node 3 participates normally after recovery")
    print("\nClient commands:")
    print("  > malicious 3 silent")
    print("  > submit \"Block 1\"")
    print("  > honest 3")
    print("  > submit \"Block 2\"")
    print("  > blockchain")


def print_setup_instructions():
    """Print setup instructions"""
    print_section("pBFT Testing Guide")
    print("This script provides test scenarios for the pBFT implementation.")
    print("\nPREREQUISITES:")
    print("1. Generate gRPC code:")
    print("   cd pBFT")
    print("   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. pbft.proto")
    print("\n2. Start 5 nodes in separate terminals:")
    print("   Terminal 1: python pbft_server.py --id node1 --port 6001 --primary")
    print("   Terminal 2: python pbft_server.py --id node2 --port 6002")
    print("   Terminal 3: python pbft_server.py --id node3 --port 6003")
    print("   Terminal 4: python pbft_server.py --id node4 --port 6004")
    print("   Terminal 5: python pbft_server.py --id node5 --port 6005")
    print("\n3. Start client in another terminal:")
    print("   python pbft_client.py")
    print("\n4. Run tests manually using the client commands shown below.")


def main():
    """Main test runner"""
    print_setup_instructions()
    
    # Print all test scenarios
    test_normal_consensus()
    test_single_byzantine()
    test_wrong_hash_attack()
    test_threshold_byzantine()
    test_beyond_threshold()
    test_byzantine_primary()
    test_recovery()
    
    print_section("Summary")
    print("Byzantine Fault Tolerance Properties:")
    print(f"  Total nodes: 5")
    print(f"  f (max Byzantine): 1")
    print(f"  Quorum (2f+1): 3")
    print(f"\nKey Insights:")
    print("  - Can tolerate 1 Byzantine node")
    print("  - Requires 3+ honest nodes for consensus")
    print("  - Wrong hashes are detected and ignored")
    print("  - Silent nodes don't prevent consensus (if ≤f)")
    print("  - Byzantine primary requires view change (not implemented)")
    
    print("\n" + "=" * 80)
    print("Testing complete! Review the results above.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
