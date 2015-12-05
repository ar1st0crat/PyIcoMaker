# -*- coding: utf-8 -*-

###############################################################
#
# @author: ar1st0crat
# @version: 0.10
#
# Script for making ico files from image files
#  
###############################################################

import wx
import struct
from io import BytesIO
from PIL import Image


def pil_image_to_wx_image(myPilImage):
    """ Convert PIL image to wxImage.
    The function is taken (and slightly changed) from
    [http://wiki.wxpython.org/WorkingWithImages] """

    # Make sure there is an alpha layer copy
    if myPilImage.mode[-1] == 'A':                                 
        myWxImage = wx.EmptyImage(*myPilImage.size)
        myPilImageCopyRGBA = myPilImage.copy()
        # RGBA --> RGB
        myPilImageCopyRGB = myPilImageCopyRGBA.convert('RGB')    
        myPilImageRgbData = myPilImageCopyRGB.tostring()
        myWxImage.SetData(myPilImageRgbData)
        # Create layer and insert alpha values
        myWxImage.SetAlphaData(myPilImageCopyRGBA.tostring()[3::4])  
    else: 
        # The resulting image will not have alpha
        myWxImage = wx.EmptyImage(*myPilImage.size)
        myPilImageCopy = myPilImage.copy()
        # Discard any alpha from the PIL image
        myPilImageCopyRGB = myPilImageCopy.convert('RGB')
        myPilImageRgbData = myPilImageCopyRGB.tostring()
        myWxImage.SetData(myPilImageRgbData)
    
    return myWxImage


class IcoMakerFrame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY,
                            'PyIcoMaker', size=(670, 370))
        self.mainPanel = wx.Panel(self, -1)
        self.create_menu() 
        self.create_statusbar()

    def get_menu_data(self):
        data = (("&File",
                ({"&Open...": self.on_openfile_click},
                    {"&Save...": self.on_savefile_click},
                    {"&Exit": self.on_exit_click })),
                ("&Edit",
                    ({"Flip &Left-to-Right": self.on_flip_leftright_click},
                    {"Flip &Top-to-Bottom": self.on_flip_topbottom_click},
                    {"&Rotate": self.on_rotate_click},
                    {"&Grayscale": self.on_grayscale_click})),
                ("&Help",
                    ({ "&About...": self.on_about_click},))
                )
        return data

    def create_menu(self):
        menu = wx.MenuBar()
        for item in self.get_menu_data():
            menuItem = self.create_sub_menu(item[1])
            menu.Append(menuItem, item[0])
        self.SetMenuBar(menu)

    def create_sub_menu(self, itemgroup):
        groupmenu = wx.Menu()
        for item in itemgroup:
            # each menu item is represented with its title 
            # and (optionally) its handler
            title, handler = item.items()[0]
            menuItem = groupmenu.Append(-1, title)
            if handler:
                self.Bind(wx.EVT_MENU, handler, menuItem)
        return groupmenu

    def create_statusbar(self):
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(4)
        self.statusbar.SetStatusWidths([0, -3, -1, -1])

    def on_openfile_click(self, event):
        """ open any image file (BMP, JPG, PNG, etc.) 
        and preview it as the set of ICO frames """

        dlg = wx.FileDialog(self, message="Choose a file",
                                    defaultDir="", defaultFile="", 
                                    wildcard="*.*", style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                self.mainImage = Image.open(dlg.Path)
                self.statusbar.SetStatusText(dlg.Path, 1)
                self.statusbar.SetStatusText("Size: %d x %d px" %
                    (self.mainImage.size[0], self.mainImage.size[1]), 2)
                self.statusbar.SetStatusText("Format: %s" %
                    self.mainImage.format, 3)
            except IOError:
                dlg = wx.MessageDialog(None,
                      'The file has not been recognized as an image file!',
                      'Error', wx.OK | wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()
                quit()
        
        self.show_ico_frames()

    def show_ico_frames(self):
        """ main function for drawing all ICO frames on the MainPanel """

        sizes = [(16,16), (24,24), (32,32), (48,48),
                 (64,64), (128,128), (255,255)]
        xCoord = 10            

        for frame in sizes[::-1]:
            img = self.mainImage.resize((frame[0], frame[1]), Image.ANTIALIAS)
            bmp = pil_image_to_wx_image(img)
            wx.StaticBitmap(self.mainPanel, -1,
                            wx.BitmapFromImage(bmp), (xCoord, 10)) 
            xCoord += frame[0] + 10
        
        self.Refresh()

    def on_savefile_click(self, event):
        """ ICO saving is based on 
        [https://github.com/python-pillow/Pillow/blob/master/PIL/IcoImagePlugin.py] """

        dlg = wx.FileDialog(self, message="Save file as...",
                            defaultDir="", defaultFile="",
                            wildcard="ICO files (*.ico)|*.ico", style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            with open(dlg.Path, 'wb') as f:
                # write header info
                f.write(b'\0\0\1\0')
                # write number of images
                f.write(b'\7\0')
             
                sizes = [(16,16), (24,24), (32,32), (48,48),
                         (64,64), (128,128), (255,255)]
                
                """ ICO format [from Wiki]:
                offset  bytes  Description
                0   1   Specifies image width in pixels. 
                        Can be any number between 0 and 255.
                        Value 0 means image width is 256 pixels.
                1   1   Specifies image height in pixels. 
                        Can be any number between 0 and 255. 
                        Value 0 means image height is 256 pixels.
                2   1   Specifies number of colors in the color palette. 
                        Should be 0 if the image does not use a color palette.
                3   1   Reserved. Should be 0
                4   2   In ICO format: Specifies color planes. 
                        Should be 0 or 1.
                6   2   In ICO format: Specifies bits per pixel.
                8   4   Specifies the size of the image's data in bytes
                12  4   Specifies the offset of BMP or PNG data 
                        from the beginning of the ICO/CUR file
                
                total:  16 bytes
                """

                # offset for writing ICO frames (PNG images)
                offset = f.tell() + len(sizes) * 16        
                
                for size in sizes:
                    # write new IcoDirEntry to ICO file
                    width, height = size
                    # write width nd height of the current ICO frame
                    f.write(struct.pack("B", width))
                    f.write(struct.pack("B", height))
                    # bColorCount=0  bReserved=0  wPlanes=0
                    f.write(b"\0\0\0\0")
                    # wBitCount=32 (we save each ico_frame as png)
                    f.write(struct.pack("<H", 32))
            
                    # write the image itself of the current ICO frame
                    tmp = self.mainImage.copy()
                    tmp = tmp.resize(size, Image.ANTIALIAS)
                    ico_frame = BytesIO()
                    tmp.save(ico_frame, "png")
                    ico_frame.seek(0)
                    # read all bytes saved earlier
                    ico_frame_bytes = ico_frame.read()
                    ico_frame_len = len(ico_frame_bytes)
                    # write dwBytesInRes = <total_length>
                    f.write(struct.pack("<I", ico_frame_len))
                    # write dwImageOffset = <offset>
                    f.write(struct.pack("<I", offset))
                    
                    current = f.tell()
                    f.seek(offset)
                    # write the current ICO frame (PNG)
                    f.write(ico_frame_bytes)
                    # increase offset for next ICO frame             
                    offset = offset + ico_frame_len
                    f.seek(current)

    def on_flip_leftright_click(self,event):
        self.mainImage = self.mainImage.transpose(Image.FLIP_LEFT_RIGHT)
        self.show_ico_frames()
    
    def on_flip_topbottom_click(self,event):
        self.mainImage = self.mainImage.transpose(Image.FLIP_TOP_BOTTOM)
        self.show_ico_frames()
    
    def on_rotate_click(self, event):
        self.mainImage = self.mainImage.rotate(-90)
        self.show_ico_frames()
    
    def on_grayscale_click(self, event):
        self.mainImage = self.mainImage.convert('L')
        self.show_ico_frames()

    def on_about_click(self, event):
        dlg = wx.MessageDialog(None, 'Version 0.1\n(c)2015 ar1st0crat',
                                     'PyIcoMaker', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
    
    def on_exit_click(self, event):
        self.Close()


if __name__ == '__main__':
    app = wx.App()
    frame = IcoMakerFrame()
    frame.Show()
    app.MainLoop()