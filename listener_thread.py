import time
from enum import Enum

from logreader import LogReader
from recorder import TimeoutRecording


class RecordingStatusCallback(Enum):
    RECORDING_READY = 1
    RECORDING_STARTED = 2
    RECORDING_ENDED = 3
    RECORDING_ERROR = 4


def run(settings, status_callback, stop_event, video_processing_pipeline):
    try:
        log_checker = LogReader(
            settings["LOG_DIR"]
        )

        timeout_recorder = TimeoutRecording(
            host=settings['OBS_HOST'],
            port=int(settings['OBS_PORT']),
            password=settings['OBS_PASSWORD'],
            timeout=int(settings["TIMEOUT"])
        )

    except Exception as e:
        status_callback((RecordingStatusCallback.RECORDING_ERROR, e))
        return
    else:
        status_callback(RecordingStatusCallback.RECORDING_READY)

    try:
        while True:
            if log_checker.check_files():
                if timeout_recorder.set_timeout():
                    status_callback(RecordingStatusCallback.RECORDING_STARTED)

            if timeout_recorder.check_timeout():
                status_callback(RecordingStatusCallback.RECORDING_ENDED)
                video_processing_pipeline.process(
                    timeout_recorder.replay_path,
                    timeout_recorder.recording_path,
                    settings["OUTPUT_DIR"],
                    timeout_recorder.output_name
                )

            # check for stop
            if stop_event.is_set():
                break

            time.sleep(1)
    except Exception as e:
        status_callback((RecordingStatusCallback.RECORDING_ERROR, e))
