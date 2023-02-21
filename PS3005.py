import serial
import pandas as pd
import numpy as np
import time
from timeit import default_timer as timer
import struct
import random

def small_check():
    print(value_to_fixed_width_string_v(1.2345))
    print(value_to_fixed_width_string_i(3.45678))


def value_to_fixed_width_string_v(value):
    """
    To produce a five character value with two digits, a point and two more
    digits. For the voltage setting.


    Parameters
    ----------
    value : float

    Returns
    -------
    value_string : string

    """
    value_string = f'{value:2.2f}'
    value_string = value_string.rjust(5, '0')
    return value_string


def value_to_fixed_width_string_i(value):
    """
    To produce a five character value with two digits, a point and two more
    digits. For the current setting.


    Parameters
    ----------
    value : float

    Returns
    -------
    value_string : string

    """
    value_string = f'{value:1.3f}'
    value_string = value_string.rjust(5, '0')
    return value_string


class LABPS3005DN:
    def __init__(self, com, baudrate=9600, timeout=1, sleeptime=0.05):
        self.df = None
        self.status = None
        self.set_v = None
        self.set_i = None
        self.on = None
        self.sleeptime = sleeptime
        self.end_char = b'\\r\\n' #/b'/n'
        self.serial = serial.serial_for_url(com, baudrate=baudrate,
                                            timeout=timeout)
        self.write_serial(b'*IDN?')
        identification = self.serial.read_until()
        print(f'Connection: {identification}')
        self.get_status()

    def close_serial(self):
        self.serial.close()

    def read_csv(self, file='SequenceFile.csv'):
        self.df = pd.read_csv(file)

    def write_serial(self, finished_command_no_endchar):
        time.sleep(self.sleeptime)
        # Trying to find out if b'/n' or b'\\r\\n' is the thing
        self.serial.write(finished_command_no_endchar + self.end_char)
        self.serial.flush()
        time.sleep(self.sleeptime)

    def write_serial_continually(self):
        while True:
            input_string = input('Serial: ')
            self.write_serial(input_string.encode())
            print(self.serial.read_until())

    def vset(self, value):
        value_string = value_to_fixed_width_string_v(value)
        value_encoded = value_string.encode()
        v_string = b''.join([b'VSET1:', value_encoded])
        v_string_comp = b''.join([value_encoded, b'\n'])
        # print(f'v_string: {v_string}, v_string_comp: {v_string_comp}')
        while self.set_v != v_string_comp:
            self.write_serial(v_string)
            self.get_status()

    def iset(self, value):
        value_string = value_to_fixed_width_string_i(value)
        value_encoded = value_string.encode()
        i_string = b''.join([b'ISET1:', value_encoded])
        i_string_comp = b''.join([value_encoded, b'\n'])
        # print(f'i_string: {i_string}, i_string_comp: {i_string_comp}')
        while self.set_i != i_string_comp:
            self.write_serial(i_string)
            self.get_status()

    def output_on(self):
        while not self.on:
            output_string = b'OUTPUT1'
            self.write_serial(output_string)
            self.get_status()

    def output_off(self):
        while not self.on:
            output_string = b'OUTPUT0'
            self.write_serial(output_string)
            self.get_status()

    def get_status(self, verbose=False):
        self.status = b''
        while len(self.status) == 0:
            self.write_serial(b'STATUS?')
            self.status = self.serial.read_until()
        if self.status[1] == 49:  # 49 is the binary for 1 in this encoding
            self.on = True
        else:
            self.on = False

        self.write_serial(b'VSET1?')
        self.set_v = self.serial.read_until()
        # print(type(self.set_v))
        self.write_serial(b'ISET1?')
        self.set_i = self.serial.read_until()
        if verbose:
            print(f'STATUS: {self.status}, VSET: {self.set_v}, ISET: '
                  f'{self.set_i}')

    def info_csv_print(self, row):
        print(f"Step: {row['Step']:.0f}, Uset(V): {row['Uset(V)']}, Iset(A): "
              f"{row['Iset(A)']}, Duration(s): {row['Duration(s)']}")

    def follow_csv(self, repetitions=1):
        if self.df is None:
            print('No sequence file loaded')
            return

        # More checks
        self.vset(0.0)
        self.iset(0.0)
        self.output_on()

        for rep in range(repetitions):
            for index, row in self.df.iterrows():
                self.info_csv_print(row)
                self.vset(row['Uset(V)'])
                self.iset(row['Iset(A)'])
                #time.sleep(row['Duration(s)']) # Old way
                start = timer()
                end = timer()
                while end - start < row['Duration(s)']:
                    end = timer()


def check_of_class():
    lab = LABPS3005DN('COM7')
    lab.read_csv('SequenceFile.csv')
    # lab.follow_csv()
    lab.vset(0.00)
    lab.get_status(verbose=True)
    lab.vset(5.17)
    lab.get_status(verbose=True)
    lab.iset(0.00)
    lab.get_status(verbose=True)
    lab.iset(1.47)
    lab.get_status(verbose=True)
    lab.close_serial()

def check_of_class2():
    lab = LABPS3005DN('COM7')
    lab.read_csv('SequenceFile.csv')
    lab.follow_csv()

if __name__ == '__main__':
    small_check()


