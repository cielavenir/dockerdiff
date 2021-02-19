#!/usr/bin/python

import sys
import os
import stat
import json
import subprocess

def getDiff(fout, container, filename, *args):
    dockerDir = subprocess.check_output(['docker','info','--format','{{.DockerRootDir}}'],shell=False).decode('utf-8').strip()
    if os.getuid() != os.stat(dockerDir).st_uid:
        raise Exception('dockerdiff user (%d) is different from DockerRootDir (%s) user (%d).\nNote: dockerdiff to usual (non-rootless) dockerd requires sudo.'%(os.getuid(),dockerDir,os.stat(dockerDir).st_uid))

    # need to run user which can access docker volume
    if filename[0]!='/':
        raise Exception('filename needs to start with "/"')

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
        # file is not written
        if lower is None:
            # file does not exist
            raise Exception('%s does not exist in container (%s)'%(filename,container))
        else:
            # file is not modified, no need to run diff
            assert os.path.exists(merged)
            return
    # now upper surely exists.
    if lower is None:
        # file is added
        lower = '/dev/null'
    else:
        # file is modified (or deleted)
        pass
    if not os.path.exists(merged):
        # file is deleted
        upper = '/dev/null'
    
    subprocess.call(['diff',lower,upper]+list(args),stdout=fout)

if __name__=='__main__':
    if len(sys.argv)<3:
        sys.stderr.write('Usage: [sudo] dockerdiff container filename [diff-args...]\n')
        exit(1)

    prog, container, filename = sys.argv[:3]
    args = sys.argv[3:]
    getDiff(sys.stdout, container, filename, *args)
