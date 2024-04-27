import datetime

import obsws_python as obs


class TimeoutRecording:
    def __init__(self, host, port, password, timeout=60):
        self.ws = obs.ReqClient(host=host, port=port, password=password, timeout=3)
        self.start_time = None
        self.end_time = None
        self.timeout = timeout

        # Register callback to get information on the current recording path
        self.cl = obs.EventClient(host=host, port=port, password=password)
        self.cl.callback.register(self.on_record_state_changed)
        self.recording_path = None

    def on_record_state_changed(self, data):
        """Callback function, do not rename!"""
        if data.output_path is not None:
            self.recording_path = data.output_path

    @property
    def replay_path(self):
        return self.ws.get_last_replay_buffer_replay().saved_replay_path

    @property
    def output_name(self):
        return self.start_time.strftime("%Y%m%d-%H%M%S")

    def check_timeout(self):
        if self.end_time is not None and self.end_time < datetime.datetime.now():
            self.ws.stop_record()
            self.end_time = None
            return True
        return False

    def set_timeout(self):
        if self.end_time is None:
            try:
                self.ws.start_record()
                self.ws.save_replay_buffer()
                self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.timeout)
                self.start_time = datetime.datetime.now()
            except obs.error.OBSSDKRequestError:
                # OBS is already recording -> do nothing
                pass
            return True
        else:
            self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.timeout)
            return False
