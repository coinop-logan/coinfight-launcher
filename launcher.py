import wx, requests, os, stat, sys
from zipfile import ZipFile

PLATFORM_LINUX = 0
PLATFORM_WINDOWS = 1
PLATFORM_MAC = 2

class Version:
    def __init__(self, versionNumList):
        self.versionNumList = versionNumList
    
    def toString(self):
        return ".".join(map(str, self.versionNumList))
    
    def toGitTag(self):
        return "v" + self.toString()

def fetchVersionInfo():
    response = requests.get("https://coinfight.io/latest_version_info.json")
    response.raise_for_status()
    versionInfo = response.json()
    versionInfo['version'] = Version(versionInfo['version'])
    return versionInfo

def getFolderName(platform):
    if platform == PLATFORM_LINUX:
        return "coinfight-linux"
    elif platform == PLATFORM_WINDOWS:
        return "coinfight-windows"
    elif platform == PLATFORM_MAC:
        return "coinfight-mac-x86"
    else:
        raise "Unrecognized platform"

def getZipFileName(platform):
    return getFolderName(platform) + ".zip"

def getDownloadUrl(platform, version):
    return "https://github.com/coinop-logan/coinfight/releases/download/" + version.toGitTag() + "/" + getZipFileName(platform)

class Launcher(wx.Frame):
    def __init__(self, platform):
        style=wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, title="Coinfight Launcher", size=(800, 400), style=style)

        self.platform = platform

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
        self.button = wx.Button(self, label="test", size=(200, 70))
        self.button.SetFont(buttonFont)
        self.button.Bind(wx.EVT_BUTTON, self.buttonClicked)
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

        self.started = False

    def buttonClicked(self, event):
        self.progressBar.Show()

    def OnShow(self, event):
        # this method will be called every time the frame is shown
        # including the first time
        if (not self.started):
            if event.IsShown():
                # if the window is being shown, schedule our specific procedure
                self.started = True
                wx.CallAfter(self.startDownloadProcess)
    
    def startDownloadProcess(self):
        self.progressBar.Hide()
        
        self.dlResponse = None

        self.statusText.SetLabel("Checking latest version")
        try:
            version = fetchVersionInfo()['version']
        except requests.exceptions.ConnectionError as err:
            self.statusText.SetLabel("Connection error. Are you connected to the Internet?")
            return
        
        self.statusText.SetLabel("Starting download of " + version.toGitTag())

        if os.path.exists(getZipFileName(self.platform)):
            os.remove(getZipFileName(self.platform))

        try:
            response = requests.get(getDownloadUrl(self.platform, version), stream=True, allow_redirects=True)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 404:
                self.statusText.SetLabel("Download file for " + version.toGitTag() + " not found...")
            else:
                self.statusText.SetLabel("http error " + str(response.status_code))

            return
        except requests.exceptions.ConnectionError as err:
            self.statusText.SetLabel("Connection error. Are you connected to the Internet?")
            return

        totalLength = response.headers.get('content-length')

        self.writingFile = open(getZipFileName(self.platform), 'wb')
        if (totalLength is None):
            self.statusText.SetLabel("None total length; saving directly")

            self.writingFile.write(response.content)
            self.writingFile.close()
            return

        else:

            self.dlResponse = response
            self.dataGenerator = response.iter_content(chunk_size=5000)
            self.statusText.SetLabel("downloading...")
            self.totalDlLength = int(totalLength)
            self.downloadedSoFar = 0

            self.progressBar.SetRange(self.totalDlLength)
            self.progressBar.Show()

            for data in self.dataGenerator:
                self.downloadedSoFar += len(data)
                self.writingFile.write(data)
                self.progressBar.SetValue(self.downloadedSoFar)
                
                if (self.downloadedSoFar == self.totalDlLength):
                    self.statusText.SetLabel("Download complete! Unzipping.")
                    self.writingFile.close()
                    break
                
                wx.YieldIfNeeded()
            
            with ZipFile(getZipFileName(self.platform), 'r') as zObject:
                zObject.extractall()
            
            os.remove(getZipFileName(self.platform))

            self.statusText.SetLabel("Unzipped")

            if self.platform == PLATFORM_LINUX or self.platform == PLATFORM_MAC:
                coinfightBinaryPath = os.path.join(getFolderName(self.platform), "coinfight")            
                st = os.stat(coinfightBinaryPath)
                os.chmod(coinfightBinaryPath, st.st_mode | stat.S_IEXEC)
                
                self.statusText.SetLabel("Unzipped and executable now")
            
            os.chdir(getFolderName(self.platform))
            self.statusText.SetLabel("Running")
            wx.YieldIfNeeded()
            if self.platform == PLATFORM_WINDOWS:
                execName = "coinfight.exe"
            else:
                execName = "coinfight"
            os.spawnv(os.P_WAIT, execName, [execName])
            self.statusText.SetLabel("All done!")


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
