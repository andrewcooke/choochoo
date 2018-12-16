
from abc import ABC, abstractmethod
from collections import defaultdict


class DBSCAN(ABC):

    def __init__(self, log, epsilon, minpts):
        self._log = log
        self.__epsilon = epsilon
        self.__minpts = minpts

    def run(self, candidates):
        count, label = self.scan(candidates)
        return sorted(self.prune(count, label), reverse=True,
                      key=lambda g: len(g) + (min(g) / max(g)))  # try to give repeatability

    def prune(self, count, label):
        index = defaultdict(list)
        for key in label.keys():
            if label[key]:
                index[label[key]].append(key)
        for i in range(count):
            if len(index[i+1]) < self.__minpts:
                del index[i+1]
        return list(index.values())

    def scan(self, candidates):
        label = defaultdict(lambda: None)
        count = 0
        for candidate in candidates:
            if label[candidate] is None:
                neighbours = list(self.neighbourhood(candidate, self.__epsilon))
                # self._log.debug('Candidate %s has %d initial neighbours' % (candidate, len(neighbours)))
                if len(neighbours) >= self.__minpts:
                    count += 1
                    # self._log.debug('Candidate %s is nucleus of group %d' % (candidate, count))
                    label[candidate] = count
                    self.grow(count, neighbours, label)
                else:
                    label[candidate] = 0
        return count, label

    def grow(self, count, stack, label):
        n = 0
        while stack:
            candidate = stack.pop()
            neighbours = list(self.neighbourhood(candidate, self.__epsilon))
            # self._log.debug('Candidate %s has %d neighbours' % (candidate, len(neighbours)))
            if len(neighbours) >= self.__minpts:
                for neighbour in neighbours:
                    if not label[neighbour]:
                        if label[neighbour] is None:
                            stack.append(neighbour)
                        label[neighbour] = count
                        n += 1
            elif label[candidate] is None:
                label[candidate] = 0  # we know this is a leaf so save some time
        # self._log.debug('Grew group %d by %d members' % (count, n))

    @abstractmethod
    def neighbourhood(self, candidate, epsilon):
        raise NotImplementedError()
