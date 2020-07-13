from flask import Flask, send_from_directory

app = Flask(__name__)


@app.route("/<path:path>")
def local(path):
    return send_from_directory("site", path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--port", type=int, default=8080)

    args = parser.parse_args()

    port: int = args.port

    app.run(host="127.0.0.1", port=port)
