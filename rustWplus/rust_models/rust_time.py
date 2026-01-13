from .serialization import Serializable

class RustTime(Serializable):
    def __init__(self, day_length, sunrise, sunset, time, raw_time, time_scale) -> None:
        self._day_length: float = day_length
        self._sunrise: str = sunrise
        self._sunset: str = sunset
        self._time: str = time
        self._raw_time: float = raw_time
        self._time_scale: float = time_scale

    @property
    def sunrise_in(self) -> float:
        return self._sunrise_in
    
    @property
    def sunset_in(self) -> float:
        return self._sunset_in

    #Full day in real life minutes
    @property
    def day_length(self) -> float:
        return self._day_length

    #Start of sunrise
    @property
    def sunrise(self) -> str:
        return self._sunrise

    #Start of sunset
    @property
    def sunset(self) -> str:
        return self._sunset

    #Time
    @property
    def time(self) -> str:
        return self._time

    #Minutes from 0:00
    @property
    def raw_time(self) -> float:
        return self._raw_time

    # day_length / 1440(24h)
    @property
    def time_scale(self) -> float:
        return self._time_scale
    
    def __str__(self) -> str:
        return "RustTime[day_length={}, sunrise={}, sunset={}, time={}, raw_time={}, time_scale={}]".format(
            self.day_length,
            self.sunrise,
            self.sunset,
            self.time,
            self.raw_time,
            self.time_scale
        )