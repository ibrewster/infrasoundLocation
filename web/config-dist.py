# Config.py
# Configuration file for the infrasound calculations

IMG_DIR = "/tmp/infrasound"
SAVE_IMAGES = True
TIME_BUFFER = 10
AGC_PARAMS = None
TIME_METHOD = 'celerity'  # Choose either 'celerity' or 'fdtd'
STACK_METHOD = 'sum'  # Choose either 'sum', 'product', or 'semblance'
NETWORK = 'AV'
SOURCE = 'IRIS'
LOCATION = '*'
CHANNEL = 'BDF'
DECIMATION_RATE = 20

DETECT_THREASHOLD = .4

##########
# PostgreSQL DB for storing detections
##########
PG_SERVER = 'myserver.myhost.edu'
PG_DB = 'MyDBName'
PG_USER = 'MyUser'

VOLCS = {
    "pavlof": {
        "lon": -161.893047,  # [deg] Longitude of grid center
        "lat": 55.417833,   # [deg] Latitude of grid center
        "x_radius": 1000,   # [m] E-W grid radius (half of grid "width")
        "y_radius": 1000,   # [m] N-S grid radius (half of grid "height")
        "spacing": 25,      # [m] Grid spacing
        "station": 'PN7A,PV6A,PS4A,HAG,PS1A,PVV',
        "freq_min": .5,  # [Hz] Lower bandpass corner
        "freq_max": 7,  # [Hz] Upper bandpass corner
        "smooth_win": 1,    # [s] Smoothing window duration
    },
    "semi": {
        "lon": 179.585257,  # [deg] Longitude of grid center
        "lat": 51.935984,   # [deg] Latitude of grid center
        "x_radius": 10000,   # [m] E-W grid radius (half of grid "width")
        "y_radius": 10000,   # [m] N-S grid radius (half of grid "height")
        "spacing": 100,      # [m] Grid spacing
        "station": 'CERB,CESW,CEPE',
        "freq_min": 0.2,  # [Hz] Lower bandpass corner
        "freq_max": 5,  # [Hz] Upper bandpass corner
        "decimation_rate": 20,  # [Hz] New sampling rate to use for decimation
        "smooth_win": 2,    # [s] Smoothing window duration
    },
}
