import os, sys, shutil

dir = os.path.split(__file__)[0]
if dir:
    os.chdir(dir)
sys.path += ['..', '.']

import tatl, builder

try:
    html = tatl.load('gen.html').html()
except:
    import pdb, traceback
    traceback.print_exc()
    pdb.post_mortem()
open('../gh-pages/index.html', 'w').write(html.encode('utf-8'))
shutil.copyfile('docs.css', '../gh-pages/docs.css')