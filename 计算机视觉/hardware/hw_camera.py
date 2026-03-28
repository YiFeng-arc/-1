import cv2

class CameraManager:
    """
    物理相机管理引擎：处理外部USB外设或内置摄像头的挂载、帧率控制与画面获取。
    """
    def __init__(self, camera_index=0, width=1920, height=1080):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None

    def open(self):
        # Windows下使用CAP_DSHOW可以显著提升摄像头启动速度并避免黑屏
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        # 降低采集缓冲，减少高负载时的“延迟堆积感”
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.cap.isOpened():
            actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(f"[视觉硬件] 成功接管驱动, 索引 {self.camera_index}，分配分辨率: {actual_w}x{actual_h} @ {actual_fps:.1f} FPS")
            return True

        print(f"[视觉异常] 设备节点空缺或被占用, 索引 {self.camera_index}")
        return False

    def capture_image(self):
        """
        截取当前画面的图像帧。
        使用 grab/retrieve 并仅轻量丢弃1帧，平衡实时性与CPU占用。
        """
        if not self.cap or not self.cap.isOpened():
            return None

        # 轻量刷新缓冲，避免旧帧积压导致“跟手差”
        self.cap.grab()
        ret, frame = self.cap.retrieve()

        if ret:
            return frame

        # 兜底：若retrieve失败，回退到read
        ret, frame = self.cap.read()
        return frame if ret else None

    def close(self):
        if self.cap:
            self.cap.release()
            print("[视觉硬件] 驱动接管已解除。")
