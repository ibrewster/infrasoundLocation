from generate_images import infrasound_location
from obspy import UTCDateTime
from web import config

from concurrent.futures import ProcessPoolExecutor


def runDate(RUN_END):
    missed = []
    generator = infrasound_location(RUN_END)
    for volc_name, volc_info in config.VOLCS.items():
        try:
            generator.gen_volc_image(volc_name, volc_info, False)
        except Exception as e:
            print(e)
            missed.append(RUN_END)
            pass

    return missed


if __name__ == "__main__":
    missed = []
    futures = []
    # 2022-11-24T03:00:00.000000Z
    START = UTCDateTime(2023, 1, 31, 3, 0, 0)
    STOP = UTCDateTime(2023, 1, 31, 18, 30, 0)
    RUN_END = START
    with ProcessPoolExecutor(max_workers = 6) as executor:
        while RUN_END <= STOP:
            future = executor.submit(runDate, RUN_END)
            RUN_END = RUN_END + (10 * 60)

    for future in futures:
        missed += future.result()

    print("****************RUN COMPLETE**************")
#    print(missed)



