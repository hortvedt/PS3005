import serial
import pandas as pd
import numpy as np
import time
from timeit import default_timer as timer
import struct
import random

def small_check():
    print(value_to_fixed_width_string_v(1.2345).encode())
    print(type(value_to_fixed_width_string_i(3.45678).encode()))


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
    """
    Class handling the serial connection to the power supply.

    Methods
    -------
    __init__
    close_serial
    read_csv
    write_serial
    write_serial_continually
    vset
    iset
    output_on
    output_off
    get_status
    info_csv_print
    follow_csv
    """

    def __init__(self, com, baudrate=9600, timeout=1, sleeptime=0.05):
        # TODO: Differentiate private and public variables
        """
        Opens the serial port for communication and updates the status of
        the device.

        Parameters
        ----------
        com : str
            The port of the connection
        baudrate : int
            The baudrate of the PSU
        timeout : float
            Timeout for communication
        sleeptime : float
            The time between sent commands.

        Attributes
        ----------
        self.df : pandas dataframe
        self.status : bytes
        self.set_v : bytes
        self.set_i : bytes
        self.cv : bool
        self.on : bool
        self.ocp : bool
        self.sleeptime : float
        self.end_char : bytes
        self.serial : serial connection
        """
        self.df = None
        self.status = None
        self.set_v = None
        self.set_i = None
        self.cv = None
        self.on = None
        self.ocp = None
        self.sleeptime = sleeptime
        self.end_char = b'\\r\\n'  # /b'/n'
        self.identification = None
        self.serial = serial.serial_for_url(com, baudrate=baudrate,
                                            timeout=timeout)
        self.write_serial(b'*IDN?')
        self.identification = self.serial.read_until()
        print(f'Connection: {self.identification}')
        self.get_status()

    def close_serial(self):
        """
        To close the serial port

        Parameters
        ----------

        Returns
        -------
        """
        self.serial.close()

    def load_csv(self, file='SequenceFile.csv'):
        """
        Loads the csv file in

        Parameters
        ----------
        file : str
            A .csv file with the right specifications. See example.

        Returns
        -------
        """
        self.df = pd.read_csv(file)

    def write_serial(self, finished_command_no_endchar):
        """
        The command for all serial writing. It adds the end characters itself.

        Parameters
        ----------
        finished_command_no_endchar: bytes

        Returns
        -------
        """
        time.sleep(self.sleeptime)
        self.serial.write(finished_command_no_endchar + self.end_char)
        self.serial.flush()
        time.sleep(self.sleeptime)

    def write_serial_continually(self):
        """
        For writing yourself to directly to the PSU. It does so by use of
        the input function. It still adds the
        escape characters itself so no need to add them.

        Returns
        -------
        """
        while True:
            input_string = input('Serial: ')
            self.write_serial(input_string.encode())
            print(self.serial.read_until())

    def vset(self, value):
        """
        For setting the voltage value. It confirms it has been set. It also
        checks if the value is valid.

        Parameters
        ----------
        value: float
            Voltage value for the PSU in volts.

        Returns
        -------
        """
        if value > 30:
            raise ValueError(f'Value is larger than allowed voltage value. '
                             f'{value}V > 30V')
        value_string = value_to_fixed_width_string_v(value)
        value_encoded = value_string.encode()
        v_string = b''.join([b'VSET1:', value_encoded])
        v_string_comp = b''.join([value_encoded, b'\n'])
        # print(f'v_string: {v_string}, v_string_comp: {v_string_comp}')
        while self.set_v != v_string_comp:
            self.write_serial(v_string)
            self.get_status()

    def iset(self, value):
        """
        For setting the current value. It confirms it has been set. It also
        checks if the value is valid.

        Parameters
        ----------
        value: float
            Current value for the PSU in amperes.

        Returns
        -------
        """
        if value > 5:
            raise ValueError(f'Value is larger than allowed current value. '
                             f'{value}A > 5A')
        value_string = value_to_fixed_width_string_i(value)
        value_encoded = value_string.encode()
        i_string = b''.join([b'ISET1:', value_encoded])
        i_string_comp = b''.join([value_encoded, b'\n'])
        # print(f'i_string: {i_string}, i_string_comp: {i_string_comp}')
        while self.set_i != i_string_comp:
            self.write_serial(i_string)
            self.get_status()

    def output_on(self):
        """
        Turns the output on

        Returns
        -------
        """
        while not self.on:
            output_string = b'OUTPUT1'
            self.write_serial(output_string)
            self.get_status()

    def output_off(self):
        """
        Turns the output off

        Returns
        -------
        """
        while self.on:
            output_string = b'OUTPUT0'
            self.write_serial(output_string)
            self.get_status()

    def get_status(self, verbose=False):
        """
        Updates the status of the

        Parameters
        ----------
        verbose: bool

        Returns
        -------
        """
        self.status = b''
        while len(self.status) == 0:
            self.write_serial(b'STATUS?')
            self.status = self.serial.read_until()
        # 49 is the binary for 1 in this encoding
        if self.status[0] == 49:
            self.cv = True
        else:
            self.cv = False
        if self.status[1] == 49:
            self.on = True
        else:
            self.on = False
        if self.status[2] == 49:
            self.ocp = True
        else:
            self.ocp = False

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
                time.sleep(row['Duration(s)']) # Old way

                #start = timer()
                #nd = timer()
                #while end - start < row['Duration(s)']:
                #    end = timer()


def check_of_class(port):
    lab = LABPS3005DN(port)
    lab.load_csv('SequenceFile.csv')
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

def check_of_csv(port):
    lab = LABPS3005DN(port)
    lab.load_csv('SequenceFile.csv')
    lab.follow_csv()

if __name__ == '__main__':
    #check_of_csv(input('port: '))
    small_check()


