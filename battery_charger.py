import matplotlib.pyplot as plt
import PSU
import yaml
import pprint
import time
from datetime import datetime
import pandas as pd
import matplotlib.dates as mdates


class BatteryCharger:
    """
    Class handling the serial connection to the power supply.

    Methods
    -------
    __init__
    start_serial
    settings
    unsafe_charge
    charge
    update_data
    charge_check
    charge_update
    charge_setup_high_level
    charge_setup_low_level
    ready_before_charge
    make_current_params
    check_voltage
    vset
    iset
    end
    """
    def __init__(self, *args, **kwargs):
        self.psu = None
        self.port = None
        self.settings_confirmed = False
        self.started_serial = False
        self.battery = None
        self.battery_params = None
        self.charge_params = None
        self.battery_voltage = None
        self.soc = None
        self.current = None
        self.voltage = None

        # Plotting
        self.time_history = []
        self.voltage_history = []
        self.current_history = []
        self.battery_voltage_history = []

        # Setting up from the start if everything is ready
        if self.settings():
            self.start_serial(*args, **kwargs)
        else:
            print('Set settings and start serial manually.')

    def start_serial(self, *args, **kwargs):
        """
        Initializes the serial connection.

        Parameters
        ----------
        args
            To the serial.serial_for_url
        kwargs
            To the serial.serial_for_url

        Returns
        -------

        """
        self.psu = PSU.PSU(self.port, *args, **kwargs)
        self.psu.output_off()
        self.started_serial = True

    def settings(self):
        """
        Reads and check the settings. Returns if settings are set.

        Capacity in battery_params overrule capacity in charge_params. It
        must have one.

        Returns
        -------
        bool
            If settings are set or not.
        """
        with open('Config/charge_params.yml', 'r') as file:
            charge_params = yaml.safe_load(file)
        with open('Config/battery_params.yml', 'r') as file:
            battery_params = yaml.safe_load(file)

        self.battery = charge_params['Battery']
        self.port = charge_params['Port']

        if battery_params[self.battery]['Capacity'] is None:
            if charge_params['Capacity'] is None:
                raise ValueError('Capacity is not set.')
            else:
                battery_params[self.battery]['Capacity'] = \
                    charge_params['Capacity']

        self.battery_params = battery_params[self.battery]
        self.make_current_params()

        print('The settings are: ')
        pprint.pprint(self.battery_params)
        sure = input('Are you ok with these settings (y, n_): ')
        if sure.lower() == 'y':
            self.settings_confirmed = True
            return True
        else:
            return False

    def unsafe_charge(self, plotting=True, save_data=True):
        """
        Charges the battery. It checks for settings set, if the battery is
        in good condition

        Parameters
        ----------
        plotting : bool
            Enable plotting
        save_data : bool
            Enable saving csv

        Returns
        -------

        """
        if not self.charge_setup_high_level():
            return
        if plotting:
            plot_graph(self.soc, self.current_history, self.voltage_history,
                       self.time_history, self.battery_voltage_history)

        while self.charge_check():
            time.sleep(120 / self.battery_params['SOC_CR'][self.soc])
            self.charge_update()

            self.update_data()
            if plotting:
                plot_graph(self.soc, self.current_history,
                           self.voltage_history, self.time_history,
                           self.battery_voltage_history)

        self.psu.output_off()
        print('Finished charging')

        if save_data:
            save_data_csv(self.current_history, self.voltage_history,
                          self.time_history, self.battery_voltage_history,
                          self.charge_params['CSVFile'])

    def charge(self, plotting=True, save_data=True):
        """
        Charges the battery, but in comparison to unsafe_charge, it turns
        off the output if anything goes wrong.

        Parameters
        ----------
        plotting : bool
            Enable plotting
        save_data : bool
            Enable saving csv

        Returns
        -------

        """
        try:
            self.unsafe_charge(plotting, save_data)
        except ValueError as error:
            self.psu.output_off()
            print("Probably voltage or current set to be outside of allowed "
                  "values or battery params not set correctly")
            raise error
        except Exception as error:
            self.psu.output_off()
            print(f"Unexpected {error}, {type(error)}")
            raise error

    def update_data(self):
        """
        Updates the time-, current-, charging voltage- and battery
        voltage-history.

        Returns
        -------

        """
        self.time_history.append(datetime.now())
        self.current_history.append(self.current)
        self.voltage_history.append(self.voltage)
        self.battery_voltage_history.append(self.battery_voltage)

    def charge_check(self):
        """
        Checks if the charging should continue.

        Returns
        -------
        bool
            Continue charging.
        """
        if not self.battery_voltage >= self.battery_params['VoltageMin']:
            return False
        if not self.current >= self.battery_params['CurrentChargeCutOff']:
            return False
        if not self.battery_voltage >= self.battery_params[
                'VoltageChargeCutOff']:
            return False
        return True

    def charge_update(self):
        """
        Updates the values needed for charging; computing SOC, setting the
        current and getting the voltage and current outputs.

        Returns
        -------

        """
        self.battery_voltage = self.check_voltage()
        while self.battery_voltage > self.battery_params['SOC_OCV'][self.soc +
                                                                    10]:
            self.soc += 10
        self.iset(self.battery_params['SOC_Current'][self.soc])
        self.current = self.psu.get_iout()
        self.voltage = self.psu.get_vout()
        self.update_data()

    def charge_setup_high_level(self):
        """
        All setup needed before charging.

        Returns
        -------
        bool
            If ready for charging.
        """
        if not self.settings_confirmed:
            print('Please set settings first.')
            return False

        if not self.started_serial:
            print('Please start serial first.')
            return False

        if not self.ready_before_charge():
            print('Check battery or parameters.')
            return False

        self.charge_setup_low_level()
        self.update_data()
        return True

    def charge_setup_low_level(self):
        """
        Does the setup for the charge, computing SOC, safely setting the
        voltage- and current-values and getting the voltage and current
        outputs.

        Returns
        -------

        """
        soc = 0
        while self.battery_voltage > self.battery_params['SOC_OCV'][soc + 10]:
            soc += 10
        self.soc = soc

        self.psu.output_off()
        self.iset(self.battery_params['SOC_Current'][soc])
        self.vset(self.battery_params['VoltageMax'])
        self.psu.output_on()
        self.current = self.psu.get_iout()
        self.voltage = self.psu.get_vout()

    def ready_before_charge(self):
        """
        Checks battery against over-voltage and under-voltage

        Returns
        -------
        bool
            If battery is ready for charge or not
        """
        battery_voltage = self.check_voltage()
        self.battery_voltage = battery_voltage
        if battery_voltage < self.battery_params['VoltageMin']:
            print(f'The battery voltage is too low.\nBattery voltage: '
                  f'{battery_voltage}V < {self.battery_params["VoltageMin"]}V')
            return False
        if battery_voltage > self.battery_params['VoltageMax']:
            print(f'The battery voltage is too high.\nBattery voltage: '
                  f'{battery_voltage}V > {self.battery_params["VoltageMax"]}V')
            return False
        return True

    def make_current_params(self):
        """
        Makes current parameters from the c-value parameters.

        Returns
        -------

        """
        soc_current = {}
        for i in range(11):
            soc_current[i*10] = self.battery_params['SOC_CR'][i * 10] * \
                                self.battery_params['Capacity']
        self.battery_params['SOC_Current'] = soc_current
        self.battery_params['CurrentChargeCutOff'] = \
            self.battery_params['CChargeCutOff'] * \
            self.battery_params['Capacity']
        self.battery_params['CurrentChargeMax'] = \
            self.battery_params['CChargeMax'] * self.battery_params['Capacity']
        self.battery_params['CurrentChargeMin'] = \
            self.battery_params['CChargeCutOff'] * \
            self.battery_params['Capacity']

    def check_voltage(self):
        """
        Checks battery voltage with parameters.

        Returns
        -------
        float
            The voltage of the battery.
        """
        battery_voltage = self.psu.find_voltage_battery(self.battery_params[
                                                            'VoltageMax'],
                                                        0.000)
        return battery_voltage

    def vset(self, value):
        """
        Sets the voltage of the PSU but with the constraints from the
        battery parameters.
        Parameters
        ----------
        value : float
            Voltage value for the PSU.

        Returns
        -------

        """
        if self.battery_params['VoltageMin'] <= value <= self.battery_params[
                'VoltageMax']:
            self.psu.vset(value)
        else:
            raise ValueError(f'Voltage not allowed. It should be '
                             f'{self.battery_params["VoltageMin"]}V <= '
                             f'{value}V <= '
                             f'{self.battery_params["VoltageMax"]}V')

    def iset(self, value):
        """
        Sets the current of the PSU but with the constraints from the
        battery parameters.
        Parameters
        ----------
        value : float
            Current value for the PSU.

        Returns
        -------

        """
        if self.battery_params['CurrentChargeMin'] <= value <= \
                self.battery_params['CurrentChargeMax']:
            self.psu.iset(value)
        else:
            raise ValueError(f'Current not allowed. It should be '
                             f'{self.battery_params["CurrentChargeMin"]}A <= '
                             f'{value}A <= '
                             f'{self.battery_params["CurrentChargeMax"]}A')

    def end(self):
        """
        An easier way to access the close serial command of the PSU.

        Returns
        -------

        """
        self.psu.close_serial()


def plot_graph(soc, current_history, voltage_history, time_history,
               battery_voltage_history):
    """

    Parameters
    ----------
    soc : int
        The state of charge on percent. Must be a multiple of 10.
    current_history : list[float]
        A list of charging currents.
    voltage_history : list[float]
        A list of charging voltages.
    time_history : list[datetime]
        A list of times for measurements.
    battery_voltage_history : list[float]
        A list of battery voltages.

    Returns
    -------

    """
    # TODO: Maybe return the figure instead of showing it here.
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(1)
    fig.suptitle(f'Battery charge {soc}%')

    ax1.plot(time_history, current_history, color='b', label='Current')
    ax1.set_xlabel('Time')
    ax1.xaxis.axis_date()
    ax1.set_ylabel('Current (A)', color='b')

    ax2 = ax1.twinx()
    ax2.plot(time_history, voltage_history, color='r', label='Charging '
                                                             'Voltage')
    ax2.plot(time_history, battery_voltage_history, color='orange',
             label='Battery Voltage')
    ax2.set_ylabel('Voltage (V)', color='r')

    ah, energy = amount_charged(current_history, voltage_history, time_history)
    mah = 1000 * ah
    ax1.set_title(f'Charged {mah:.0f}mAh and {energy:.0f}J')

    my_fmt = mdates.DateFormatter("%H:%M")
    ax1.xaxis.set_major_formatter(my_fmt)

    ax2.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.show()


def amount_charged(current_history, voltage_history, time_history):
    """
    Gives the charge and energy given in Ah and J.

    Parameters
    ----------
    current_history : list[float]
        A list of charging currents.
    voltage_history : list[float]
        A list of charging voltages.
    time_history : list[datetime]
        A list of times for measurements.

    Returns
    -------
    float
        Charge charged in Ah.
    float
        Energy charged J.

    """
    ampere_hours = 0
    energy = 0
    for index in range(len(current_history) - 1):
        delta_t = time_history[index + 1] - time_history[index]
        seconds = delta_t.total_seconds()
        hours = seconds / 3600
        current = current_history[index]
        voltage = voltage_history[index]

        ampere_hours += hours * current
        energy += seconds * current * voltage

    return ampere_hours, energy


def save_data_csv(current_history, voltage_history, time_history,
                  battery_voltage_history, filename):
    """

    Parameters
    ----------
    current_history : list[float]
        A list of charging currents.
    voltage_history : list[float]
        A list of charging voltages.
    time_history : list[datetime]
        A list of times for measurements.
    battery_voltage_history : list[float]
        A list of battery voltages.
    filename : str
        Name and or location of the file

    Returns
    -------

    """
    data_dict = {'Time': time_history, 'Current': current_history,
                 'Charge Voltage': voltage_history,
                 'Battery Voltage': battery_voltage_history}
    df = pd.DataFrame(data_dict)
    df.to_csv(filename)


def yaml_func():
    with open('Config/battery_params.yml', 'r') as file:
        conf = yaml.safe_load(file)
    print(conf['Li-Ion']['SOC_OCV'][0])


def plotting_test():
    soc = 40
    current_history = [0.5, 0.45, 0.4, 0.35]
    voltage_history = [3.7, 3.75, 3.80, 3.85]
    battery_voltage_history = [3.2, 3.3, 3.3, 3.8]
    time_history = []
    for _ in range(4):
        time_history.append(datetime.now())
        time.sleep(1)
    plot_graph(soc, current_history, voltage_history, time_history,
               battery_voltage_history)


def save_data_test():
    filename = 'Data/testCSV.csv'
    current_history = [0.5, 0.45, 0.4, 0.35]
    voltage_history = [3.7, 3.75, 3.80, 3.85]
    battery_voltage_history = [3.2, 3.3, 3.3, 3.8]
    time_history = []
    for _ in range(4):
        time_history.append(datetime.now())
        time.sleep(1)
    save_data_csv(current_history, voltage_history, time_history,
                  battery_voltage_history, filename)
    df = pd.read_csv(filename)
    print(df)
    print(df.info())


if __name__ == '__main__':
    pass
