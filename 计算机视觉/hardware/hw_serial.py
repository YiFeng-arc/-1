import serial
import time

class SerialManager:
    """
    硬件串口通信引擎：负责与单片机底层进行握手、数据拆包及异步信号拦截。
    """
    def __init__(self, port='COM3', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[硬件总线] 连接成功: {self.port}")
            return True
        except Exception as e:
            print(f"[硬件总线] 无法连接串口 {self.port}: {e}")
            return False

    def wait_for_trigger(self, trigger_msg="CAPTURE"):
        """
        阻塞等待单片机发送的触发信号。
        通信协议建议：单片机发送 "CAPTURE,电压值" (例如 "CAPTURE,5.0")
        :return: 解析后的电压值(float)，如果未附带则返回None
        """
        while True:
            if self.serial_conn and self.serial_conn.in_waiting > 0:
                data = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if data.startswith(trigger_msg):
                    parts = data.split(',')
                    voltage = float(parts[1]) if len(parts) > 1 else None
                    return voltage
            time.sleep(0.05)

    def close(self):
        if self.serial_conn:
            self.serial_conn.close()
            print("[硬件总线] 连接已安全断开。")
