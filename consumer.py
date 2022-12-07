import sys
import monitor2
from ports_file import PORTS

monitor_obj = monitor2.Monitor(PORTS, int(sys.argv[1]), int(sys.argv[2]))


max_val = 10000
buffer = 5
current_val = 0

while max_val > current_val:
    if monitor_obj.enter_cs():
        if len(monitor_obj.data) > 0:
            current_val = monitor_obj.read_data()
            print(current_val)
        monitor_obj.leave_cs()

monitor_obj.stop_all()
print("Work ended here is result:", monitor_obj.data)
