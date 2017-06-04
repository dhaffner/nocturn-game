from .device import Device
from .midi import Bus

if __name__ == '__main__':
    with Device() as device:
        def callback(message):
            device.update(message.control, message.value)
        with Bus(callback=callback) as bus:
            while True:
                for (note, value) in device:
                    bus.send(note, value)
