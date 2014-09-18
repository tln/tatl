from distutils.core import setup, Extension

fastbuf = Extension('fastbuf',
                    sources = ['fastbuf.c'])

setup (name = 'tatl',
       version = '0.1',
       description = 'Tag & Attribute Template Language',
       packages = ['tatl'],
       py_modules = ['tatlrt'],
       ext_modules = [fastbuf])
