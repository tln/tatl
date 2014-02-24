import tatl, os, sys
os.chdir('docs')
sys.path.append(os.getcwd())
try:
    print tatl.load('gen.html').html()
except:
    import pdb
    pdb.post_mortem()
