import flask
import os

import psycopg

from collections import deque
from datetime import datetime, timezone, timedelta

from . import app, config


@app.route('/')
def index():
    volcs = list(config.VOLCS.keys())
    return flask.render_template("index.html", volcs = volcs)

@app.route('/getDetections/<volcano>')
def detections(volcano):
    with psycopg.connect(host = config.PG_SERVER, dbname = config.PG_DB,
                         user = config.PG_USER, password = config.PG_PASS) as db_conn:
        cur = db_conn.cursor()
        cur.execute("SELECT TO_CHAR(d_time,'YYYY-MM-DD HH24:MI:SS'),value,dist FROM detections WHERE volc=%s", (volcano, ))
        detections = cur.fetchall()
    detections = tuple(zip(*detections))
    return flask.jsonify(detections)
    
@app.route("/getImages")
def get_images():
    volcano = flask.request.args['volc']
    count = int(flask.request.args.get('count', 1))
    return flask.jsonify(list_images(volcano, count))


def parse_file_time(file):
    parts = file.name.split("_")
    file_date = parts[1]
    file_time = parts[2]
    
    file_time = datetime.strptime(f"{file_date}T{file_time}",
                                  "%Y%m%dT%H%M")
    return file_time.timestamp()
    
def get_img_list(base_dir, dir_date: datetime):
    year = dir_date.strftime("%Y")
    month = dir_date.strftime("%m")
    day = dir_date.strftime("%d")
    img_dir = os.path.join(base_dir, year, month, day)

    try:
        listing = [(x, parse_file_time(x)) for x in os.scandir(img_dir)]
    except FileNotFoundError:
        return []
    
    listing.sort(key = lambda x: x[1], reverse = True)
    return listing

def list_images(volcano, count, stop_time: datetime = None):
    # stop_time is exclusive, any files equal to said stop time will not be included.
    if stop_time is None:
        img_dir_time = datetime.utcnow() + timedelta(minutes = 10)
    else:
        img_dir_time = stop_time
        stop_time = stop_time.timestamp()
        

    img_dir = os.path.join(config.IMG_DIR, volcano)

    file_groups = []
    # Group files by creation time. Since time may vary some, we need a "slush" amount
    ctime_slush = 120  # in seconds, two minutes
    prev_mtime = 0
    newest_ctime = None
    cur_group = []
    m_times = deque(maxlen = 2)
    next_mtime = None
    
    listing = get_img_list(img_dir, img_dir_time)
    
    while len(file_groups) < count:
        try:
            file, file_mtime = listing.pop(0)
        except IndexError:
            # Look at the previous day
            img_dir_time -= timedelta(days = 1)
            listing = get_img_list(img_dir, img_dir_time)
            try:
                file, file_mtime = listing.pop(0)
            except IndexError:
                # No previous day. Out of images.
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
        stop = datetime.utcfromtimestamp(stop)
    except ValueError:
        stop = datetime.strptime(flask.request.args['stop'],
                                 '%m/%d/%Y %H:%M').replace(tzinfo = timezone.utc)
        stop += timedelta(minutes = 10)

    return flask.jsonify(list_images(volcano, count, stop))


@app.route('/getImage/<volc>/<year>/<month>/<day>/<image>')
def get_image(volc, year, month, day, image):
    # This should not be used in production. Rather, Nginx
    # or whatever server is being used should be configured
    # to serve up requests to this path as static files from
    # the image directory directly.
    img_dir = os.path.join(config.IMG_DIR, volc, year, month, day)
    return flask.send_from_directory(img_dir, image)
