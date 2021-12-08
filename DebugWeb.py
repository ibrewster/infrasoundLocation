from web import app

if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host = "0.0.0.0", use_reloader = True, use_debugger = False)
