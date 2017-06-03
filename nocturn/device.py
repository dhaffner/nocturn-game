'''
Created on 27.12.2010

@author: felicitus
@warning This is my first python program ever. Feel free to fix, blame or burn.
'''
from binascii import unhexlify
from time import sleep

import usb.core
import usb.util


class Device(object):
    def __init__(self, vendor_id=0x1235, product_id=0x000a):
        dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if dev is None:
            raise ValueError('Device not found')

        dev.set_configuration()
        config = dev.get_active_configuration()
        self.devin, self.devout = config[(0, 0)]
        self.send_init_packets()

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

    # Turns a button LED on or off
    # button = 0-16
    # val = 0 or 1
    def set_button(self, button, value):
        assert 0 <= button <= 15, "Button value needs inbetween 0 and 15 (0x00 and 0x0F)"
        assert value in (0, 1), "Button value needs to be 0 or 1"
        self.devout.write(chr(0x70 + button) + chr(value))

    def demo(self):
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

    def write(self, packet):
        self.devout.write(packet)

    def echo(self):
        while True:
            data = self.read()
            if data:
                print(data)
