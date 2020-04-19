from ..json import JsonResponse
from ...commands.search import expanded_activities


class Search:

    def __call__(self, request, s, query):
        return JsonResponse(expanded_activities(s, query))
