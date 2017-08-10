
from __future__ import print_function

import os

newpath = ['C:/Windows/system32', 
        'C:/Windows', 
        'C:/Windows/System32/Wbem',
        'C:/Users/xas_user/AppData/Local/Continuum/Anaconda2',
        'C:/Users/xas_user/AppData/Local/Continuum/Anaconda2/Scripts',
        'C:/Users/xas_user/AppData/Local/Continuum/Anaconda2/Library/bin']

for p in os.environ['PATH'].split(';'):
    p = p.replace('\\', '/')
    if p not in newpath:
        newpath.append(p)


print("REM Setting Path Environmental Variable")
print("@ECHO OFF")
print("PATH=%s" % newpath[0])
for p in newpath[1:]:
    print("PATH=%%PATH%%;%s" % p)





