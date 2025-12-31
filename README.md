# RAFT
RAFT in Blockchain  

## Install requirements
pip install -r requirements.txt  

## gRPC code generation (run once)
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto  

## Run each node on separate terminal
python server.py --id node1 --port 5001 --peers localhost:5002 localhost:5003 localhost:5004 localhost:5005 localhost:5006 localhost:5007  
python server.py --id node2 --port 5002 --peers localhost:5001 localhost:5003 localhost:5004 localhost:5005 localhost:5006 localhost:5007  
python server.py --id node3 --port 5003 --peers localhost:5001 localhost:5002 localhost:5004 localhost:5005 localhost:5006 localhost:5007  
python server.py --id node4 --port 5004 --peers localhost:5001 localhost:5002 localhost:5003 localhost:5005 localhost:5006 localhost:5007  
python server.py --id node5 --port 5005 --peers localhost:5001 localhost:5002 localhost:5003 localhost:5004 localhost:5006 localhost:5007  
python server.py --id node6 --port 5006 --peers localhost:5001 localhost:5002 localhost:5003 localhost:5004 localhost:5005 localhost:5007  
python server.py --id node7 --port 5007 --peers localhost:5001 localhost:5002 localhost:5003 localhost:5004 localhost:5005 localhost:5006  

## Run client  
python client.py --nodes localhost:5001 localhost:5002 localhost:5003 localhost:5004 localhost:5005 localhost:5006 localhost:5007
(getleader, set, get, exit)  

