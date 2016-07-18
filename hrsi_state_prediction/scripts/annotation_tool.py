#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 17 10:46:31 2016

@author: cdondrup
"""

import Tkinter
import rospy
from geometry_msgs.msg import Pose
import argparse
import yaml

class SimpleAppTk(Tkinter.Tk):
    def __init__(self, config_file, save_path, parent=None):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        
        config = self.parse_yaml(config_file)    
        print config
        
        self.initialise(
            button_list=config['buttons'], 
            canvas_width=config['canvas']['width'], 
            canvas_height=config['canvas']['height']
        )
        
        rospy.Subscriber("/test", Pose, self.callback)
        
    def parse_yaml(self, f):
        with open(f, 'r') as stream:
            try:
                return yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        
    def initialise(self, button_list=[], canvas_width=100, canvas_height=100):
        self.grid()
        
        canvas = Tkinter.Canvas(self, width=canvas_width, height=canvas_height)
        canvas.grid(row=0, column=0, columnspan=len(button_list), sticky='EW')        
        
        buttons = []
        for button in button_list:
            button = button.replace(' ','-')
            buttons.append(Tkinter.Button(
                self,
                text=button,
                command=(lambda n: lambda: self.button_callback(n))(button)
            ))
            buttons[-1].grid(row=1, column=len(buttons)-1)
            
        
        
#        self.entry_text = Tkinter.StringVar()
#        self.entry = Tkinter.Entry(self, textvariable=self.entry_text)
#        self.entry.grid(column=0, row=0, sticky='EW')
#        self.entry.bind("<Return>", self.on_enter_pressed)
#        
#        self.button = Tkinter.Button(self, text='Click', command=self.on_button_clicked)
#        self.button.grid(column=1, row=0)
#        
#        self.text = Tkinter.StringVar()
#        self.label = Tkinter.Label(self, anchor='w', textvariable=self.text)
#        self.label.grid(column=0, row=1, columnspan=2, sticky='EW')
#        self.text.set("Text will appear here")
#        
#        self.canvas = Tkinter.Canvas(self, width=200, height=200)
#        self.canvas.grid(column=0, row=2, columnspan=2)
#        self.canvas.create_line(0, 0, 200, 100)
#        self.canvas.create_line(0, 100, 200, 0, fill="red", dash=(4, 4))
#        
#        self.grid_columnconfigure(0, weight=1)
#        self.resizable(True, False)
        
    def on_button_clicked(self):
        self.text.set(self.entry_text.get())
        
    def on_enter_pressed(self, event):
        self.text.set(self.entry_text.get())
        
    def callback(self, msg):
        self.text.set(msg.data)
        
    def button_callback(self, name):
        print name
    
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str,
                        help="Path to yaml config file")
    parser.add_argument("save_path", type=str,
                        help="Path to save the results under")
    args = parser.parse_args()
    
    rospy.init_node("gui_test")
    app = SimpleAppTk(args.config, args.save_path)
    app.title("MyApp")
    app.mainloop()
    rospy.signal_shutdown(0)