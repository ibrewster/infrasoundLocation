# %% (1) Define grid
import os

import numpy
import psycopg
import utm

import matplotlib.pyplot as plt

from datetime import timezone

from obspy import UTCDateTime
from rtm import (
    define_grid,
    produce_dem,
    process_waveforms,
    grid_search,
    plot_time_slice,
    get_peak_coordinates,
    plot_st,
    calculate_time_buffer
)

try:
    from waveform_collection.waveform_collection import gather_waveforms
except ImportError:
    from waveform_collection import gather_waveforms

from web import config

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
        self.TIME_METHOD = config.TIME_METHOD
        self.STACK_METHOD = config.STACK_METHOD
        endtime = UTCDateTime.now()
        end_minute = endtime.minute - (endtime.minute % 10)

        self.ENDTIME = end or endtime.replace(minute = end_minute, second = 0, microsecond = 0)
        print("End time set to:", self.ENDTIME)
        self.STARTTIME = start or self.ENDTIME - 10 * 60  # 10 minutes

    def gen_volc_image(self, volc_name, volc_info, SAVE_DB = True):
        NETWORK = config.NETWORK
        SOURCE = config.SOURCE
        LOCATION = config.LOCATION
        CHANNEL = config.CHANNEL

        LON_0 = volc_info['lon']  # [deg] Longitude of grid center
        LAT_0 = volc_info['lat']  # [deg] Latitude of grid center
        X_RADIUS_NET = volc_info['x_radius_net']  # [m] E-W grid radius (half of grid "width")
        Y_RADIUS_NET = volc_info['y_radius_net']  # [m] N-S grid radius (half of grid "height")
        SPACING_NET = volc_info['spacing_net']    # [m] Grid spacing

        network_grid = define_grid(lon_0=LON_0, lat_0=LAT_0, x_radius=X_RADIUS_NET,
                                   y_radius=Y_RADIUS_NET, spacing=SPACING_NET, projected=True,
                                   plot_preview=False)

        network_dem = produce_dem(network_grid, external_file=None, plot_output=False)

        X_RADIUS_SEARCH = volc_info['x_radius_search']  # [m] E-W grid radius (half of grid "width")
        Y_RADIUS_SEARCH = volc_info['y_radius_search']  # [m] N-S grid radius (half of grid "height")
        SPACING_SEARCH = volc_info['spacing_search']    # [m] Grid spacing

        search_grid = define_grid(lon_0=LON_0, lat_0=LAT_0, x_radius=X_RADIUS_SEARCH,
                                  y_radius=Y_RADIUS_SEARCH, spacing=SPACING_SEARCH, projected=True,
                                  plot_preview=False)

        search_dem = produce_dem(search_grid, external_file=None, plot_output=False)

        # %% (2) Grab and process the data

        # Data collection parameters
        STATION = volc_info['station']

        FREQ_MIN = volc_info['freq_min']  # [Hz] Lower bandpass corner
        FREQ_MAX = volc_info['freq_max']   # [Hz] Upper bandpass corner

        DECIMATION_RATE = config.DECIMATION_RATE    # [Hz] New sampling rate to use for decimation
        SMOOTH_WIN = volc_info['smooth_win']        # [s] Smoothing window duration

        # Automatically determine appropriate time buffer in s
        MAX_STATION_DIST = volc_info['max_station_dist']  # [km] Max. dist. from grid center to station (approx.)
        time_buffer = calculate_time_buffer(network_grid, MAX_STATION_DIST)

        st = gather_waveforms(source=SOURCE, network=NETWORK, station=STATION,
                              location=LOCATION, channel=CHANNEL, starttime=self.STARTTIME,
                              endtime=self.ENDTIME, time_buffer=time_buffer)

        st.remove_sensitivity()

        nsta = len(st)

        AGC_WIN = config.AGC_WIN
        #AGC_PARAMS = None
        AGC_PARAMS = dict(win_sec=AGC_WIN, method='walker')

        st_proc = process_waveforms(st, freqmin=FREQ_MIN, freqmax=FREQ_MAX,
                                    envelope=True, smooth_win=SMOOTH_WIN,
                                    agc_params=AGC_PARAMS,
                                    decimation_rate=DECIMATION_RATE, normalize=True,
                                    plot_steps=False)

        # %% (3) Perform grid search
        TIME_KWARGS = {'celerity': config.CEL, 'dem': search_dem}

        # STACK_METHOD = 'semblance'  # Choose either 'sum', 'product', or 'semblance'
        #TIME_KWARGS = {'celerity': 338, 'dem': network_dem, 'window': 10}

        S = grid_search(processed_st=st_proc, grid=search_grid, time_method=self.TIME_METHOD,
                        starttime=self.STARTTIME, endtime=self.ENDTIME,
                        stack_method=self.STACK_METHOD, **TIME_KWARGS)

        # Normalize to number of stations
        S.data = S.data / nsta

        PK_HT = config.PEAK_HEIGHT
        MIN_TIME = AGC_WIN
        PROM = config.PROMINANCE

        # Find and save any detections
        time_max, y_max, x_max, peaks, props = get_peak_coordinates(
            S, global_max=False,
            height=PK_HT,
            min_time=MIN_TIME,
            prominence=PROM,
            unproject=True
        )

        det_times = [x.datetime.replace(tzinfo = timezone.utc) for x in time_max]
        det_lon = numpy.asarray(x_max)
        det_lat = numpy.asarray(y_max)
        det_values = props['peak_heights']

        if len(det_values) > 0 and SAVE_DB and nsta >= 3:
            det_volc = [volc_name] * len(det_values)
            gc_x, gc_y, _, _ = utm.from_latlon(*reversed(S.grid_center))
            det_x, det_y, _, _ = utm.from_latlon(det_lat, det_lon)

            # Distance to center in meters (a^2+b^2=c^2)
            det_dist = numpy.sqrt(numpy.square(det_x - gc_x) + numpy.square(det_y - gc_y))

            db_data = list(zip(det_volc, det_values, det_times, det_dist))

            ##### DEBUG
            print("Saving detections to DB:", db_data)

            with psycopg.connect(host = config.PG_SERVER, dbname = config.PG_DB,
                                 user = config.PG_USER) as db_conn:
                curr = db_conn.cursor()
                curr.executemany("INSERT INTO detections (volc,value,d_time,dist) VALUES (%s,%s,%s,%s)",
                                 db_data)
                db_conn.commit()

        # fig_rec = plot_record_section(st_proc, origin_time=time_max,
                # source_location=(y_max, x_max),
                # plot_celerity=S.celerity, label_waveforms=True)

        # fig_rec.axes[0].set_ylim(bottom=6)  # Start at this distance (km) from source

        if self.ISAVE:
            from matplotlib import rcParams
            # %% (4) Plot

            # This should be the default, but go ahead and be explicit about it anyway just to be sure.
            rcParams.update({'font.size': 10})

            fig_st = plot_st(st, filt=[FREQ_MIN, FREQ_MAX], equal_scale=False,
                             remove_response=False, label_waveforms=True)

            fig_slice = plot_time_slice(S, st_proc, label_stations=True, dem=network_dem,
                                        plot_peak=True, xy_grid=X_RADIUS_NET, cont_int = 50,
                                        annot_int = 500)

            fig_st.set_dpi(200)
            fig_slice.set_dpi(200)

            # Adjust fig_slice to get rid of excess white space
            fig_slice.set_size_inches(8, 10.465)
            fig_slice.subplots_adjust(top = .945, bottom = .06, hspace = .2)

            colorbar = fig_slice.get_children()[-1]
            cb_pos = colorbar.get_position()
            cb_pos.y1 = 0.9405
            cb_pos.y0 = 0.347
            cb_pos.x0 = .915
            cb_pos.x1 = .935
            colorbar.set_position(cb_pos)
            ax = fig_slice.axes[0]
            im = ax.get_images()
            im[0].set_clim(.4, 1)

            img_time = st_proc[0].stats.starttime
            tmstr = UTCDateTime.strftime(img_time, '%Y%m%d_%H%M')
            year = UTCDateTime.strftime(img_time, '%Y')
            month = UTCDateTime.strftime(img_time, '%m')
            day = UTCDateTime.strftime(img_time, '%d')
            img_dir = os.path.join(self.SVDIR, volc_name, year, month, day)
            os.makedirs(img_dir, exist_ok = True)

            rcParams.update({'font.size': 10})

            combined_file = os.path.join(img_dir, f'{volc_name}_{tmstr}_combined.png')

            c1 = fig_slice.canvas
            c2 = fig_st.canvas

            c1.draw()
            c2.draw()

            a1 = numpy.array(c1.buffer_rgba())
            a2 = numpy.array(c2.buffer_rgba())

            a = numpy.vstack((a1, a2))

            dpi = 800
            height = fig_slice.get_figheight() + fig_st.get_figheight()
            fig_c, ax_c = plt.subplots(figsize=(8, height), dpi = dpi)
            fig_c.subplots_adjust(0, 0, 1, 1)
            ax_c.set_axis_off()
            ax_c.matshow(a)

            fig_c.savefig(combined_file, dpi = 200, pad_inches = 0.04, bbox_inches='tight')
            plt.close('all')

            # wfs_file = os.path.join(img_dir, f'{volc_name}_{tmstr}_wfs.png')
            # slice_file = os.path.join(img_dir, f'{volc_name}_{tmstr}_slice.png')
            # # recsec_file = os.path.join(img_dir, f'{volc_name}_{tmstr}_recsec.png')

            # fig_st.savefig(wfs_file, dpi=200,
            # bbox_inches='tight', pad_inches=0.04)

            # # fig_slice.set_size_inches(5,5)
            # fig_slice.savefig(slice_file, dpi=200,
            # bbox_inches='tight', pad_inches=0.04)

            # fig_rec.savefig(recsec_file, dpi=200,
            # bbox_inches='tight', pad_inches=0.1)


if __name__ == "__main__":
    generator = infrasound_location()
    for volc_name, volc_info in config.VOLCS.items():
        generator.gen_volc_image(volc_name, volc_info)
