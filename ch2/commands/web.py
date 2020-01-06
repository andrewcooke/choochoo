
from .args import SUB_COMMAND, SERVICE, STOP, START, STATUS
from ..web.server import WebController


def web(args, system, db):
    '''
    TODO
    '''
    cmd = args[SUB_COMMAND]
    controller = WebController(args, system)
    if cmd == SERVICE:
        controller.service()
    elif cmd == STATUS:
        controller.status()
    elif cmd == START:
        controller.start()
    elif cmd == STOP:
        controller.stop()
