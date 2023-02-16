import wx, requests, os, stat, sys
from zipfile import ZipFile

PLATFORM_LINUX = 0
PLATFORM_WINDOWS = 1
PLATFORM_MAC = 2

def getFolderName(platform):
    if platform == PLATFORM_LINUX:
        return "coinfight-linux"
    elif platform == PLATFORM_WINDOWS:
        return "coinfight-windows"
    elif platform == PLATFORM_MAC:
        return "coinfight-mac"
    else:
        raise "Unrecognized platform"

def getZipFileName(platform):
    return getFolderName(platform) + ".zip"

def getDownloadUrl(platform):
    return "https://github.com/coinop-logan/coinfight/releases/download/v0.3.5.0/" + getZipFileName(platform)

class Launcher(wx.Frame):
    def __init__(self, platform):
        style=wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, None, title="Coinfight Launcher", size=(600, 400), style=style)

        self.platform = platform

        self.SetBackgroundColour(wx.Colour(0, 0, 0))

        self.statusText = wx.StaticText(self, label="")
        font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.statusText.SetFont(font)
        self.statusText.SetForegroundColour(wx.Colour(255, 255, 255))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.statusText, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddStretchSpacer()
        self.SetSizer(sizer)

        self.Bind(wx.EVT_SHOW, self.OnShow)

        self.started = False

    def OnShow(self, event):
        # this method will be called every time the frame is shown
        # including the first time
        if (not self.started):
            if event.IsShown():
                # if the window is being shown, schedule our specific procedure
                self.started = True
                wx.CallAfter(self.startDownload)
    
    def startDownload(self):
        self.dlResponse = None

        if os.path.exists(getZipFileName(self.platform)):
            os.remove(getZipFileName(self.platform))

        self.writingFile = open(getZipFileName(self.platform), 'wb')
        response = requests.get(getDownloadUrl(self.platform), stream=True, allow_redirects=True)
        totalLength = response.headers.get('content-length')

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

            for data in self.dataGenerator:
                self.downloadedSoFar += len(data)
                self.writingFile.write(data)
                self.statusText.SetLabel(str(float(self.downloadedSoFar) / self.totalDlLength))
                
                if (self.downloadedSoFar == self.totalDlLength):
                    self.statusText.SetLabel("Download complete! Unzipping.")
                    self.writingFile.close()
                    break
                
                wx.YieldIfNeeded()
            
            with ZipFile(getZipFileName(self.platform), 'r') as zObject:
                zObject.extractall()
            
            os.remove(getZipFileName(self.platform))

            self.statusText.SetLabel("Unzipped")

            if self.platform == PLATFORM_LINUX:
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
