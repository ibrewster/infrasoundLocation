# %% (1) Define grid
import os

from obspy import UTCDateTime
from rtm import (
    define_grid,
    produce_dem,
    process_waveforms,
    grid_search,
    plot_time_slice,
    plot_record_section,
    get_peak_coordinates,
    plot_st
)

from waveform_collection import gather_waveforms

import config

"""
To obtain the below file from OpenTopography, run the command

$ curl https://cloud.sdsc.edu/v1/AUTH_opentopography/hosted_data/OTDS.072019.4326.1/raster/DEM_WGS84.tif -o DEM_WGS84.tif

or simply paste the above URL in a web browser. Alternatively, specify None to
automatically download and use 1 arc-second STRM data.
"""
#EXTERNAL_FILE = 'DEM_WGS84.tif'


class infrasound_location:
    def __init__(self, end = None, start = None):
        self.SVDIR = config.IMG_DIR
        self.ISAVE = config.SAVE_IMAGES
        self.TIME_BUFFER = config.TIME_BUFFER
        self.AGC_PARAMS = config.AGC_PARAMS
        self.TIME_METHOD = config.TIME_METHOD
        self.STACK_METHOD = config.STACK_METHOD
        end = UTCDateTime.now()
        end_minute = end.minute - (end.minute % 10)

        self.ENDTIME = end or end.replace(minute = end_minute, second = 0, microsecond = 0)
        self.STARTTIME = start or self.ENDTIME - 10 * 60  # 10 minutes

    def gen_volc_image(self, volc_name, volc_info):
        LON_0 = volc_info['lon']  # [deg] Longitude of grid center
        LAT_0 = volc_info['lat']  # [deg] Latitude of grid center
        X_RADIUS = volc_info['x_radius']  # [m] E-W grid radius (half of grid "width")
        Y_RADIUS = volc_info['y_radius']  # [m] N-S grid radius (half of grid "height")
        SPACING = volc_info['spacing']    # [m] Grid spacing

        network_grid = define_grid(lon_0=LON_0, lat_0=LAT_0, x_radius=X_RADIUS,
                                   y_radius=Y_RADIUS, spacing=SPACING, projected=True)

        network_dem = produce_dem(network_grid, external_file=None)

        # %% (2) Grab and process the data

        # Data collection parameters
        SOURCE = volc_info['source']
        NETWORK = volc_info['network']
        STATION = volc_info['station']
        LOCATION = volc_info['location']
        CHANNEL = volc_info['channel']

        # MAX_STATION_DIST = volc_info['max_station_dist']  # [km] Max. dist. from grid center to station (approx.)

        FREQ_MIN = volc_info['freq_min']  # [Hz] Lower bandpass corner
        FREQ_MAX = volc_info['freq_max']   # [Hz] Upper bandpass corner

        DECIMATION_RATE = volc_info['decimation_rate']  # [Hz] New sampling rate to use for decimation
        SMOOTH_WIN = volc_info['smooth_win']        # [s] Smoothing window duration

        # Automatically determine appropriate time buffer in s
        #time_buffer = calculate_time_buffer(network_grid, MAX_STATION_DIST)
        time_buffer = 10

        st = gather_waveforms(source=SOURCE, network=NETWORK, station=STATION,
                              location=LOCATION, channel=CHANNEL, starttime=self.STARTTIME,
                              endtime=self.ENDTIME, time_buffer=time_buffer)

        st.remove_sensitivity()

        # nsta = len(st)

        st_proc = process_waveforms(st, freqmin=FREQ_MIN, freqmax=FREQ_MAX,
                                    envelope=True, smooth_win=SMOOTH_WIN,
                                    agc_params=self.AGC_PARAMS,
                                    decimation_rate=DECIMATION_RATE, normalize=True, plot_steps=False)

        # %% (3) Perform grid search
        TIME_KWARGS = {'celerity': 335, 'dem': network_dem}

        # STACK_METHOD = 'semblance'  # Choose either 'sum', 'product', or 'semblance'
        #TIME_KWARGS = {'celerity': 338, 'dem': network_dem, 'window': 10}

        S = grid_search(processed_st=st_proc, grid=network_grid, time_method=self.TIME_METHOD,
                        starttime=self.STARTTIME, endtime=self.ENDTIME,
                        stack_method=self.STACK_METHOD, **TIME_KWARGS)

        # %% (4) Plot
        fig_st = plot_st(st, filt=[FREQ_MIN, FREQ_MAX], equal_scale=False,
                         remove_response=False, label_waveforms=True)

        fig_slice = plot_time_slice(S, st_proc, label_stations=True, dem=network_dem,
                                    plot_peak=True, xy_grid=X_RADIUS)

        time_max, y_max, x_max, peaks, props = get_peak_coordinates(S, global_max=True,
                                                                    unproject=S.UTM)

        fig_rec = plot_record_section(st_proc, origin_time=time_max,
                                      source_location=(y_max, x_max),
                                      plot_celerity=S.celerity, label_waveforms=True)

        fig_rec.axes[0].set_ylim(bottom=6)  # Start at this distance (km) from source

        if self.ISAVE:
            os.makedirs(self.SVDIR, exist_ok = True)
            from matplotlib import rcParams

            rcParams.update({'font.size': 12})

            tmstr = UTCDateTime.strftime(st_proc[0].stats.starttime, '%Y%m%d_%H%M')

            wfs_file = os.path.join(self.SVDIR, f'{volc_name}_{tmstr}_wfs.png')
            slice_file = os.path.join(self.SVDIR, f'{volc_name}_{tmstr}_slice.png')
            recsec_file = os.path.join(self.SVDIR, f'{volc_name}_{tmstr}_recsec.png')

            fig_st.savefig(wfs_file, dpi=200,
                           bbox_inches='tight', pad_inches=0.04)

            # fig_slice.set_size_inches(5,5)
            fig_slice.savefig(slice_file, dpi=200,
                              bbox_inches='tight', pad_inches=0.04)

            fig_rec.savefig(recsec_file, dpi=200,
                            bbox_inches='tight', pad_inches=0.1)


if __name__ == "__main__":
    generator = infrasound_location()
    for volc_name, volc_info in config.VOLCS.items():
        generator.gen_volc_image(volc_name, volc_info)
