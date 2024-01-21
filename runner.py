import time

from postprocessing import PostProcessing
from reader import LogChecker
from recorder import TimeoutRecording


def run(settings):
    log_checker = LogChecker(
        settings["LOG_DIRECTORY"]
    )

    timeout_recorder = TimeoutRecording(
        host=settings['OBS_HOST'],
        port=int(settings['OBS_PORT']),
        password=settings['OBS_PASSWORD'],
        timeout=int(settings["TIMEOUT"])
    )

    pp = PostProcessing(settings)

    while True:
        if log_checker.check():
            timeout_recorder.start()
            timeout_recorder.set_timeout()

        if timeout_recorder.check_timeout():
            pp.process(timeout_recorder.replay_path, timeout_recorder.replay_path, settings["OUTPUT_DIR"],timeout_recorder.output_name)

        time.sleep(1)
