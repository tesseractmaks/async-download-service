import argparse
import asyncio
import logging
import os

import aiohttp
import aiofiles

from dotenv import load_dotenv
from aiohttp import web, ClientConnectionError

load_dotenv()
INTERVAL_SECS = os.getenv("DELAY")
PATH = os.path.abspath(os.getcwd())
logging.basicConfig(level=logging.WARNING)


def get_arguments(PATH, INTERVAL_SECS):
    parser = argparse.ArgumentParser(
        description='The code add directory into archive.'
    )
    parser.add_argument(
        '-p',
        '--path',
        default=PATH,
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
        default=INTERVAL_SECS,
        type=int,
        help="Enable delay use arguments: '-d or --delay' set number"
    )

    args = parser.parse_args()
    if args.path:
        PATH = args.path
    if args.logging:
        logging.disable(logging.WARNING)
    if args.path:
        INTERVAL_SECS = args.delay
    return PATH, int(INTERVAL_SECS)


PATH, INTERVAL_SECS = get_arguments(PATH, int(INTERVAL_SECS))


async def archive(request):
    name = request.match_info.get('archive_hash', "Anonymous")
    current = os.path.dirname(f"./test_photos/{name}/")
    if not os.path.exists(current):
        raise aiohttp.web.HTTPNotFound(text=f"404 Not Found\n\nFileNotFound path not correct: {current}")

    try:
        process = await asyncio.create_subprocess_exec(
            "zip", f"{PATH}/photos", "-r", "./",
            f"./test_photos/{name}/",
            stdout=asyncio.subprocess.PIPE, cwd=current
        )
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/html'

        while True:
            await process.stdout.read(100 * 1024)
            logging.warning(f'Sending archive chunk...')
            await asyncio.sleep(int(INTERVAL_SECS))

            if process.stdout.at_eof():
                logging.warning(f'-- Success --')
                return response
    except(asyncio.CancelledError, ClientConnectionError):
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
