import requests
import time
import logging


class ProxyValueGrabber:

    VALUE = -1
    LAST_FETCHED = -1

    @staticmethod
    def get_value() -> int:
        if (
            ProxyValueGrabber.VALUE != 1
            and
            ProxyValueGrabber.LAST_FETCHED >= time.time() - 600
        ):
            return ProxyValueGrabber.VALUE
        
        data = requests.get("https://companion-rust.facepunch.com/api/version")

        if data.status_code == 200:
            publish_time = data.json().get("minPublishedTime", None)
            if publish_time is not None:
                ProxyValueGrabber.VALUE = publish_time
                ProxyValueGrabber.LAST_FETCHED = time.time()
                return ProxyValueGrabber.VALUE
            
        logging.getLogger("rustWplus").warning("Failed to get value from Rust+ server")

        return 9999999999999