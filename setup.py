"""Tag & Attribute Template Language

TATL templates are expressive, easy to learn, and cross easily from
server to client. TATL uses the natural block structure in your HTML code,
resulting in less repetition and more natural indentation.

Templates are precompiled into either Python or Javascript and then loaded
as modules.
"""

from setuptools import setup, Extension

description, long_description = __doc__.split('\n\n', 1)

setup(
    name='tatl',
    version='0.1.0',

    description=description,
    long_description=long_description,
    url='https://github.com/tln/tatl',
    author='Tony Lownds',
    author_email='tony@lownds.com',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Environment :: Web Environment',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        #'Programming Language :: Python :: 3',  # maybe have a separate package for tatlrt?
        #'Programming Language :: Python :: 3.4',
    ],
    keywords='templates',

    packages=['tatl'],
    py_modules=['tatlrt'],
    ext_modules=[Extension('fastbuf', sources=['fastbuf.c'])],

    install_requires=['beautifulsoup4', 'grako>=3.4.1', 'lxml'],
    ##TODO: tatlc :)
    #entry_points={
    #    'console_scripts': [
    #        'sample=sample:main',
    #    ],
)