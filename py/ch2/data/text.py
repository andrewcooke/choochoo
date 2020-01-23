
from textblob import TextBlob


def wordlist(source, src, dest=None):
    if not dest:
        dest = src
    source[dest] = source[src].apply(lambda text: TextBlob(text).words if text is not None else [])
    source[dest] = source[dest].apply(lambda words: [w.lower() for w in words])


class WeightedScorer:

    def __init__(self, intensifiers, terms, gamma=0):
        self._intensifiers = intensifiers
        self._terms = terms
        self._gamma = gamma

    def score_words(self, words):
        score = 0
        for i, word in enumerate(words):
            delta = 0
            if word in self._terms:
                if i and words[i-1] in self._intensifiers:
                    if not i-1 or words[i-2] != 'no':
                        delta = self._intensifiers[words[i-1]] * self._terms[word]
                elif not i or words[i-1] != 'no':
                    delta = self._terms[word]
                # print(word, delta)
                score += delta
        if words:
            return score / len(words) ** self._gamma
        else:
            return 0

    def score_all(self, source, words, score):
        source[score] = source[words].apply(self.score_words)


