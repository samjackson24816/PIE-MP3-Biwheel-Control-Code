sudo apt update
sudo apt install -y python3-flask python3-opencv v4l-utils

nohup python3 test_stream.py > stream.log 2>&1 &
