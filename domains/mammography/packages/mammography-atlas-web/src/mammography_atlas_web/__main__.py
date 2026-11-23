"""Run the production WSGI server from any working directory."""
import argparse
import os

from waitress import serve

from . import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=os.environ.get('MAMMOGRAPHY_ATLAS_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('MAMMOGRAPHY_ATLAS_PORT', '8879')))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    print(f'Mammography atlas: http://{args.host}:{args.port}/', flush=True)
    serve(create_app(), host=args.host, port=args.port, threads=4)


if __name__ == '__main__':
    main()
