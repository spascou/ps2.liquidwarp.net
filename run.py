import webbrowser
from threading import Timer

from flask import Flask, send_from_directory

from generate.constants import SITE_DIRECTORY

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.route("/<path:path>")
def local(path):
    return send_from_directory(SITE_DIRECTORY, path)


def open_browser():
    url: str = f"http://127.0.0.1:{port}/index.html"
    webbrowser.open_new_tab(url)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--port", type=int, default=8080)

    args = parser.parse_args()

    port: int = args.port

    Timer(1, open_browser).start()

    app.run(host="127.0.0.1", port=port)
