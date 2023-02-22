import PSU
import yaml
import pprint


class BatteryCharger:
    def __init__(self, *args, **kwargs):
        pass

    def choose_settings(self):
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
            print('The settings are: ')
            pprint.pprint(conf[battery])
            while True:
                shure = input('Are you ok with these settings (y_, n): ')
                if shure == '' or shure == 'y' or shure == 'n' or \
                    shure == 'quit':




    def make_new_battery(self):
        raise NotImplementedError  # May never be




def yaml_func():
    with open('Config/battery_params.yml', 'r') as file:
        conf = yaml.safe_load(file)
    print(conf['Li-Ion']['SOC_OCV'][0])


if __name__ == '__main__':
    bat = BatteryCharger()
    bat.choose_settings()
