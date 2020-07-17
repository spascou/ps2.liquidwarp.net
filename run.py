import webbrowser
from threading import Timer

from flask import Flask, send_from_directory

from generate.constants import SITE_DIRECTORY

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.route("/<path:path>")
def local(path):
    return send_from_directory(SITE_DIRECTORY, path)


def open_browser(port):
    url: str = f"http://127.0.0.1:{port}/index.html"
    webbrowser.open_new_tab(url)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--open", action="store_true")

    args = parser.parse_args()

    port: int = args.port

    if args.open is True:
        Timer(1, lambda: open_browser(port=port)).start()

    app.run(host="127.0.0.1", port=port)
