from generate_images import infrasound_location
from obspy import UTCDateTime
from web import config

if __name__ == "__main__":
    missed = []
    START = UTCDateTime(2023, 1, 31, 19, 00, 0)
    STOP = UTCDateTime(2023, 1, 31, 19, 10, 0)
    RUN_END = START
    while RUN_END <= STOP:
        generator = infrasound_location(RUN_END)
        for volc_name, volc_info in config.VOLCS.items():
            try:
                generator.gen_volc_image(volc_name, volc_info)
            except Exception as e:
                print(e)
                missed.append(RUN_END)
                pass
        RUN_END = RUN_END + (10 * 60)
    print("****************RUN COMPLETE**************")
#    print(missed)
