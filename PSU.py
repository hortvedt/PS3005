import serial
import pandas as pd
import time


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


def info_csv_print(row):
    """
    Prints the information of a row of the csv file

    Parameters
    ----------
    row: pandas DF row

    Returns
    -------

    """
    print(f"Step: {row['Step']:.0f}, Uset(V): {row['Uset(V)']}, Iset(A): "
          f"{row['Iset(A)']}, Duration(s): {row['Duration(s)']}")


class PSU:
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
    get_vset
    get_iset
    get_status
    update_status
    get_vout
    get_iout
    info_csv_print
    follow_csv
    """

    def __init__(self, com, baudrate=9600, timeout=1, sleeptime=0.05):
        # TODO: Differentiate private and public variables
        # TODO: Find a solution when the psu is off or unable to connect
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
        self.output_off()
        self.update_status()

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
            input_string = input('Serial (no endchar): ')
            self.write_serial(input_string.encode() + self.end_char)
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

        self.write_serial(v_string)
        self.update_status()

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

        self.write_serial(i_string)
        self.update_status()

    def output_on(self):
        """
        Turns the output on

        Returns
        -------
        """
        output_string = b'OUTPUT1'
        self.write_serial(output_string)
        self.update_status()

    def output_off(self):
        """
        Turns the output off

        Returns
        -------
        """
        output_string = b'OUTPUT0'
        self.write_serial(output_string)
        self.update_status()

    def get_vset(self):
        """
        Gets the set voltage level

        Returns
        -------
        float
            The set voltage value
        """
        self.write_serial(b'VSET1?')
        vset = self.serial.read_until()
        vset = float(vset.decode())
        return vset

    def get_iset(self):
        """
        Gets the set current level

        Returns
        -------
        float
            The set current value
        """
        self.write_serial(b'ISET1?')
        iset = self.serial.read_until()
        iset = float(iset.decode())
        return iset

    def get_status(self):
        """
        Gets the status.

        Returns
        -------
        bytes
            The status flags
        """
        # self.status = b''  # Don't think this is needed this any longer
        # Can check for length of the serial read if multiple call are needed.
        self.write_serial(b'STATUS?')
        return self.serial.read_until()

    def update_status(self, verbose=False):
        """
        Updates the status of the PSU. This means the three flags of the
        status and set voltage and current levels.

        Calls get_vset, get_iset and get_status

        Parameters
        ----------
        verbose: bool
            For writing out the status afterwards.

        Returns
        -------
        """
        self.status = self.get_status()

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

        self.set_v = self.get_vset()
        self.set_i = self.get_iset()

        if verbose:
            print(f'STATUS: {self.status}, VSET: {self.set_v}, ISET: '
                  f'{self.set_i}')

    def get_vout(self):
        """
        Gets the voltage value output.

        Returns
        -------
        float
            The voltage output value
        """
        self.write_serial(b'VOUT1?')
        vout = self.serial.read_until()
        vout = float(vout.decode())
        return vout

    def get_iout(self):
        """
        Gets the current value output.

        Returns
        -------
        float
            The current output value
        """
        self.write_serial(b'IOUT1?')
        iout = self.serial.read_until()
        iout = float(iout.decode())
        return iout

    def follow_csv(self, repetitions=1):
        """
        Follows the instructions of the loaded csv. If no csv then it
        returns empty without doing anything.

        Parameters
        ----------
        repetitions : int
            Number of repetitions of the csv

        Returns
        -------

        """
        if self.df is None:
            print('No sequence file loaded')
            return

        # More checks
        self.vset(0.0)
        self.iset(0.0)
        self.output_on()

        for rep in range(repetitions):
            for index, row in self.df.iterrows():
                info_csv_print(row)
                self.vset(row['Uset(V)'])
                self.iset(row['Iset(A)'])
                time.sleep(row['Duration(s)'])

    def find_voltage_battery(self, safe_voltage=5, checking_current=0.001):
        """
        Finds the voltage of a battery or voltage source.

        It limits the current, then sets the voltage and measures to voltage
        over the battery. Returns to last set values afterwards.

        Parameters
        ----------
        safe_voltage: float
            The voltage level set during the check
        checking_current
            The current during the test

        Returns
        -------
        float
            Battery voltage
        """
        #  TODO: Find out if I can use 0 as current
        on_before = self.on

        old_iset = self.get_iset()
        old_vset = self.get_vset()
        self.iset(checking_current)
        self.vset(safe_voltage)
        if not on_before:
            self.output_on()
        time.sleep(0.5)
        battery_voltage = self.get_vout()
        if not on_before:
            self.output_off()
        self.vset(old_vset)
        self.iset(old_iset)
        return battery_voltage


def check_of_class(port):
    lab = PSU(port)
    lab.load_csv('SequenceFile.csv')
    # lab.follow_csv()
    lab.vset(0.00)
    lab.update_status(verbose=True)
    lab.vset(5.17)
    lab.update_status(verbose=True)
    lab.iset(0.00)
    lab.update_status(verbose=True)
    lab.iset(1.47)
    lab.update_status(verbose=True)
    lab.close_serial()


def check_of_csv(port):
    lab = PSU(port)
    lab.load_csv('SequenceFile.csv')
    lab.follow_csv()


def iset_func(value):
    value_string = value_to_fixed_width_string_i(value)
    value_encoded = value_string.encode()
    i_string = b''.join([b'ISET1:', value_encoded])
    i_string_comp = b''.join([value_encoded, b'\n'])
    print(f'i_string: {i_string}, i_string_comp: {i_string_comp}')
    value_part = i_string_comp[0:5]
    print(float(value_part.decode()))


if __name__ == '__main__':
    check_of_csv(input('port: '))


