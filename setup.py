"""
pokergame: A simple poker game simulation framework
"""

import setuptools

with open('README.md') as f:
    long_description = f.read()

setuptools.setup(
    name='pokergame',
    version='0.1',
    description=__doc__,
    long_description=long_description,
    author='Lion Ackermann',
    # url='',
    packages=['pokergame', 'deuces'],
    package_dir={ '': 'src' },
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3'
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Topic :: Games/Entertainment'
    ]
)
