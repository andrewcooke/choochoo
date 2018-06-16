

def sign(x):
    if x == 0:
        return 0
    elif x > 0:
        return 1
    else:
        return -1


PALETTE = [('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
           ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
           ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
           ]
