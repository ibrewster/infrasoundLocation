import flask
import glob
import math
import os

import psycopg

from collections import deque
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse

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
        cur.execute("SELECT TO_CHAR(d_time AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'),value,dist FROM detections WHERE volc=%s", (volcano, ))
        detections = cur.fetchall()

    x_dist = config.VOLCS[volcano]['x_radius_search']
    y_dist = config.VOLCS[volcano]['y_radius_search']
    max_dist = math.sqrt(x_dist ** 2 + y_dist ** 2)
    detections = tuple(zip(*detections))
    ret = {'max_dist': max_dist,
           'detections': detections, }
    return flask.jsonify(ret)


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
    file_time = file_time.replace(tzinfo = timezone.utc)
    return file_time.timestamp()


def decompose_date(date: datetime):
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")
    return (year, month, day)

def get_img_times_listing(base_dir, dir_date: datetime) -> set:
    year,month,day = decompose_date(dir_date)
    img_dir = os.path.join(base_dir, year, month, day)

    try:
        # Get a listing for the current day
        listing = {(img_dir, parse_file_time(x)) for x in os.scandir(img_dir)}
    except FileNotFoundError:
        listing = set()
        
    return listing
    
def get_img_times(base_dir, dir_date: datetime):
    listing = get_img_times_listing(base_dir, dir_date)
        
    # and *one* entry for the next day, so we don't get stuck
    dir_date += timedelta(days = 1)

    try:
        listing2 = sorted(get_img_times_listing(base_dir, dir_date),
                       key = lambda x: x[1])[0]
    
        listing.add(listing2)
    except IndexError:
        # No next day. No problem.
        pass

    listing = sorted(listing, key = lambda x: x[1], reverse = True)
    return listing


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


def get_prev(img_dir, img_dir_time, listing):
    try:
        day_dir, file_mtime = listing.pop(0)
    except IndexError:
        # Look at the previous day
        img_dir_time -= timedelta(days = 1)
        listing = get_img_times(img_dir, img_dir_time)
        try:
            # Discard the first entry, as it is for the next day.
            listing.pop(0)
            day_dir, file_mtime = listing.pop(0)
        except IndexError:
            return None, None, []
        
    return day_dir, file_mtime, listing


def list_images(volcano, count, stop_time: datetime = None):
    # stop_time is inclusive, any files equal to said stop time will be included.
    if stop_time is None:
        img_dir_time = datetime.utcnow() + timedelta(minutes = 10)
    else:
        img_dir_time = stop_time
        stop_time = stop_time.timestamp()

    img_dir = os.path.join(config.IMG_DIR, volcano)

    file_dates = []
    if count > 1:
        prev_time_opts = deque(maxlen = count - 1)
    else:
        prev_time_opts = None

    next_time = None
    prev_time = None

    listing = get_img_times(img_dir, img_dir_time)

    while len(file_dates) < count:
        day_dir, file_mtime,listing = get_prev(img_dir, img_dir_time, listing)
        if file_mtime is None:
            # No previous day. Out of images.
            break  # No more files to be had

        if stop_time is not None:
            # Start counting files once they are *older* than the stop_time
            # That is, do nothing (continue) as long as the file is as new
            # as or newer than the stop time.
            if file_mtime > stop_time:
                next_time = file_mtime
                continue

        if prev_time_opts is not None:
            prev_time_opts.appendleft(file_mtime)

        # Get a listing of files for this time
        time_obj = datetime.utcfromtimestamp(file_mtime).replace(tzinfo = timezone.utc)
        time_str = time_obj.strftime('%Y%m%d_%H%M')
        glob_pattern = f"{day_dir}/{volcano}_{time_str}_*.png"
        file_group = [os.path.basename(x) for x in glob.glob(glob_pattern)]
        file_dates.append(file_group)

    # if count == 1:
        # day_dir, prev_time, listing = get_prev(img_dir, img_dir_time, listing)
    # else:
    
    # if file_mtime is none, we ran out of files while navigating backward before we 
    # even had as many as we wanted, so clearly no previous files are available.
    if file_mtime is None:
        prev_time = None
        
    else:
        # Get what would be the next file back if we kept going.
        day_dir, prev_time, listing = get_prev(img_dir, img_dir_time, listing)
            
        # If there is no next file back, then leave prev_time as None.
        # If there is, but we are only showing 1 image, then the next 
        # file back is the "target" file for navigating back, and we 
        # can just leave the prev_time value as-is.
        if prev_time is not None and count > 1:
            # if count>1, then we want to use the previously stored 
            # "opt" value for prev_time.
            try:
                prev_time = prev_time_opts.pop()
            except:
                prev_time = None

    return {"files": file_dates, "prev": prev_time, 'next': next_time}


@app.route("/imageBrowse")
def browse_images():
    volcano = flask.request.args['volc']
    count = int(flask.request.args.get('count', 1))
    try:
        stop = float(flask.request.args['stop'])
        stop = datetime.utcfromtimestamp(stop).replace(tzinfo = timezone.utc)
    except ValueError:
        stop = parse(flask.request.args['stop']).replace(tzinfo = timezone.utc)

    return flask.jsonify(list_images(volcano, count, stop))


@app.route('/getImage/<volc>/<year>/<month>/<day>/<image>')
def get_image(volc, year, month, day, image):
    # This should not be used in production. Rather, Nginx
    # or whatever server is being used should be configured
    # to serve up requests to this path as static files from
    # the image directory directly.
    img_dir = os.path.join(config.IMG_DIR, volc, year, month, day)
    return flask.send_from_directory(img_dir, image)
