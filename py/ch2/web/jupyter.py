from logging import getLogger

from werkzeug.utils import redirect

from ..jupyter.load import create_notebook
from ..jupyter.utils import get_template


log = getLogger(__name__)


class Jupyter:

    def __init__(self, controller):
        self.__controller = controller

    def __call__(self, request, s, template):
        log.info(f'Attempting to display template {template}')
        fn, spec = get_template(template)
        args = list(self.match_args(request.args, spec))
        log.debug(f'Template args: {args}')
        name = create_notebook(fn, self.__controller.notebook_dir(), self.__controller.database_path(),
                               args, {})
        url = f'{self.__controller.connection_url()}tree/{name}'
        log.debug(f'Redirecting to {url}')
        return redirect(url)

    def match_args(self, params, spec):
        # the HTTP parameters are not ordered, but the temp[late function args are
        for arg in spec.args:
            yield params[arg]