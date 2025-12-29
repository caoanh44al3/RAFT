# RAFT
RAFT in Blockchain

## Install requirements
pip install -r requirements.txt

## gRPC code generation (run once)
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto

## Run each node on separate terminal
python server.py --id node1 --port 5001
python server.py --id node2 --port 5002
python server.py --id node3 --port 5003
python server.py --id node4 --port 5004
python server.py --id node5 --port 5005

## Run client
python client.py
(getleader, set, get, exit)

