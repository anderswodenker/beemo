# Version 0.1.1 | CSV Version
from dataset import Dataset
from configuration.local_config import LocalConfig
from helper.logger import ErrorHandler
import time
import os
import csv
import mapping
from helper.time_helper import get_time
import pyudev

dataset = Dataset()
config = LocalConfig()
error = ErrorHandler()

# todo: usb stick check


def is_mounted():
    try:
        context = pyudev.Context()
        removable = [device for device in context.list_devices(subsystem='block', DEVTYPE='disk') if
                     device.attributes.asstring('removable') == "1"]

        for device in removable:
            partitions = [device.device_node for device in
                          context.list_devices(subsystem='block', DEVTYPE='partition', parent=device)]

            for partition in partitions:
                path = f"/home/pi/usb-drive{partition}"
                if not os.path.exists(os.path.join(path)):
                    os.system(f"sudo mkdir {os.path.join(path)}")
                os.system(f"sudo mount {partition} {path}")
                usb_found = True
                print(path)
                return usb_found, path
    except Exception as e:
        error.log.exception(e)
        return False, False


def write_data(data):
    """
    format: time, device+location, hum, temp, weight, ds18b20x
    :param data: csv list data
    :return: bool
    """

    try:
        is_usb, usb_path = is_mounted()
        if is_usb:
            path = usb_path
        else:
            path = mapping.csv_data_path
        with open(path, mode='a+') as dataset_file:
            dataset_writer = csv.writer(dataset_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            dataset_writer.writerow(data)
        dataset_file.close()
        return True
    except Exception as e:
        error.log.exception(e)
        return False


if not config.scale["calibrated"]:
    from sensorlib.rgb import RGB
    led = RGB()
    # calibration
    try:
        # calibration mode
        led.blink("blue", 3, 0.3)
        # remove all items from scale please
        led.blink("red", 30, 1)
        dataset.scale.setup()
        # put the calibration weight on the scale
        led.blink("green", 15, 1)
        dataset.scale.calibrate(int(config.scale["calibrate_weight"]))
        # all done
        led.blink("green", 3, 0.3)
        # reboot system
        os.system("sudo reboot")
    except Exception as e:
        led.blink("red", 5, 0.3)
        error.log.exception(e)
else:
    while True:
        # start measuring
        try:
            # reset csv_data list
            csv_data = list()

            # reset dataset data
            dataset.data = dict()

            # get config data
            config.get_config_data()

            # add time first
            csv_data.append(get_time())

            # iterate all sensors in DATA (conf.ini)
            for sensor, is_active in config.data.items():
                # get data from sensor if active
                if is_active:
                    dataset.get_data(sensor)

            # add device id and location
            csv_data.append(f"{config.settings['device_location']}{config.settings['device_name']}")

            # add hum from aht20 to csv
            if 'hum' in dataset.data:
                csv_data.append(dataset.data["hum"])
            else:
                csv_data.append(00)

            # add temp from aht20 to csv
            if 'temp' in dataset.data:
                csv_data.append(dataset.data["temp"])
            else:
                csv_data.append(00)

            # add weight to csv
            if 'weight' in dataset.data:
                csv_data.append(dataset.data["weight"])
            else:
                csv_data.append(00)

            # add all ds18b20
            for key, val in dataset.data.items():
                if "ds18b20" in key:
                    csv_data.append(val)

            if not write_data(csv_data):
                error.log.exception("data writing failed")

            # sleep x Seconds (app_weight_seconds) (conf.ini)
            time.sleep(int(config.settings["app_wait_seconds"]))
        except Exception as e:
            print(e)
            error.log.exception(e)
            continue
        except KeyboardInterrupt:
            exit()
