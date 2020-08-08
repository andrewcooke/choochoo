from logging import getLogger

from werkzeug.utils import redirect

from ...jupyter.load import create_notebook
from ...jupyter.utils import get_template

log = getLogger(__name__)


class Jupyter:

    def __init__(self, config, controller):
        self.__config = config
        self.__controller = controller

    def __call__(self, request, s, template):
        log.info(f'Attempting to display template {template}')
        fn, spec = get_template(template)
        args = [request.args[arg] for arg in spec.args]  # order
        log.debug(f'Template args: {args}')
        name = create_notebook(self.__config, fn, args)
        url = f'{self.__controller.connection_url()}tree/{name}'
        log.debug(f'Redirecting to {url}')
        return redirect(url)
