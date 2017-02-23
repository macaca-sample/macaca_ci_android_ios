__author__ = 'tongshan'
# -*- coding: utf-8 -*-

import os
import re
import threading
import requests
from requests.exceptions import ConnectionError
from requests.exceptions import ReadTimeout
from multiprocessing.pool import Pool
from time import sleep
from macaca import WebDriver


ANDROID_PACKAGE = "YOUR ANDROID PACKAGE"
ANDROID_ACTIVITY = "YOUR ANDROID ACTIVITY"

IOS_BUNDLE = "YOUR IOS BUNDLE ID"


class DRIVER:

    driver = None
    OS = None

    @classmethod
    def set_driver(cls, driver):
        cls.driver = driver

    @classmethod
    def set_OS(cls, OS):
        cls.OS = OS


class InitDevice:
    """
    获取连接的设备的信息
    """
    def __init__(self):
        self.GET_ANDROID = "adb devices"
        self.GET_IOS = "instruments -s devices"

    def get_device(self):
        value = os.popen(self.GET_ANDROID)

        device = []

        for v in value.readlines():
            android = {}
            s_value = str(v).replace("\n", "").replace("\t", "")
            if s_value.rfind('device') != -1 and (not s_value.startswith("List")) and s_value != "":
                android['platformName'] = 'Android'
                android['udid'] = s_value[:s_value.find('device')].strip()
                android['package'] = ANDROID_PACKAGE
                android['activity'] = ANDROID_ACTIVITY
                device.append(android)

        value = os.popen(self.GET_IOS)

        for v in value.readlines():
            iOS = {}

            s_value = str(v).replace("\n", "").replace("\t", "").replace(" ", "")

            if v.rfind('Simulator') != -1:
                continue
            if v.rfind("(") == -1:
                continue

            iOS['platformName'] = 'iOS'
            iOS['platformVersion'] = re.compile(r'\((.*)\)').findall(s_value)[0]
            iOS['deviceName'] = re.compile(r'(.*)\(').findall(s_value)[0]
            iOS['udid'] = re.compile(r'\[(.*?)\]').findall(s_value)[0]
            iOS['bundleId'] = IOS_BUNDLE

            device.append(iOS)

        return device


def __is_using(port):
    """
    判断端口号是否被占用
    :param port:
    :return:
    """
    cmd = "netstat -an | grep %s" % port

    if os.popen(cmd).readlines():
        return True
    else:
        return False


def get_port(count):
    """
    获得3456端口后一系列free port
    :param count:
    :return:
    """
    port = 3456
    port_list = []
    while True:
        if len(port_list) == count:
            break

        if not __is_using(port) and (port not in port_list):
            port_list.append(port)
        else:
            port += 1

    return port_list


class MacacaServer():
    def __init__(self):

        i = InitDevice()

        self.devices = i.get_device()
        self.count = len(self.devices)
        self.url = 'http://127.0.0.1:%s/wd/hub/status'

    def run(self):

        if self.count == 0:
            print("Have no device!")
            return

        pool = Pool(processes=self.count)
        port_list = get_port(self.count)

        for i in range(self.count):
            pool.apply_async(self.run_server, args=(self.devices[i], port_list[i]))

        pool.close()
        pool.join()

    def run_server(self, device, port):

        r = RunServer(port)
        r.start()

        while not self.is_running(port):
            sleep(1)

        server_url = {
            'hostname': "ununtrium.local",
            'port': port,
        }
        driver = WebDriver(device, server_url)
        driver.init()

        DRIVER.set_driver(driver)
        DRIVER.set_OS(device.get("platformName"))

        self.run_test()

    def run_test(self):
        """这里运行你的测试用例, 在测试用例中driver可以通过以下方式获取

        driver = DRIVER.driver
        """
        pass

    def is_running(self, port):
        """Determine whether server is running
        :return:True or False
        """
        url = self.url % port
        response = None
        try:
            response = requests.get(url, timeout=0.01)

            if str(response.status_code).startswith('2'):

                # data = json.loads((response.content).decode("utf-8"))

                # if data.get("staus") == 0:
                return True

            return False
        except ConnectionError:
            return False
        except ReadTimeout:
            return False
        finally:
            if response:
                response.close()


class RunServer(threading.Thread):

    def __init__(self, port):
        threading.Thread.__init__(self)
        self.cmd = 'macaca server -p %s --verbose' % port

    def run(self):
        os.system(self.cmd)


if __name__ == "__main__":

    m = MacacaServer()
    m.run()
