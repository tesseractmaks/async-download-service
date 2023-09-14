import argparse
import asyncio
import logging
import os

import aiohttp
import aiofiles

from dotenv import load_dotenv
from aiohttp import web, ClientConnectionError

load_dotenv()
logging.basicConfig(level=logging.WARNING)


def get_arguments(path, internal_secs):
    parser = argparse.ArgumentParser(
        description='The code add directory into archive.'
    )
    parser.add_argument(
        '-p',
        '--path',
        default=path,
        type=str,
        help="Set path to catalog use arguments: '-p or --path'"
    )
    parser.add_argument(
        '-l',
        '--logging',
        default=0,
        type=int,
        help="Enable logging use arguments: '-l or --logging' set 1"
    )
    parser.add_argument(
        '-d',
        '--delay',
        default=internal_secs,
        type=int,
        help="Enable delay use arguments: '-d or --delay' set number"
    )

    args = parser.parse_args()
    if args.path:
        path = args.path
    if args.logging:
        logging.disable(logging.WARNING)
    if args.path:
        internal_secs = args.delay
    return path, int(internal_secs)


async def archive(request):
    internal_secs = os.getenv("DELAY")
    path = os.path.abspath(os.getcwd())
    path, internal_secs = get_arguments(path, int(internal_secs))
    archive_hash = request.match_info['archive_hash']
    current = os.path.dirname(f"./test_photos/{archive_hash}/")
    if not os.path.exists(current):
        raise aiohttp.web.HTTPNotFound(text=f"404 Not Found\n\nFileNotFound path not correct: {current}")

    process = await asyncio.create_subprocess_exec(
        "zip", f"{path}/photos", "-r", "./",
        f"./test_photos/{archive_hash}/",
        stdout=asyncio.subprocess.PIPE, cwd=current
    )
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    try:
        while process.stdout.at_eof():
            await process.stdout.read(100 * 1024)
            logging.warning(f'Sending archive chunk...')
            await asyncio.sleep(int(internal_secs))
        logging.warning(f'-- Success --')
    except asyncio.CancelledError:
        logging.warning(f'Download was interrupted')
        process.kill()
        raise
    except(ClientConnectionError, SystemExit, Exception, KeyboardInterrupt):
        logging.warning(f'Download was interrupted')
        process.kill()
    finally:
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes(
        [
            web.get('/', handle_index_page),
            web.get('/archive/{archive_hash}/', archive),
        ]
    )
    web.run_app(app)
