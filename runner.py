import time

from postprocessing import PostProcessing
from reader import LogChecker
from recorder import TimeoutRecording


def run(settings, status_callback, stop_event):
    try:
        log_checker = LogChecker(
            settings["LOG_DIR"]
        )

        timeout_recorder = TimeoutRecording(
            host=settings['OBS_HOST'],
            port=int(settings['OBS_PORT']),
            password=settings['OBS_PASSWORD'],
            timeout=int(settings["TIMEOUT"])
        )

        pp = PostProcessing(
            concatenate=bool(settings["CONCATENATE_OUTPUTS"]),
            delete=bool(settings["DELETE_ORIGINALS"]),
            status_callback=status_callback
        )
    except Exception as e:
        status_callback(str(e))
    else:
        status_callback("recording_ready")

    while True:
        if log_checker.check():
            if timeout_recorder.set_timeout():
                status_callback("recording_start")

        if timeout_recorder.check_timeout():
            status_callback("recording_end")
            pp.process(
                timeout_recorder.replay_path,
                timeout_recorder.recording_path,
                settings["OUTPUT_DIR"],
                timeout_recorder.output_name
            )

        # check for stop
        if stop_event.is_set():
            break

        time.sleep(0.3)
