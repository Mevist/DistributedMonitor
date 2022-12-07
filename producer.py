import monitor2
import sys
from ports_file import PORTS

monitor_obj = monitor2.Monitor(PORTS, int(sys.argv[1]), int(sys.argv[2]))


max_val = 10000
buffer = 5
current_val = 0


while max_val > current_val:
    if monitor_obj.enter_cs():
        if 0 <= len(monitor_obj.data) < buffer:
            current_val = monitor_obj.last_value + 1
            monitor_obj.add_data(current_val)
        monitor_obj.leave_cs()

monitor_obj.stop_all()
print("Work ended here is result:", monitor_obj.data)
