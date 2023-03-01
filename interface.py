import PSU
import battery_charger


def interface():
    print("Options:\n0 = quit\n1 = follow CSV\n2 = chargeBattery"
          "\n3 = testCharge\n4 = inputmodePSU\n")
    mode = input("Select one:\n")

    try:
        mode = int(mode)
    except ValueError:
        raise ValueError('Must be an integer.')

    if mode == 0:
        pass
    if mode == 1:
        psu = PSU.PSU(input('PORT: '))
        psu.load_csv(input('CSV-file: '))
        psu.follow_csv(int(input('Number of repetitions: ')))
        psu.close_serial()
    if mode == 2:
        batcha = battery_charger.BatteryCharger(input('PORT: '))
        batcha.choose_settings()
        batcha.safe_charge()
        batcha.end()
    if mode == 3:
        psu = PSU.PSU(input('PORT: '))
        battery_voltage = psu.find_voltage_battery(float(input('Max battery '
                                                         'voltage: ')))
        print(f'The battery voltage is {battery_voltage}V.')
        psu.close_serial()
    if mode == 4:
        psu = psu = PSU.PSU(input('PORT: '))
        psu.write_serial_continually()


if __name__ == '__main__':
    interface()
