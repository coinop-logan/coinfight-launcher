import wx, requests, os, stat, sys, shutil
from zipfile import ZipFile

PLATFORM_LINUX = 0
PLATFORM_WINDOWS = 1
PLATFORM_MAC = 2

class Version:
    def __init__(self, versionNumList: list):
        self.versionNumList = versionNumList
    
    def toString(self):
        return ".".join(map(str, self.versionNumList))
    
    def toGitTag(self):
        return "v" + self.toString()
    
    def __eq__(self, other):
        if len(self.versionNumList) != len(other.versionNumList):
            return False
        
        for i in range(len(self.versionNumList)):
            if (self.versionNumList[i] != other.versionNumList[i]):
                return False
            
        return True

def versionFromString(versionString):
    return Version(list(map(int, versionString.split('.'))))

class CorruptVersionError(Exception):
    pass

def getLocalVersionOrNone(platform):
    try:
        f = open(os.path.join(getDataFolder(platform), "version"), 'r')
        versionStr = f.read()
        f.close()
    except FileNotFoundError:
        return None
    
    try:
        version = versionFromString(versionStr)
    except ValueError:
        raise CorruptVersionError

    return version

def fetchVersionInfo():
    response = requests.get("https://coinfight.io/version_info.json")
    response.raise_for_status()
    versionInfo = response.json()
    versionInfo['version'] = Version(versionInfo['version'])
    return versionInfo

def getDataFolder(platform):
    if platform == PLATFORM_LINUX:
        return "/usr/share/coinfight/"
    else:
        return "."

def getGameFolderPath(platform):
    if platform == PLATFORM_LINUX:
        return "/usr/lib/coinfight/" + getCoinfightFolderName(platform)
    else:
        return getCoinfightFolderName(platform)

def getCoinfightFolderName(platform):
    if platform == PLATFORM_LINUX:
        return "coinfight-linux"
    elif platform == PLATFORM_WINDOWS:
        return "coinfight-windows"
    elif platform == PLATFORM_MAC:
        return "coinfight-mac-x86"
    else:
        raise "Unrecognized platform"

def getZipFileName(platform):
    return getCoinfightFolderName(platform) + ".zip"

def getZipFilePath(platform):
    return getDataFolder(platform) + getZipFileName(platform)

def getDownloadUrl(platform, version):
    return "https://github.com/coinop-logan/coinfight/releases/download/" + version.toGitTag() + "/" + getZipFileName(platform)

# def getDownloadFolderPath(platform):
#     if platform == PLATFORM_LINUX:
#         return "/usr/lib/coinfight/"
#     else:
#         return ""


# def getZipFileName(platform):
#     return getFolderName(platform) + ".zip"

# def getZipFilePath(platform):
#     return getDownloadFolderPath(platform) + getZipFileName(platform)


BUTTONSTATE_WAITING = 0
BUTTONSTATE_UPDATE = 1
BUTTONSTATE_UPDATING = 2
BUTTONSTATE_PLAY = 3
BUTTONSTATE_PLAYING = 4
BUTTONSTATE_ERROR = 5

class Launcher(wx.Frame):
    def __init__(self, platform):
        style=wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, title="Coinfight Launcher", size=(800, 400), style=style)

        self.initLayout()
        self.initState(platform)
    
    def initLayout(self):
        self.SetBackgroundColour(wx.Colour(0, 0, 50))

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainSizer.AddSpacer(15)

        font = wx.Font(36, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        title = wx.StaticText(self, label="Coinfight Launcher")
        title.SetFont(font)
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        self.mainSizer.Add(title, 0, wx.ALIGN_CENTER_HORIZONTAL)

        self.mainSizer.AddStretchSpacer()

        buttonAndStatusSizer = wx.BoxSizer(wx.HORIZONTAL)

        buttonFont = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.button = wx.Button(self, label="...", size=(200, 70))
        self.button.SetFont(buttonFont)
        buttonAndStatusSizer.Add(self.button, 0, wx.ALIGN_LEFT, 20)

        self.statusText = wx.StaticText(self, label="")
        font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.statusText.SetFont(font)
        self.statusText.SetForegroundColour(wx.Colour(200, 200, 200))
        buttonAndStatusSizer.Add(self.statusText, 0, wx.ALIGN_LEFT | wx.ALIGN_BOTTOM | wx.ALL, 10)

        self.mainSizer.Add(buttonAndStatusSizer, 0, wx.ALL, 10)

        self.progressBar = wx.Gauge(self)
        self.mainSizer.Add(self.progressBar, 0, wx.EXPAND | wx.ALL, 10)

        self.mainSizer.AddSpacer(15)

        self.SetSizer(self.mainSizer)

        self.Bind(wx.EVT_SHOW, self.OnShow)
    
    def initState(self, platform):
        self.platform = platform
        self.started = False
        self.latestRemoteVersion = None

    def OnShow(self, event):
        # this method will be called every time the frame is shown
        # including the first time
        if (not self.started):
            if event.IsShown():
                # if the window is being shown, schedule our specific procedure
                self.started = True
                self.progressBar.Hide()
                self.setButtonState(BUTTONSTATE_WAITING)
                self.statusText.SetLabel("Checking for updates")
                wx.CallLater(100, self.startVersionCheck)
    
    def setButtonState(self, state):
        if state == BUTTONSTATE_WAITING:
            self.button.SetBackgroundColour(wx.Colour(200, 200, 200))
            self.button.SetLabel("...")
            self.button.SetForegroundColour(wx.Colour(50, 50, 50))
        elif state == BUTTONSTATE_UPDATE:
            self.button.SetBackgroundColour(wx.Colour(50, 50, 255))
            self.button.SetLabel("UPDATE")
            self.button.SetForegroundColour(wx.Colour(255, 255, 255))
            self.button.Bind(wx.EVT_BUTTON, self.updateClicked)
        elif state == BUTTONSTATE_UPDATING:
            self.button.SetBackgroundColour(wx.Colour(200, 200, 255))
            self.button.SetLabel("UPDATING")
            self.button.SetForegroundColour(wx.Colour(50, 50, 50))
        elif state == BUTTONSTATE_PLAY:
            self.button.SetBackgroundColour(wx.Colour(0, 255, 0))
            self.button.SetLabel("PLAY")
            self.button.SetForegroundColour(wx.Colour(0, 0, 0))
            self.button.Bind(wx.EVT_BUTTON, self.startGameClicked)
        elif state == BUTTONSTATE_PLAYING:
            self.button.SetBackgroundColour(wx.Colour(200, 255, 200))
            self.button.SetLabel("PLAYING")
            self.button.SetForegroundColour(wx.Colour(50, 50, 50))
        elif state == BUTTONSTATE_ERROR:
            self.button.SetBackgroundColour(wx.Colour(255, 100, 100))
            self.button.SetLabel("ERROR")
            self.button.SetForegroundColour(wx.Colour(50, 50, 50))
    
    def startVersionCheck(self):
        try:
            localVersion = getLocalVersionOrNone(self.platform)
        except CorruptVersionError:
            self.statusText.SetLabel("Corrupt 'version' file")
            return
        
        try:
            latestRemoteVersionInfo = fetchVersionInfo()
        except requests.exceptions.ConnectionError as err:
            self.statusText.SetLabel("Connection error. Are you connected to the Internet?")
            return
        
        self.latestRemoteVersion = latestRemoteVersionInfo['version']
        self.serverIsUpdating = latestRemoteVersionInfo['updating']
        
        if localVersion is None:
            updateNeeded = True
        else:
            updateNeeded = localVersion != self.latestRemoteVersion
        
        if updateNeeded:
            self.statusText.SetLabel("Ready to download version " + self.latestRemoteVersion.toString())
            self.setButtonState(BUTTONSTATE_UPDATE)
        else:
            self.setButtonState(BUTTONSTATE_PLAY)

            if self.serverIsUpdating:
                self.statusText.SetLabel("Note: Server is being updated and will not respond.")
            else:
                self.statusText.SetLabel("")
    
    def updateClicked(self, event):
        self.setButtonState(BUTTONSTATE_UPDATING)
        self.dlResponse = None
        self.statusText.SetLabel("Downloading " + self.latestRemoteVersion.toGitTag())
        wx.CallLater(100, self.startUpdate)
    
    def startUpdate(self):
        if os.path.exists(getZipFilePath(self.platform)):
            os.remove(getZipFilePath(self.platform))

        try:
            response = requests.get(getDownloadUrl(self.platform, self.latestRemoteVersion), stream=True, allow_redirects=True)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 404:
                self.statusText.SetLabel("Download file for " + self.latestRemoteVersion.toGitTag() + " not found...")
            else:
                self.statusText.SetLabel("http error " + str(response.status_code))

            self.setButtonState(BUTTONSTATE_ERROR)
            return
        except requests.exceptions.ConnectionError as err:
            self.statusText.SetLabel("Connection error. Are you connected to the Internet?")
            self.setButtonState(BUTTONSTATE_ERROR)
            return

        totalLength = response.headers.get('content-length')

        self.writingFile = open(getZipFilePath(self.platform), 'wb')
        if (totalLength is None):
            self.writingFile.write(response.content)
            self.writingFile.close()

            self.setButtonState(BUTTONSTATE_PLAY)
            self.statusText.SetLabel("Download was surprisingly small... There may be something wrong :/")
            return

        else:
            self.dlResponse = response
            self.dataGenerator = response.iter_content(chunk_size=5000)
            self.statusText.SetLabel("Downloading...")
            self.totalDlLength = int(totalLength)
            self.downloadedSoFar = 0

            self.progressBar.SetRange(self.totalDlLength)
            self.progressBar.Show()

            for data in self.dataGenerator:
                self.downloadedSoFar += len(data)
                self.writingFile.write(data)
                self.progressBar.SetValue(self.downloadedSoFar)
                
                if (self.downloadedSoFar == self.totalDlLength):
                    self.writingFile.close()
                    break
                
                wx.YieldIfNeeded()
            
            self.statusText.SetLabel("Extracting...")
            with ZipFile(getZipFilePath(self.platform), 'r') as zObject:
                zObject.extractall(getDataFolder(self.platform))
            
            os.remove(getZipFilePath(self.platform))

            # save the version info
            f = open(os.path.join(getDataFolder(self.platform), "version"), 'w')
            f.write(self.latestRemoteVersion.toString())
            f.close()

            if self.platform == PLATFORM_LINUX or self.platform == PLATFORM_MAC:
                self.statusText.SetLabel("Updating Permissions...")
                coinfightFolderPath = os.path.join(getDataFolder(self.platform), getCoinfightFolderName(self.platform))
                coinfightBinaryPath = os.path.join(coinfightFolderPath, "coinfight")            
                st = os.stat(coinfightBinaryPath)
                os.chmod(coinfightBinaryPath, st.st_mode | stat.S_IEXEC)
            
                if self.platform == PLATFORM_LINUX:
                    shutil.rmtree(getGameFolderPath(self.platform))
                    os.rename(coinfightFolderPath, os.path.join(getGameFolderPath(self.platform)))
                
        self.setButtonState(BUTTONSTATE_PLAY)
        if self.serverIsUpdating:
            self.statusText.SetLabel("Ready to play! (but server is updating)")
        else:
            self.statusText.SetLabel("Ready to play!")

    def startGameClicked(self, event):
        self.statusText.SetLabel("Running")
        self.setButtonState(BUTTONSTATE_PLAYING)
        wx.CallLater(100, self.startGame)

    def startGame(self):
        os.chdir(getGameFolderPath(self.platform))
        wx.YieldIfNeeded()
        if self.platform == PLATFORM_WINDOWS:
            execName = "coinfight.exe"
        else:
            execName = "coinfight"
        os.spawnv(os.P_WAIT, execName, [execName])
        # the above line blocks until the game closes
        os.chdir("..")

        self.statusText.SetLabel("")
        self.setButtonState(BUTTONSTATE_PLAY)


def main():
    if sys.platform == "linux" or sys.platform == "linux2":
        platform = PLATFORM_LINUX
    elif sys.platform == "darwin":
        platform = PLATFORM_MAC
    elif sys.platform == "win32":
        platform = PLATFORM_WINDOWS
    else:
        print("Unrecognized platform: " + platform)
        return

    app = wx.App()
    launcherFrame = Launcher(platform)
    launcherFrame.Show(True)
    app.MainLoop()


if __name__ == "__main__":
    main()
