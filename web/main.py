import flask
import glob
import os

from collections import deque
from datetime import datetime, timezone, timedelta

from . import app, config


@app.route('/')
def index():
    volcs = list(config.VOLCS.keys())
    return flask.render_template("index.html", volcs = volcs)


@app.route("/getImages")
def get_images():
    volcano = flask.request.args['volc']
    count = int(flask.request.args.get('count', 1))
    return flask.jsonify(list_images(volcano, count))


def list_images(volcano, count, stop_time = None):
    # stop_time is exclusive, any files equal to said stop time will not be included.
    img_dir = config.IMG_DIR
    image_wildcard = os.path.join(img_dir, f'{volcano.lower()}*')
    listing = list(filter(os.path.isfile, glob.glob(image_wildcard)))
    listing = [(x, os.path.getmtime(x)) for x in listing]
    listing.sort(key = lambda x: x[1], reverse = True)

    file_groups = []
    # Group files by creation time. Since time may vary some, we need a "slush" amount
    ctime_slush = 120  # in seconds, two minutes
    prev_mtime = 0
    newest_ctime = None
    cur_group = []
    m_times = deque(maxlen = 2)
    next_mtime = None
    while len(file_groups) < count:
        try:
            file, file_mtime = listing.pop(0)
        except IndexError:
            if cur_group:
                file_groups.append(cur_group)
            break  # No more files to be had

        new_group = abs(file_mtime - prev_mtime) > ctime_slush
        if stop_time is not None and new_group:
            m_times.append(prev_mtime)

        prev_mtime = file_mtime
        if stop_time is not None:
            # Start counting files once they are *older* than the stop_time
            # That is, do nothing (continue) as long as the file is as new
            # as or newer than the stop time.
            if file_mtime > stop_time - ctime_slush:
                continue

        if new_group:
            if cur_group:
                file_groups.append(cur_group)
                cur_group = []

        cur_group.append(os.path.basename(file))
        if newest_ctime is None:
            newest_ctime = file_mtime
            if m_times:
                next_mtime = m_times.popleft()

    return {"files": file_groups, "newest": newest_ctime, 'next': next_mtime}


@app.route("/imageBrowse")
def browse_images():
    volcano = flask.request.args['volc']
    count = int(flask.request.args.get('count', 1))
    try:
        stop = float(flask.request.args['stop'])
    except ValueError:
        stop = datetime.strptime(flask.request.args['stop'],
                                 '%m/%d/%Y %H:%M').replace(tzinfo = timezone.utc)
        stop += timedelta(minutes = 10)
        stop = stop.timestamp()

    return flask.jsonify(list_images(volcano, count, stop))


@app.route('/getImage/<image>')
def get_image(image):
    # This should not be used in production. Rather, Nginx
    # or whatever server is being used should be configured
    # to serve up requests to this path as static files from
    # the image directory directly.
    img_dir = config.IMG_DIR
    return flask.send_from_directory(img_dir, image, filename = image)
