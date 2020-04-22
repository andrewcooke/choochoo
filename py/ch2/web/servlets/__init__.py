from collections import defaultdict
from os.path import splitext


class ContentType:

    CONTENT_TYPE = defaultdict(lambda: 'text/plain', {
        'js': 'text/javascript',
        'html': 'text/html',
        'css': 'text/css',
        'png': 'image/png'
    })

    def set_content_type(self, response, name):
        ext = splitext(name)[1].lower()
        if ext:
            ext = ext[1:]
        response.content_type = self.CONTENT_TYPE[ext]
