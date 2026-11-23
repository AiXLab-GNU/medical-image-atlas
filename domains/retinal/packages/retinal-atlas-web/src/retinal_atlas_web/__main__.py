"""Run the production WSGI server from any working directory."""
import argparse
import os

from waitress import serve

from . import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=os.environ.get('RETINAL_ATLAS_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('RETINAL_ATLAS_PORT', '8877')))
    parser.add_argument('--image-root', help='Directory containing the four provider image files')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    config = {'IMAGE_ROOT': args.image_root} if args.image_root else None
    print(f'Retinal atlas: http://{args.host}:{args.port}/', flush=True)
    serve(create_app(config), host=args.host, port=args.port, threads=4)


if __name__ == '__main__':
    main()
