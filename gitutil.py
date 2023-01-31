import os
import subprocess


def is_valid_git(path):
    '''
    Check if the path is a valid git project
    '''
    # Can add other condition if needed (ex: valid config file) later
    return os.path.isdir(os.path.join(path, '.git'))
    

def get_current_branch(path):
    '''
    Get current branch name of a path
    ''' 
    head = os.path.join(path, '.git', 'HEAD')
    s = None
    with open(head, 'r') as f:
        s = f.readline()
    return s[s.rindex('/')+1:]
    
    
def get_status(path):
    '''
    Get current git status
    '''
    pass
    #git status --porcelain=v1 -u