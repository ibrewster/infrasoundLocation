from generate_images import infrasound_location
from obspy import UTCDateTime
from web import config

if __name__ == "__main__":
    START = UTCDateTime(2022, 10, 17, 0, 0, 0)
    STOP = UTCDateTime(2022, 11, 20, 0, 0, 0)
    RUN_END = START
    while RUN_END <= STOP:
        generator = infrasound_location(RUN_END)
        for volc_name, volc_info in config.VOLCS.items():
            generator.gen_volc_image(volc_name, volc_info)
        RUN_END = RUN_END + (10 * 60)