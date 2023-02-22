import PSU


def interface():
    print("Options:\n0 = quit\n1 = follow CSV\n2 = testCharger"
          "\n3 = chargeBattery")
    mode = input("Select one.\n")

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
        raise NotImplementedError('testCharger is not implemented')
    if mode == 3:
        raise NotImplementedError('batteryCharger is not implemented')


if __name__ == '__main__':
    interface()
