
from ch2.data import data


def test_activities():
    d = data('-v', '5')
    a = d.activity('Cycling')
    s = a.activity_statistics('.*')
    print(s.describe())


def test_sumamries():
    d = data('-v', '5')
    a = d.activity('Cycling')
    s = a.summary_statistics('.*')
    print(s)
