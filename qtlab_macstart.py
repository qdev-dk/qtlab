from source import qtlab_shell
filelist=qtlab_shell.do_start()

for (dir, name) in filelist:
    filename = '%s/%s' % (dir, name)
    print 'Executing %s...' % (filename)
    try:
        execfile(filename)
    except SystemExit:
        break
