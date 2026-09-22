from abaqusGui import *
from abaqusConstants import *

import os
import sys


class EBSD2AbaqusForm(AFXForm):

    def __init__(self, owner):
        AFXForm.__init__(self, owner)
        self.cmd = AFXGuiCommand(
            self, 'build_model', 'ebsd2abaqus_kernel',
            registerQuery=False)

        self.ctfKw = AFXStringKeyword(self.cmd, 'ctfFile', TRUE, '')
        self.projectKw = AFXStringKeyword(self.cmd, 'projectFolder', TRUE, '')
        self.angleKw = AFXFloatKeyword(
            self.cmd, 'misorientationDeg', TRUE, 5.0)
        self.minPixelsKw = AFXIntKeyword(
            self.cmd, 'minGrainPixels', TRUE, 5)

        self.ctfPickKw = AFXStringKeyword(None, '', FALSE)
        self.folderPickKw = AFXStringKeyword(None, '', FALSE)
        self.ctfPatternTgt = AFXIntTarget(0)
        self.folderPatternTgt = AFXIntTarget(0)

    def getFirstDialog(self):
        return EBSD2AbaqusDB(self)

    def doCustomChecks(self):
        dialog = self.getCurrentDialog()
        ctf_file = self.ctfKw.getValue().strip().strip('"')
        project_folder = self.projectKw.getValue().strip().strip('"')

        if not os.path.isfile(ctf_file):
            showAFXErrorDialog(dialog, 'Select an existing CTF file.')
            dialog.onKeywordError(self.ctfKw)
            return False
        if not ctf_file.lower().endswith('.ctf'):
            showAFXErrorDialog(dialog, 'The input file must use the .ctf extension.')
            dialog.onKeywordError(self.ctfKw)
            return False
        if not project_folder:
            showAFXErrorDialog(dialog, 'Select a project output folder.')
            dialog.onKeywordError(self.projectKw)
            return False
        if self.angleKw.getValue() <= 0.0:
            showAFXErrorDialog(dialog, 'Misorientation must be greater than zero.')
            dialog.onKeywordError(self.angleKw)
            return False
        if self.minPixelsKw.getValue() < 1:
            showAFXErrorDialog(dialog, 'Minimum grain pixels must be at least one.')
            dialog.onKeywordError(self.minPixelsKw)
            return False
        return True


class EBSD2AbaqusDB(AFXDataDialog):

    [ID_PICK_CTF, ID_CTF_SELECTED, ID_PICK_FOLDER, ID_FOLDER_SELECTED] = range(
        AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 4)

    def __init__(self, form):
        AFXDataDialog.__init__(
            self, form, 'EBSD2Abaqus', self.OK | self.CANCEL,
            DIALOG_ACTIONS_SEPARATOR | DECOR_RESIZE)
        self.form = form
        self.ctfDb = None
        self.folderDb = None
        self.getActionButton(self.ID_CLICKED_OK).setText('Build CAE')

        FXMAPFUNC(
            self, SEL_COMMAND, self.ID_PICK_CTF,
            EBSD2AbaqusDB.onPickCtf)
        FXMAPFUNC(
            self, SEL_COMMAND, self.ID_CTF_SELECTED,
            EBSD2AbaqusDB.onCtfSelected)
        FXMAPFUNC(
            self, SEL_COMMAND, self.ID_PICK_FOLDER,
            EBSD2AbaqusDB.onPickFolder)
        FXMAPFUNC(
            self, SEL_COMMAND, self.ID_FOLDER_SELECTED,
            EBSD2AbaqusDB.onFolderSelected)

        box = FXGroupBox(
            self, 'Conversion settings', FRAME_GROOVE | LAYOUT_FILL_X)

        row = FXHorizontalFrame(box, LAYOUT_FILL_X)
        AFXTextField(
            row, 58, 'Oxford CTF file:', form.ctfKw, 0, LAYOUT_FILL_X)
        FXButton(row, 'Browse...', None, self, self.ID_PICK_CTF)

        row = FXHorizontalFrame(box, LAYOUT_FILL_X)
        AFXTextField(
            row, 58, 'Project folder:', form.projectKw, 0, LAYOUT_FILL_X)
        FXButton(row, 'Browse...', None, self, self.ID_PICK_FOLDER)

        values = AFXVerticalAligner(box, LAYOUT_FILL_X)
        AFXTextField(
            values, 12, 'Misorientation (deg):', form.angleKw, 0)
        AFXTextField(
            values, 12, 'Minimum grain pixels:', form.minPixelsKw, 0)

        FXLabel(
            box,
            'The generated CAE contains grains, mesh, sets and orientations only.\n'
            'No step, load, crack, XFEM or damage model is added.',
            None, JUSTIFY_LEFT | LAYOUT_FILL_X)

    def onPickCtf(self, sender, sel, ptr):
        self.form.ctfPickKw.setValue(self.form.ctfKw.getValue())
        self.ctfDb = AFXFileDialog(
            self, 'Select Oxford CTF File', self.form.ctfPickKw,
            None, None, 0, AFXSELECTFILE_EXISTING,
            'Oxford CTF (*.ctf)\nAll files (*.*)', self.form.ctfPatternTgt)
        self.ctfDb.setTarget(self)
        self.ctfDb.setSelector(self.ID_CTF_SELECTED)
        self.ctfDb.create()
        self.ctfDb.showModal()
        return 1

    def onCtfSelected(self, sender, sel, ptr):
        if self.ctfDb.getPressedButtonId() == AFXDialog.ID_CLICKED_OK:
            path = self.form.ctfPickKw.getValue().strip().strip('"')
            if path:
                self.form.ctfKw.setValue(path)
                if not self.form.projectKw.getValue().strip():
                    default_folder = os.path.join(
                        os.path.dirname(path), 'EBSD2Abaqus_model')
                    self.form.projectKw.setValue(default_folder)
        self.ctfDb.setTarget(None)
        return 1

    def onPickFolder(self, sender, sel, ptr):
        self.form.folderPickKw.setValue(self.form.projectKw.getValue())
        self.folderDb = AFXFileDialog(
            self, 'Select Project Folder', self.form.folderPickKw,
            None, None, 0, AFXSELECTFILE_DIRECTORY,
            'Directories (*)\nAll files (*.*)', self.form.folderPatternTgt)
        self.folderDb.setTarget(self)
        self.folderDb.setSelector(self.ID_FOLDER_SELECTED)
        self.folderDb.create()
        self.folderDb.showModal()
        return 1

    def onFolderSelected(self, sender, sel, ptr):
        if self.folderDb.getPressedButtonId() == AFXDialog.ID_CLICKED_OK:
            path = self.form.folderPickKw.getValue().strip().strip('"')
            if path:
                self.form.projectKw.setValue(path)
        self.folderDb.setTarget(None)
        return 1


thisPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisPath).replace('\\', '/')
if thisDir not in sys.path:
    sys.path.append(thisDir)

kernelInit = (
    "import sys\n"
    "p = r'%s'\n"
    "if p not in sys.path: sys.path.append(p)\n"
    "import ebsd2abaqus_kernel\n"
    "reload(ebsd2abaqus_kernel)\n"
) % thisDir

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()
toolset.registerGuiMenuButton(
    buttonText='EBSD2Abaqus...',
    object=EBSD2AbaqusForm(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString=kernelInit,
    applicableModules=ALL,
    version='1.0',
    author='CrackPrediction',
    description='Build a neutral Abaqus CAE model from Oxford CTF EBSD data.',
    helpUrl='')
