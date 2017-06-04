import mido

class Bus(object):
    def __init__(self, port=None, name='knockburn', callback=None):
        self.name = name
        self.callback = callback
        self.port = port or self.get_port()

    def get_port(self):
        print(f'[{self.name}] opening MIDI I/O port named...')
        return mido.open_ioport(name=self.name, virtual=True, callback=self.recv, autoreset=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.port.close()

    def recv(self, message):
        print(f'[{self.name}] MIDI message received: {message}')
        if self.callback is not None:
            self.callback(message)

    def send(self, control, value):
        message = mido.Message('control_change', control=control, value=int(value))
        self.port.send(message)
        print(f'[{self.name}] MIDI message sent: {message}')
