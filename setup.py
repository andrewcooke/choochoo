
import setuptools

setuptools.setup(name='choochoo',
                 packages=setuptools.find_packages(),
                 version='0.6.7',
                 author='andrew cooke',
                 author_email='andrew@acooke.org',
                 description='A Programmable Training Diary',
                 url='https://github.com/andrewcooke/choochoo',
                 long_description='''
# choochoo (ch2)

An **open**, **hackable** and **free** training diary.

See [documentation](https://andrewcooke.github.io/choochoo/) for full
details.

Source and screenshots on [github](https://github.com/andrewcooke/choochoo).
                 ''',
                 long_description_content_type='text/markdown',
                 include_package_data=True,
                 install_requires=[
                     'urwid',
                     'sqlalchemy',
                     'nose',
                     'robotframework',
                     'openpyxl',
                     'numpy',
                     'pandas',
                     'pyGeoTile',
                     'colorama',
                     'pendulum',
                     'requests',
                     'matplotlib',
                     'bokeh',
                     'jupyter'
                     ],
                 entry_points={
                     'console_scripts': [
                         'ch2 = ch2:main',
                     ],
                 },
                 classifiers=(
                     "Programming Language :: Python :: 3.7",
                     "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                     "Operating System :: OS Independent",
                     "Development Status :: 4 - Beta",
                 ),
                 )

