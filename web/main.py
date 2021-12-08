import flask
import glob
import os

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
    img_dir = config.IMG_DIR
    image_wildcard = os.path.join(img_dir, f'{volcano.lower()}*')
    listing = list(filter(os.path.isfile, glob.glob(image_wildcard)))
    listing.sort(key = os.path.getctime, reverse = True)

    file_groups = []
    # Group files by creation time. Since time may vary some, we need a "slush" amount
    ctime_slush = 120  # in seconds, two minutes
    prev_ctime = stop_time or 0
    newest_ctime = None
    next_ctime = None
    cur_group = []
    while len(file_groups) < count:
        try:
            file = listing.pop(0)
        except IndexError:
            if cur_group:
                file_groups.append(cur_group)
            break  # No more files to be had

        file_ctime = os.path.getctime(file)
        if stop_time is not None:
            # Start counting files once they are *older* than the stop_time
            if file_ctime > stop_time - ctime_slush:
                next_ctime = file_ctime + + (2 * ctime_slush)
                continue

        if abs(file_ctime - prev_ctime) > ctime_slush:
            if cur_group:
                file_groups.append(cur_group)
                cur_group = []

        cur_group.append(os.path.basename(file))
        prev_ctime = file_ctime
        if newest_ctime is None:
            newest_ctime = file_ctime

    return {"files": file_groups, "newest": newest_ctime, 'next': next_ctime}


@app.route("/imageBrowse")
def browse_images():
    volcano = flask.request.args['volc']
    count = int(flask.request.args.get('count', 1))
    stop = float(flask.request.args['stop'])

    return flask.jsonify(list_images(volcano, count, stop))


@app.route('/getImage/<image>')
def get_image(image):
    # This should not be used in production. Rather, Nginx
    # or whatever server is being used should be configured
    # to serve up requests to this path as static files from
    # the image directory directly.
    img_dir = config.IMG_DIR
    return flask.send_from_directory(img_dir, image, filename = image)
