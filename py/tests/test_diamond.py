

class Root:

    def __init__(self, *args, **kargs):
        print('Root init')
        print(self.bar)
        print(f'Root {dir(self)}')
        print(self.bar)


class ChildA(Root):

    def __init__(self, *args, **kargs):
        print('Child A init')
        print(self.bar)
        super().__init__(*args, **kargs)
        print(f'Child A {dir(self)}')
        print(self.bar)

    def foo(self):
        print('Child A foo')
        yield from self.bar()

    def bar(self):
        print('Child A bar')
        raise NotImplementedError()


class ChildB(Root):

    def __init__(self, *args, **kargs):
        print('Child B init')
        print(self.bar)
        super().__init__(*args, **kargs)
        print(f'Child B {dir(self)}')
        print(self.bar)


class Grandchild(ChildA, ChildB):

    def __init__(self, *args, **kargs):
        print('Grandchild init')
        print(self.bar)
        super().__init__(*args, **kargs)
        print(f'Grandchild {dir(self)}')
        print(self.bar)

    def bar(self):
        print('Grandchild bar')
        yield 1


if __name__ == '__main__':
    x = Grandchild()
    print(list(x.foo()))
