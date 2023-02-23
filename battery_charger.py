import matplotlib.pyplot as plt

import PSU
import yaml
import pprint
import time


class BatteryCharger:
    #  TODO: make it into Config here too
    def __init__(self, port, *args, **kwargs):
        self.psu = PSU.PSU(port, *args, **kwargs)
        self.psu.output_off()
        self.settings_chosen = False
        self.battery = None
        self.conf = None
        self.battery_voltage = None
        self.soc = None
        self.current = None
        self.voltage = None

        # Plotting
        self.time = []
        self.voltage_history = []
        self.current_history = []

    def choose_settings(self):
        # TODO: Break it up into smaller pieces and a more modular design
        print("You can quit the settings by typing 'Quit'")
        with open('Config/battery_params.yml', 'r') as file:
            conf = yaml.safe_load(file)
        print(f'Your choices of batteries are:')
        first_choice = ['New', 'Quit']
        for key, value in conf.items():
            first_choice.append(key)
        for item in first_choice:
            print(f'  - {item}')
        while True:
            battery = input('Choose battery: ')
            if battery in first_choice:
                break
            print(f'{battery} is not an option.')
        if battery == 'Quit':
            return
        if battery == 'New':
            self.make_new_battery()
        elif battery in conf:
            while conf[battery]['Capacity'] is None:
                print('Capacity is not set in battery parameter')
                capacity = float(input(f'Capacity of the {battery} battery ['
                                       f'Ah]: '))
                conf[battery]['Capacity'] = capacity
            print('The settings are: ')
            pprint.pprint(conf[battery])
            while True:
                shure = input('Are you ok with these settings (y_, n): ')
                if shure == '' or shure == 'y' or shure == 'n' or \
                    shure == 'Quit':
                    break
                else:
                    print(f'{shure} is not an option.')
            if shure == 'Quit':
                return
            if shure == 'n':
                print('Please change configfiles and try again.')
                return
            if shure == '' or shure == 'y':
                print('Settings chosen.')
                self.settings_chosen = True
                self.battery = battery
                self.conf = conf[battery]
                self.make_current_params()

    def charge(self):
        # TODO: Implement a try except to make it turn off the output if failed
        # TODO: Make it show the charging in a graph
        if not self.settings_chosen:
            print('Please set settings first.')
            return

        if not self.ready_before_charge():
            print('Check battery or parameters.')
            return

        self.charge_setup()

        self.plot_graph()

        while self.charge_check():
            time.sleep(120 / self.conf['SOC_CR'][self.soc])
            self.charge_update()

            self.update_data()
            self.plot_graph()

        self.psu.output_off()
        print('Finished charging')

    def update_data(self):
        self.current_history.append(self.current)
        self.voltage_history.append(self.voltage)

    def plot_graph(self):
        fig, ax1 = plt.subplots(1)
        ax1.set_title(f'Battery charge {self.soc}%')
        ax1.plot(self.current_history, color='r', label='Current')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Current (A)', color='red')
        ax2 = ax1.twinx()
        ax2.plot(self.voltage_history, color='b', label='Voltage')
        ax2.set_ylabel('Voltage (V)', color='blue')
        fig.show()

    def charge_update(self):
        self.battery_voltage = self.check_voltage()
        while self.battery_voltage > self.conf['SOC_OCV'][self.soc + 10]:
            self.soc += 10
        self.iset(self.conf['SOC_Current'][self.soc])
        self.current = self.psu.get_iout()
        self.voltage = self.psu.get_vout()

    def charge_check(self):
        if not self.voltage >= self.conf['VoltageMin']:
            return False
        if not self.current >= self.conf['CurrentChargeCutOff']:
            return False
        return True

    def charge_setup(self):
        soc = 0
        while self.battery_voltage > self.conf['SOC_OCV'][soc + 10]:
            soc += 10
        self.soc = soc

        self.psu.output_off()
        self.iset(self.conf['SOC_Current'][soc])
        self.vset(self.conf['VoltageMax'])
        self.psu.output_on()
        self.current = self.psu.get_iout()
        self.voltage = self.psu.get_vout()


    def ready_before_charge(self):
        battery_voltage = self.check_voltage()
        self.battery_voltage = battery_voltage
        if battery_voltage < self.conf['VoltageMin']:
            print(f'The battery voltage is too low.\nBattery voltage: '
                  f'{battery_voltage}V < {self.conf["VoltageMin"]}V')
            return False
        if battery_voltage > self.conf['VoltageMax']:
            print(f'The battery voltage is too high.\nBattery voltage: '
                  f'{battery_voltage}V > {self.conf["VoltageMax"]}V')
            return False
        return True

    def make_current_params(self):
        soc_current = {}
        for i in range(11):
            soc_current[i*10] = self.conf['SOC_CR'][i*10] * self.conf[
                'Capacity']
        self.conf['SOC_Current'] = soc_current

        self.conf['CurrentChargeCutOff'] = self.conf['CChargeCutOff'] * \
                                           self.conf['Capacity']
        self.conf['CurrentChargeMax'] = self.conf['CChargeMax'] * \
                                        self.conf['Capacity']
        self.conf['CurrentChargeMin'] = self.conf['CChargeCutOff'] * \
                                           self.conf['Capacity']

    def check_voltage(self):
        battery_voltage = self.psu.find_voltage_battery(self.conf['VoltageMax']
                                                        , 0.001)
        return battery_voltage

    def vset(self, value):
        if self.conf['VoltageMin'] <= self.voltage <= self.conf['VoltageMax']:
            self.psu.vset(value)
        else:
            raise ValueError(f'Voltage not allowed. It should be '
                             f'{self.conf["VoltageMin"]}V <= '
                             f'{self.voltage}V <= {self.conf["VoltageMax"]}V')

    def iset(self, value):
        if self.conf['CurrentChargeMin'] <= self.voltage <= self.conf[
            'CurrentChargeMax']:
            self.psu.iset(value)
        else:
            raise ValueError(f'Current not allowed. It should be '
                             f'{self.conf["CurrentChargeMin"]}A <= '
                             f'{self.current}A <= '
                             f'{self.conf["CurrentChargeMax"]}A')
    def make_new_battery(self):
        raise NotImplementedError  # May never be


def yaml_func():
    with open('Config/battery_params.yml', 'r') as file:
        conf = yaml.safe_load(file)
    print(conf['Li-Ion']['SOC_OCV'][0])


if __name__ == '__main__':
    bat = BatteryCharger('COM7')
    bat.choose_settings()
