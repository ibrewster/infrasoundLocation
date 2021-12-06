# Config.py
# Configuration file for the infrasound calculations

IMG_DIR = "/tmp/infrasound"
SAVE_IMAGES = True
TIME_BUFFER = 10
AGC_PARAMS = None
TIME_METHOD = 'celerity'  # Choose either 'celerity' or 'fdtd'
STACK_METHOD = 'sum'  # Choose either 'sum', 'product', or 'semblance'

VOLCS = {
    "pavlof": {
        "lon": -161.893047,  # [deg] Longitude of grid center
        "lat": 55.417833,   # [deg] Latitude of grid center
        "x_radius": 1000,   # [m] E-W grid radius (half of grid "width")
        "y_radius": 1000,   # [m] N-S grid radius (half of grid "height")
        "spacing": 25,      # [m] Grid spacing
        "source": 'IRIS',
        "network": "AV",
        "station": 'PN7A,PV6A,PS4A,HAG,PS1A,PVV',
        "location": "*",
        "channel": "BDF",
        "max_station_dist": 8,  # [km] Max. dist. from grid center to station (approx.)
        "freq_min": .5,  # [Hz] Lower bandpass corner
        "freq_max": 7,  # [Hz] Upper bandpass corner
        "decimation_rate": 20,  # [Hz] New sampling rate to use for decimation
        "smooth_win": 1,    # [s] Smoothing window duration
    },
}
