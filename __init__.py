import os
from threading import Thread
from time import sleep
import cudatext as cud
import cuda_git_pane.gitutil as git
from cudax_lib import get_translation


_ = get_translation(__file__)


FN_ICON = './py/cuda_git_pane/assets/gitw.png'
UI_TITLE = 'Git Pane'

MSG_INVALID_GIT = _('Git Pane: Not a valid git. Nothing was changed.')
FMT_MSG_OPENED = _('Git Pane: Opened ({path})') 


class Command:
    h_dlg = None
    h_tree = None
    git_path = None
    git_name = None
    is_pane_showing = True
    
    update_requests = 0
    updater = None
    updeter_busy = False
    _new_git_info_avail = False
    git_info = {
        'branch':None
    }
    
    # cuda settings
    cs_background = 0
    
    # plugin setting
    ps_indent = 2
    ps_ui_staged = 'Staged Changes'
    ps_ui_unstaged = 'Changes'
    ps_ui_header = '{repo} ({branch})'
    ps_update_frequency = 0.5
    
    def __init__(self):
        self.load_configs()
        
    def load_configs(self):
        # cuda setting
        theme = cud.app_proc(cud.PROC_THEME_UI_DICT_GET, '')
        self.cs_background = theme['TreeBg']['color']

    def init_pane(self):
        '''
        Init the side panel
        '''
        self.h_dlg = cud.dlg_proc(0, cud.DLG_CREATE)
        cud.dlg_proc(self.h_dlg, cud.DLG_PROP_SET, prop={
            'color':self.cs_background,
            'on_show':'cuda_git_pane.on_pane_show',
            'on_hide':'cuda_git_pane.on_pane_hide',           
        })
        # button open folder
        idx_btn_open = cud.dlg_proc(self.h_dlg, cud.DLG_CTL_ADD, prop='button_ex')
        cud.dlg_proc(self.h_dlg, cud.DLG_CTL_PROP_SET, index=idx_btn_open, prop={
            'name':'btn_open',
            'a_l':None,
            'a_r':('',']'),
            'cap':'\u2026',
            'hint':'Open',
            'w':30,
            'h':30,
            'on_change':'cuda_git_pane.on_btn_open_click',
        })
        # button refresh
        idx_btn_refresh = cud.dlg_proc(self.h_dlg, cud.DLG_CTL_ADD, prop='button_ex')
        cud.dlg_proc(self.h_dlg, cud.DLG_CTL_PROP_SET, index=idx_btn_refresh, prop={
            'name':'btn_refresh',
            'a_l':None,
            'a_r':('btn_open','['),
            'cap':'\u2b6e',
            'hint':'Refresh',
            'w':30,
            'h':30,
            'on_change':'cuda_git_pane.on_btn_refresh_click',
        })        
        # treeview
        idx_tree = cud.dlg_proc(self.h_dlg, cud.DLG_CTL_ADD, prop='treeview')
        cud.dlg_proc(self.h_dlg, cud.DLG_CTL_PROP_SET, index=idx_tree, prop={
            'name':'tree',
            'a_t':('btn_open', ']'),
            'a_r':('',']'),
            'a_b':('',']')
        })
        self.h_tree = cud.dlg_proc(self.h_dlg, cud.DLG_CTL_HANDLE, index=idx_tree)
        cud.tree_proc(self.h_tree, cud.TREE_THEME)
        # finalize
        cud.app_proc(cud.PROC_SIDEPANEL_ADD_DIALOG, (UI_TITLE, self.h_dlg, FN_ICON))
        self.request_update()
    
    def update_pane(self):
        '''
        Update the side panel
        '''
        cud.tree_proc(self.h_tree, cud.TREE_LOCK)
        cud.tree_proc(self.h_tree, cud.TREE_ITEM_DELETE, 0)
        if self.git_path is not None:
            h_root = cud.tree_proc(self.h_tree, cud.TREE_ITEM_ADD,
                index=-1, text=self.ps_ui_header.format(repo=self.git_name, branch=self.git_info['branch'])
            )
            h_staged = cud.tree_proc(self.h_tree, cud.TREE_ITEM_ADD, index=-1, text=self.ps_ui_staged)
            h_unstaged = cud.tree_proc(self.h_tree, cud.TREE_ITEM_ADD, index=-1, text=self.ps_ui_unstaged)
            cud.tree_proc(self.h_tree, cud.TREE_ITEM_UNFOLD_DEEP, id_item=h_root)
        cud.tree_proc(self.h_tree, cud.TREE_UNLOCK)
        
    def update_git_info(self):
        '''
        Update git info
        '''
        self.git_info['branch'] = git.get_current_branch(self.git_path)
    
    def request_update(self):
        '''
        Request update to the internal update thread
        '''
        if self.git_path is not None:
            self.update_requests += 1
        if self.update_requests > 0:
            if self.updater is None or not self.updater.is_alive():
                self.updater = Thread(target=self.do_updater_job, daemon=True)
                self.updater.start()
            self.start_timer()
        
    def stop_timer(self):
        '''
        Stop the timer monitoring the update thread
        '''
        cud.timer_proc(cud.TIMER_STOP, 'cuda_git_pane.on_timer', 0, '0')
        
    def start_timer(self):
        '''
        Start the timer monitoring the update thread
        '''
        cud.timer_proc(cud.TIMER_START, 'cuda_git_pane.on_timer', round(self.ps_update_frequency*150), '0')
    
    def select_path(self):
        '''
        Open dialog for user to select git folder
        '''
        p = cud.dlg_dir('')
        if p is None:
            pass
        elif git.is_valid_git(p):
            self.git_path = p
            self.git_name = os.path.basename(p)
            cud.msg_status(FMT_MSG_OPENED.format(path=p))
        else:
            cud.msg_status(MSG_INVALID_GIT)
        self.request_update()

    def do_updater_job(self):
        '''
        Function for the updater thread to run
        '''
        while True:
            if self.is_pane_showing and self.update_requests > 0:
                self.updater_busy = True
            while self.is_pane_showing and self.update_requests > 0:
                self.update_requests = 0
                self.update_git_info()
                self._new_git_info_avail = True
            self.updater_busy = False
            sleep(self.ps_update_frequency)
            
    def do_open(self):
        '''
        Do command open
        '''
        if self.h_dlg is None:
            self.init_pane()
        cud.app_proc(cud.PROC_SIDEPANEL_ACTIVATE, (UI_TITLE, True))
        self.request_update()
        
    def on_btn_open_click(self, id_ctl, data):
        '''
        Handle event click on button open
        '''
        self.select_path()
    
    def on_btn_refresh_click(self, id_ctl, data):
        '''
        Handle event click on button refresh
        '''
        self.request_update()
        
    def on_pane_show(self, id_ctl, data):
        '''
        Handle event show of pane
        '''
        self.is_pane_showing = True
        
    def on_pane_hide(self, id_ctl, data):
        '''
        Handle event hide of pane
        '''
        self.is_pane_showing = False
        
    def on_timer(self, tag='', info=''):
        '''
        Handle every timer tick
        '''
        if self.updater is None or not self.updater.is_alive():
            self.stop_timer()
            return
        if self._new_git_info_avail:
            self._new_git_info_avail = False
            self.update_pane()
        if self.update_requests <= 0 and not self.updater_busy:
            self.stop_timer()