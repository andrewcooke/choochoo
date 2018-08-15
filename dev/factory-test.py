
# this could be used to generate tokens, but frankly doesn't seem
# worth the effort

class Number:

    def __new__(cls, n):
        if n % 2:
            return super().__new__(Odd)
        else:
            return super().__new__(Even)

class FactoryNumber(Number):

    def __new__(self, n):
        raise Exception('Create via Number()')    
        
class Odd(FactoryNumber):

    def __init__(self, n):
        self.n = n

class Even(FactoryNumber):

    def __init__(self, n):
        self.n = n

a = Number(3)
print(a)
print(a.n)
print(type(a))
