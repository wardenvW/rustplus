from push_receiver import PushReceiver
from threading import Thread
from .fcm_handlers import FCMHandler
import time
import logging


class FCMListener:
    def __init__(self, data: dict = None) -> None:
        self.thread = None
        self.data = data
        self._push_listener = PushReceiver(credentials=self.data["fcm_credentials"])  
        self._start_time = time.time() * 1000   #in ms
        self.logger = logging.getLogger("rustWplus.py")
        self._fcm_handler = FCMHandler()    

    def start(self, daemon=False):
        self.logger.info("Started listening...")
        self.thread = Thread(target=self._fcm_listen, daemon=daemon).start()

    def _fcm_listen(self) -> None:
        if self.data is None:
            self.logger.error("Data for FCM not provided")
            raise ValueError()
        
        self._push_listener.listen(callback=self._process_notification)

    
    def _process_notification(self, obj, notification, data_message) -> None:
        notification_time_sent = getattr(data_message, "sent", 0)
        self.logger.debug(f"Notification sent at {notification_time_sent}")

        if notification_time_sent < self._start_time:
            self.logger.info("Ignored old notification")
            return

        for app_data in data_message.app_data:
            if app_data.key == "gcm.notification.android_channel_id" and app_data.value == "pairing":
                self.logger.info("Pairing notification received")
                self._fcm_handler.handle(fcm_message=data_message)
                break
        else:
            self.logger.debug("Non-pairing notification ignored")

        



