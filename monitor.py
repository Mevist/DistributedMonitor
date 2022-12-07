import time
import zmq
import threading
import json

debug_flag = True
debug_ln_rn = True


class Monitor:
    def __init__(self, ports: list, port_id: int, token: bool):
        self._ports = ports
        self._my_port = int(port_id)
        self._my_port_index = self._ports.index(self._my_port)
        self.pub_context = zmq.Context()
        self._running = False
        self.critical_section = False

        self._token_queue = []
        self.token = token
        self._token_requested = False
        self._rn = [0 for _ in ports]
        self._request_number = 0
        # print(f'IDS: {self._my_port} and {self._my_port_index} and {self._rn[self._my_port_index]} and {self._rn}')
        self.data = 0
        self.json_dict = {
            "sender": self._my_port,
            "receiver": None,
            "action": str,
            "token": bool,
            "ln": [0 for _ in ports],
            "sn": self._request_number,
            "data": [],
            "token_queue": []
        }

        self.max_values = 0
        self.min_values = 0
        self.buffer_values = []
        self.actual_value = 0;

        self._publisher_init()
        self._start_subscribers()
        self._lock = threading.Lock()
        self._cv = threading.Condition()

    def _publisher_init(self):
        self.pub_socket = self.pub_context.socket(zmq.PUB)
        if debug_flag:
            print(f'Binding a publisher to: tcp://*:{self._my_port}')
        self.pub_socket.bind(f'tcp://*:{self._my_port}')
        self._running = True

    def publish(self):
        temp_json = json.dumps(self.json_dict)
        self.pub_socket.send_json(temp_json)

    def _create_dict(self, sender, receiver, action, token, ln, sn, data, token_queue):
        self.json_dict['sender'] = sender if sender is not None else self._my_port
        self.json_dict['receiver'] = receiver
        self.json_dict['action'] = action
        self.json_dict['token'] = token if token is not None else self.token
        self.json_dict['ln'] = ln if ln is not None else self.json_dict['ln']
        self.json_dict['sn'] = sn if sn is not None else self.json_dict['sn']
        self.json_dict['data'] = data if data is not None else self.data
        self.json_dict['token_queue'] = list(token_queue) if token_queue is not None else self.json_dict['token_queue']

    def _check_ln_to_rn(self, requester_id):
        _ln_value = self.json_dict['ln'][requester_id] + 1
        # print(_ln_value, self._rn[requester_id])
        if _ln_value == self._rn[requester_id]:
            return True
        return False

    def enter_cs(self):
        # if debug_ln_rn:
        #     print(self.json_dict['ln'], self._rn, self._token_queue)
        if self.token:
            self.critical_section = True
            return self.critical_section
        else:
            self.critical_section = False
            self.acquire_token()
            return self.critical_section

    def leave_cs(self):
        # print(f'Im a process__{self._my_port}__ i have token__{self.token}__ and im in cs__{self.critical_section}__')
        if self.critical_section:
            self.release_token()
        else:
            print("I'm going to wait...")

    def release_token(self):
        if debug_flag:
            print("Releasing token", self.json_dict['ln'][self._my_port_index])
        with self._lock:
            self.json_dict['ln'][self._my_port_index] = self._rn[self._my_port_index]
            self.critical_section = False

            if debug_ln_rn:
                print(f'LN: {self.json_dict["ln"]}, RN: {self._rn}')
                print(f'Token queue: {self._token_queue}')

            for port in [x for x in self._ports if x is not self._my_port]:
                _requester_id = self._ports.index(port)
                self._token_queue.append(_requester_id) if self._check_ln_to_rn(_requester_id) else print(
                    "proc not in Q!!")

            if not self.critical_section and self._token_queue:
                print(self._token_queue, "sending!!!")
                self._send_token(self._token_queue.pop(0), self.json_dict['ln'])

    #     check queue if there are some process waiting, send them an token

    def _send_token(self, receiver, ln):
        self._create_dict(
            self._my_port,
            receiver,
            "token",
            True,
            ln,
            None,
            self.data,
            self._token_queue)
        self.publish()
        self.token = False

    def set_condition(self, max_values, min_values=0):
        self.max_values = max_values
        self.min_values = min_values
        self.buffer_values = []

    # def _check_conditions_reader(self):
    #     return True if len(self.buffer_values) < self.max_values else False

    def acquire_token(self):
        if not self._token_requested:
            print("Request for token is sent")
            self.json_dict['sn'] += 1
            self._create_dict(
                self._my_port,
                None,
                "acquire",
                False,
                None,
                self.json_dict['sn'],
                None,
                None)
            self._rn[self._my_port_index] = self.json_dict['sn']
            self._token_requested = True
            self.publish()
        else:
            if debug_flag:
                print("Already asked for a token...", self.json_dict['sn'], self._rn)
            self._cv.wait()
            # time.sleep(1)

    def _subscriber_init(self, port: int):
        sub_context = zmq.Context()
        sub_socket = sub_context.socket(zmq.SUB)

        print(f'Connecting a subscriber to: tcp://localhost:{port}')
        sub_socket.connect(f'tcp://localhost:{port}')

        sub_filter = ""
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, sub_filter)

        # HERE IS THE PLACE TO HANDLE MESSAGES FROM OTHER PROCESSES
        while self._running:
            if debug_flag:
                print(f'Waiting for message on port....{port}')
            json_obj = sub_socket.recv_json()
            json_received = json.loads(json_obj)
            # print(json_received)
            with self._lock:
                if json_received['action'] == "token":
                    if self._ports[json_received['receiver']] == self._my_port:
                        self.token = json_received['token']
                        self._token_requested = False
                        self._token_queue = json_received['token_queue']
                        self._create_dict(
                            None,
                            None,
                            None,
                            self.token,
                            json_received['ln'],
                            None,
                            json_received['data'],
                            json_received['token_queue'])
                        self.data = self.json_dict['data']
                        self._cv.notify_all()
                        # tutaj dac jakies notify all zeby sprawdzic czy proces ma token
                        if debug_flag:
                            print(f'Process with port: {self._my_port} has received token')
                            print(
                                f'DATA!!!: {json_received["ln"]}, {json_received["data"]} ==? {self.json_dict["data"]}')
                            print(f'{self.json_dict, self._rn}')

                if json_received['action'] == "acquire":
                    # print(self._rn[self._ports.index(json_received['sender'])], json_received['sn'])
                    _requester_id = self._ports.index(json_received['sender'])
                    self._rn[_requester_id] = max(self._rn[_requester_id], json_received['sn'])
                    if self.token:
                        self._token_queue.append(_requester_id) if self._check_ln_to_rn(_requester_id) else print(
                            "proc not in Q!!")
                        if debug_flag:
                            print(self._token_queue, self.json_dict['data'])
                if json_received['action'] == "end_work":
                    if debug_flag:
                        print("I'm ending my work...")
                    self.data = json_received['data']
                    self.pub_socket.close()
                    break

        sub_socket.close()

    # STARTING TO LISTEN FOR MESSAGES
    def _start_subscribers(self):
        self._running = True
        for port in [x for x in self._ports if x is not self._my_port]:
            thread = threading.Thread(target=self._subscriber_init, args=(port,))
            thread.daemon = True
            thread.start()

    def stop_all(self):
        if self._running:
            self._create_dict(
                self._my_port,
                None,
                "end_work",
                None,
                None,
                None,
                self.data,
                None)
            self.publish()
            self.pub_socket.close()
            self._running = False
