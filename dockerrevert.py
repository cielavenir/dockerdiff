#!/usr/bin/python

import sys
import os
import stat
import json
import subprocess
import shutil

def revert(container, filename, *args):
    dockerDir = subprocess.check_output(['docker','info','--format','{{.DockerRootDir}}'],shell=False).decode('utf-8').strip()
    if os.getuid() != os.stat(dockerDir).st_uid:
        raise Exception('dockerdiff user (%d) is different from DockerRootDir (%s) user (%d).\nNote: dockerdiff to usual (non-rootless) dockerd requires sudo.'%(os.getuid(),dockerDir,os.stat(dockerDir).st_uid))

    # need to run user which can access docker volume
    if filename[0]!='/':
        raise Exception('filename needs to start with "/" (%s)'%filename)

    inspe = json.loads(subprocess.check_output(['docker','inspect',container]).decode('utf-8'))
    graphDriver = inspe[0]['GraphDriver']
    if 'Name' in graphDriver and not graphDriver['Name'].startswith('overlay'):
        raise Exception('graphDriver not overlay')
    data = graphDriver.get('Data',{})
    if 'UpperDir' not in data or 'LowerDir' not in data or 'MergedDir' not in data:
        raise Exception('UpperDir or LowerDir or MergedDir is not published')

    merged = data['MergedDir']+filename
    upper = data['UpperDir']+filename
    # deduce lower
    for lowerDir in data['LowerDir'].split(':'): # first is outer image, maybe
        lower = lowerDir+filename
        if os.path.exists(lower):
            break
    else:
        lower = None

    if not os.path.exists(upper):
        raise Exception('the file (%s) is not written yet, no need to revert'%filename)

    if lower is None:
        # file is added
        os.unlink(merged)
        os.unlink(upper)
    else:
        # file is modified (or deleted)
        shutil.copy2(lower, merged)
        os.unlink(upper)
    if not os.path.exists(merged):
        # file is deleted
        shutil.copy2(lower, merged) # todo: is merged metadata ok?
        os.unlink(upper)

if __name__=='__main__':
    if len(sys.argv)<3:
        sys.stderr.write('Usage: [sudo] dockerrevert container filename\n')
        exit(1)

    prog, container, filename = sys.argv[:3]
    args = sys.argv[3:] # todo: args is currently unused
    revert(container, filename, *args)
