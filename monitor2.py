import sys
import time
import zmq
import threading
import json

debug_flag = False
debug_ln_rn = False


# Creating data structures and initializing sockets
class Monitor:
    def __init__(self, ports: list, port_id: int, token: bool):
        self._ports = ports
        self._my_port = int(port_id)
        self._my_port_index = self._ports.index(self._my_port)
        self.pub_context = zmq.Context()
        self.sub_context = zmq.Context()
        self._running = False
        self.critical_section = False

        self._token_queue = []
        self.token = token
        self._token_acquired = threading.Event()
        self._token_requested = False
        self._rn = [0 for _ in ports]
        self._request_number = 0
        self.data = [0]
        self.last_value = 0
        self.json_dict = {
            "sender": self._my_port,
            "receiver": None,
            "action": str,
            "token": bool,
            "ln": [0 for _ in ports],
            "sn": self._request_number,
            "data": [],
            "token_queue": [],
            "last_value": self.last_value
        }

        self._lock = threading.Lock()

        if token:
            self._token_acquired.set()
        self._publisher_init()
        thread = threading.Thread(target=self._subscriber_init)
        thread.daemon = True
        thread.start()
        time.sleep(1)

    # creating pub socket
    def _publisher_init(self):
        self.pub_socket = self.pub_context.socket(zmq.PUB)
        if debug_flag:
            print(f'Binding a publisher to: tcp://*:{self._my_port}')
        self.pub_socket.bind(f'tcp://*:{self._my_port}')
        self._running = True

    # connecting subscriber to every process publisher
    def _subscriber_init(self):
        sub_socket = self.sub_context.socket(zmq.SUB)

        for port in [x for x in self._ports if x != self._my_port]:
            print(f'Connecting a subscriber to: tcp://localhost:{port}')
            sub_socket.connect(f'tcp://localhost:{port}')

        sub_filter = ""
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, sub_filter)
        time.sleep(1)

        poll = zmq.Poller()
        poll.register(sub_socket, zmq.POLLIN)

        # HERE IS THE PLACE TO HANDLE MESSAGES FROM OTHER PROCESSES
        while self._running:
            if debug_flag:
                print(f'Waiting for message on port....{port}')

            socks = dict(poll.poll())
            if sub_socket in socks and socks[sub_socket] == zmq.POLLIN:
                with self._lock:
                    json_obj = sub_socket.recv_json()
                    json_received = json.loads(json_obj)

                    if json_received['action'] == "token":
                        if self._ports[json_received['receiver']] == self._my_port:
                            self.token = json_received['token']
                            self._token_requested = False
                            self._token_acquired.set()
                            self._token_queue = json_received['token_queue']
                            self._create_dict(
                                None,
                                None,
                                None,
                                self.token,
                                json_received['ln'],
                                None,
                                json_received['data'],
                                json_received['token_queue'],
                                json_received['last_value'])
                            self.last_value = json_received['last_value']
                            self.data = self.json_dict['data']
                            if debug_flag:
                                print(f'Process with port: {self._my_port} has received token')
                                print(
                                    f'DATA!!!: {json_received["ln"]}, {json_received["data"]}')
                                print(f'{self.json_dict, self._rn}')

                    if json_received['action'] == "acquire":
                        _requester_id = self._ports.index(json_received['sender'])
                        self._rn[_requester_id] = max(self._rn[_requester_id], json_received['sn'])
                        if self.token:
                            self._token_queue.append(_requester_id) if self._check_ln_to_rn(_requester_id) else 0
                            if debug_flag:
                                print(self._token_queue, self.json_dict['data'])

                    if json_received['action'] == "end_work":
                        if debug_flag:
                            print("I'm ending my work...")
                        self.data = json_received['data']
                        self.last_value = json_received['last_value']
                        self.pub_socket.close()
                        break

        sub_socket.close()

    def read_data(self):
        red_val = self.data.pop(0)
        # print(f'Process: {self._my_port} is reading...{red_val}, {self.data}')
        return red_val

    def publish(self):
        temp_json = json.dumps(self.json_dict)
        try:
            self.pub_socket.send_json(temp_json)
        except zmq.error.ZMQError:
            print("Socket is closed...")
            sys.exit(0)

    # method for filling up data structure TODO delete unnecessary fields
    def _create_dict(self, sender, receiver, action, token, ln, sn, data, token_queue, last_value):
        self.json_dict['sender'] = sender if sender is not None else self._my_port
        self.json_dict['receiver'] = receiver
        self.json_dict['action'] = action
        self.json_dict['token'] = token if token is not None else self.token
        self.json_dict['ln'] = ln if ln is not None else self.json_dict['ln']
        self.json_dict['sn'] = sn if sn is not None else self.json_dict['sn']
        self.json_dict['data'] = data if data is not None else self.data
        self.json_dict['token_queue'] = list(token_queue) if token_queue is not None else self.json_dict['token_queue']
        self.json_dict['last_value'] = last_value if last_value is not None else self.last_value

    # checking token array and process array of requests
    def _check_ln_to_rn(self, requester_id):
        _ln_value = self.json_dict['ln'][requester_id] + 1
        # print(_ln_value, self._rn[requester_id])
        if _ln_value == self._rn[requester_id]:
            return True
        return False

    def enter_cs(self):
        if self.token and self._token_acquired:
            self.critical_section = True
            return self.critical_section
        else:
            self.critical_section = False
            self.acquire_token()
            return self.critical_section

    def leave_cs(self):
        if self.critical_section and self.token:
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
                    if _requester_id not in self._token_queue:
                        self._token_queue.append(_requester_id) if self._check_ln_to_rn(_requester_id) else 0

                if not self.critical_section and self._token_queue:
                    # print(self._token_queue, "sending!!!")
                    self._send_token(self._token_queue.pop(0), self.json_dict['ln'])
        else:
            pass
            # print("I'm going to wait...")

    def _send_token(self, receiver, ln):
        self._create_dict(
            self._my_port,
            receiver,
            "token",
            True,
            ln,
            None,
            self.data,
            self._token_queue,
            self.last_value)
        self._token_acquired.clear()
        self.token = False
        self.publish()

    def acquire_token(self):
        # print("Request for token is sent")
        if self.token:
            with self._lock:
                self.critical_section = True
                return
        else:
            self.json_dict['sn'] += 1
            self._create_dict(
                self._my_port,
                None,
                "acquire",
                False,
                None,
                self.json_dict['sn'],
                None,
                None,
                None)
            self._rn[self._my_port_index] = self.json_dict['sn']
            self._token_requested = True
            self.publish()
            if debug_flag:
                print("Already asked for a token...", self.json_dict['sn'], self._rn)

        self._token_acquired.wait()
        if self.token:
            with self._lock:
                self.critical_section = True
                return
        # time.sleep(1)

    # STARTING TO LISTEN FOR MESSAGES
    def _start_subscribers(self):
        self._running = True
        for port in [x for x in self._ports if x is not self._my_port]:
            thread = threading.Thread(target=self._subscriber_init, args=(port,))
            thread.daemon = True
            thread.start()

    def add_data(self, value):
        # print(f'Producer {self._my_port}{self.token} adding: {value} to {self.data}')
        self.last_value = value
        self.data.append(value)

    def stop_all(self):
        if self._running and not self.data:
            self._create_dict(
                self._my_port,
                None,
                "end_work",
                None,
                None,
                None,
                self.data,
                None,
                None)
            self.publish()
            self._running = False
        self.pub_socket.close()
