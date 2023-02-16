import wx, requests, os, stat
from zipfile import ZipFile

url = "https://github.com/coinop-logan/coinfight/releases/download/v0.3.5.0/coinfight-linux.zip"

class Launcher(wx.Frame):
    def __init__(self, parent):
        style=wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, title="Coinfight Launcher", size=(600, 400), style=style)

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

    def OnShow(self, event):
        self.dlResponse = None

        self.writingFile = open('coinfight-linux.zip', 'wb')
        response = requests.get(url, stream=True, allow_redirects=True)
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
            
            with ZipFile("coinfight-linux.zip", 'r') as zObject:
                zObject.extractall(path="./")
            
            st = os.stat('coinfight-linux/coinfight')
            os.chmod('coinfight-linux/coinfight', st.st_mode | stat.S_IEXEC)
            
            self.statusText.SetLabel("Unzipped")


            # self.timerId = 1
            # self.timer = wx.Timer(self, self.timerId)
            # self.Bind(wx.EVT_TIMER, self.onTimer)
            # self.timer.Start(100)
    
    # def onTimer(self, event):
    #     if self.dlResponse is None or self.writingFile is None:
    #         print("!?!?!")
    #         return
        
    #     data = next(self.dataGenerator, None)
        
    #     if (data is None):
    #         self.statusText.SetLabel("Download complete! outcome A.")
    #         self.writingFile.close()
    #         self.timer.Stop()
        
    #     else:
        
    #     print("iter ending")


app = wx.App()
launcherFrame = Launcher(None)
launcherFrame.Show(True)
app.MainLoop()