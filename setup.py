"""
pokergame: A simple poker game simulation framework
"""

from setuptools import setup

setup(
    name='pokergame',
    version='0.1',
    description=__doc__,
    long_description=open('README.md').read(),
    author='Lion Ackermann',
    # url='',
    license='MIT',
    packages=['pokergame', 'deuces'],
    package_dir={'pokergame': 'src/pokergame', 'deuces': 'src/deuces/deuces'},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'License :: OSI Approved :: MIT License',
        'Topic :: Games/Entertainment'
    ]
)
