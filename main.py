from subprocess import Popen

p1 = Popen(["python", "consumer.py", '5555', '0'])
p2 = Popen(["python", "consumer.py", '5556', '0'])
p3 = Popen(["python", "producer.py", '5557', '1'])
p4 = Popen(["python", "producer.py", '5558', '0'])

process_list = [p1, p2, p3, p4]

try:
    [(lambda p: p.wait())(p) for p in process_list]
except KeyboardInterrupt:
    try:
        [(lambda p: p.terminate())(p) for p in process_list]
    except OSError:
       pass
    [(lambda p: p.wait())(p) for p in process_list]
    print("Done")

