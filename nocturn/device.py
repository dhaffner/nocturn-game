'''
Created on 27.12.2010

@author: felicitus
@warning This is my first python program ever. Feel free to fix, blame or burn.
'''
import enum

from binascii import unhexlify
from time import sleep

import usb.core
import usb.util


class Component(object):
    def __init__(self, devout=None):
        self.devout = devout
        self.value = 0

    def write(self, value, component_id=None):
        changed = self.value == value
        self.value = value
        if component_id and self.devout:
            self.devout.write(chr(component_id) + chr(value))

    def show(self, value):
        return value


class Button(Component):
    def write(self, value, component_id=None):
        value = int(value in (1, 127))
        assert component_id in set(Device.numbered_buttons + Device.bottom_buttons)
        super(Button, self).write(value, component_id=component_id)

    def show(self, value):
        if value == 0:
            return
        return super(Button, self).show(0 if self.value else 127)


class Encoder(Component):
    def __init__(self, sensitivity=3, **kwargs):
        self.sensitivity = sensitivity
        super(Encoder, self).__init__(**kwargs)

    def write(self, value, component_id=None):
        print(f'Encoder write: {value} -> {component_id}')
        value *= self.sensitivity
        value = value if value < 64 else value - 128
        assert component_id in Device.encoders or component_id == Device.speed_dial
        super(Encoder, self).write(
            min(max(0, self.value + value), 127), component_id=component_id)

    def show(self, value, absolute=False):
        if absolute:
            return
        value = value if value < 64 else value - 128
        value *= self.sensitivity
        return super(Encoder, self).show(
            min(max(0, self.value + value), 127))


class Slider(Component):
    pass


class Device(object):
    encoders = [64, 65, 66, 67, 68, 69, 70, 71]
    slider = 72
    speed_dial = 74
    numbered_buttons = [112, 113, 114, 115, 116, 117, 118, 119]
    bottom_buttons = [120, 121, 122, 123, 124, 125, 126, 127]

    def __init__(self, vendor_id=0x1235, product_id=0x000a):
        dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if dev is None:
            raise ValueError('Device not found')

        dev.set_configuration()
        config = dev.get_active_configuration()
        self.devin, self.devout = config[(0, 0)]
        # self.send_init_packets()
        self.hardware_map = self.get_hardware_map()
        for ring in range(8):
            self.set_led_ring_mode(ring, 0)

    def reset(self):
        for (ring, ring_id) in enumerate(self.encoders + [self.speed_dial]):
            self.set_led_ring_value(ring, 0)
        for (button, button_id) in enumerate(self.numbered_buttons + self.bottom_buttons):
            self.set_button(button, 0)

    def send_init_packets(self, packets=["b00000", "28002b4a2c002e35", "2a022c722e30", "7f00"]):
        for packet in packets:
            self.devout.write(unhexlify(packet))

    # Sets the LED ring mode for a specific LED ring
    # possible modes:
    #   0 = Start from MIN value,
    #   1 = Start from MAX value,
    #   2 = Start from MID value, single direction,
    #   3 = Start from MID value, both directions,
    #   4 = Single Value,
    #   5 = Single Value inverted
    #   The center LED ring can't be set to a mode (or I haven't found out how)
    def set_led_ring_mode(self, ring, mode):
        assert (0 <= ring <= 8), "The LED ring needs to be between 0 and 7"
        assert (0 <= mode <= 5), "The mode needs to be between 0 and 5"
        self.devout.write(chr(ring + 0x48) + chr(mode << 4))

    # Sets the LED ring value
    # ring = 0-8
    # value = 0-127
    def set_led_ring_value(self, ring, value):
        assert 0 <= ring <= 8, "The LED ring needs to be between 0 and 8"
        assert 0 <= value <= 127, "The LED ring value needs to be between 0 and 127"
        if ring == 8:
            self.write(chr(0x50) + chr(value))
        else:
            self.devout.write(chr(0x40 + ring) + chr(value))

    def set_encoder_value(self, encoder_id, value):
        assert encoder_id in self.encoders
        assert 0 <= value <= 127, "The LED ring value needs to be between 0 and 127"
        self.devout.write(chr(0x40 + ring) + chr(value))


    # Turns a button LED on or off
    # button = 0-16
    # val = 0 or 1
    def set_button(self, button, value):
        assert 0 <= button <= 15, "Button value needs inbetween 0 and 15 (0x00 and 0x0F)"
        assert value in (0, 1), "Button value needs to be 0 or 1"
        self.devout.write(chr(0x70 + button) + chr(value))

    def demo(self):
        self.reset()
        print('Running demo!')
        for j in range(16):
            self.set_button(j, 1)
            sleep(0.05)

        for i in range(128):
            self.devout.write(chr(0x50) + chr(i))

        for i in range(8):
            self.set_led_ring_mode(i, 3)

        for i in range(0, 127, 11):
            for j in range(0, 8):
                self.set_led_ring_value(j, i)

    # Reads a key and returns either "None" or the full packet.
    # The packet consists of at least 3 bytes, where the first
    # byte is irrelevant, the second byte is the control ID and
    # the third byte is the value
    def read(self):
        try:
            data = self.devin.read(self.devin.wMaxPacketSize, 10)
            return data
        except usb.core.USBError:
            return

    def update(self, component_id, value):
        component = self.hardware_map.get(component_id)
        if component is None:
            return

        print(f'Writing {value} to {component}')
        component.write(value, component_id=component_id)

    def write(self, packet):
        self.devout.write(packet)

    def get_hardware_map(self):
        devout = self.devout
        return {
            **{encoder_id: Encoder(devout=devout) for encoder_id in self.encoders},
            **{button_id: Button(devout=devout) for button_id in set(self.numbered_buttons + self.bottom_buttons)},
            **{self.slider: Slider(devout=devout)},
            **{self.speed_dial: Encoder(devout=devout)}
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __iter__(self):
        while True:
            data = self.read()
            if data is None:
                continue
            component_id, value = data[1:3]
            component = self.hardware_map.get(component_id)
            if component is None:
                print(f'Component {component_id} sent a message with {value} but no object is mapped.')
                continue
            yield (component_id, component.show(value))



