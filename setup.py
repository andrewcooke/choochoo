
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(name='choochoo',
                 packages=setuptools.find_packages(),
                 version='0.3.3',
                 author='andrew cooke',
                 author_email='andrew@acooke.org',
                 description='A Programmable Training DailyDiary',
                 url='https://github.com/andrewcooke/choochoo',
                 long_description=long_description,
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

