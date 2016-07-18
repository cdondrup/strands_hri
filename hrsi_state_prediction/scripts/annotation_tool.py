#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 17 10:46:31 2016

@author: cdondrup
"""

from __future__ import print_function
import Tkinter
from geometry_msgs.msg import Point
import argparse
import yaml
from pymongo import MongoClient
import numpy
import time
import threading
from copy import deepcopy


class SimpleAppTk(Tkinter.Tk):
    __uuid = "uuid"
    __count = "count"
    __min_dist = "min_dist"
    __travel_dist = "travel_dist"
    __last_pose = "last_pose"
    __ids = "ids"
    __class = "class"

    def __init__(self, config_file, save_path, host, port, db_name,
                 data_collection, config_collection, min_num_entries,
                 min_min_dist, min_travel_dist, parse=False, parent=None):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent

        print("Connecting")
        client = MongoClient(host, port)
        db = client[db_name]
        collections = db.collection_names(include_system_collections=False)
        print(collections)
        if data_collection not in collections:
            raise KeyError("Collection '%s' could not be found in db '%s'." % (data_collection, db_name))

        if config_collection not in collections or parse:
            print("No collection %s found. Parsing %s in %s ..." % (config_collection, data_collection, db_name))
            people = self.parse_db(db, data_collection)
            db.create_collection(config_collection)
            cc = db[config_collection]
            cc.insert(people)
        else:
            print("Loading collection %s" % config_collection)

        config = self.parse_yaml(config_file)
        print(config)

        self.an_gen = self.to_annotate(db[data_collection], db[config_collection], min_num_entries,
                 min_min_dist, min_travel_dist)
        self.an_list = [self.an_gen.next()]
        self.an_cur = self.an_list[-1]
        self.an_col = db[config_collection]
        self.draw = True

        self.width = config['canvas']['width']
        self.height = config['canvas']['height']

        self.initialise(
            button_list=config['buttons'],
            canvas_width=self.width,
            canvas_height=self.height
        )

        self.update_text()
        self.t = threading.Thread(target=self.paint)
        self.t.start()

    def update_text(self):
        self.uuid_text.set("UUID: "+self.an_cur[1])
        self.class_text.set("Class: "+str(self.an_cur[2]))

    def parse_yaml(self, f):
        with open(f, 'r') as stream:
            try:
                return yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def parse_db(self, db, collection):
        pp = db[collection]
        cnt = pp.count()
        print("Found %s entries" % cnt)
        if cnt == 0:
            raise KeyError("No entries in %s" % collection)
        print("Creating index.")
        pp.ensure_index("uuids")
        print("Getting list of uuids.")
        uuids = pp.distinct("uuids")
        print("Found %s people" % len(uuids))
        return [{self.__uuid: u, self.__class: None} for u in uuids]

    def euclidean_distance(self, human, robot):
        return numpy.sqrt(
            numpy.power(
                human.x-robot.x,
                2
            ) + numpy.power(
                human.y-robot.y,
                2
            )
        )

    def to_annotate(self, data_collection, config_collection, min_num_entries,
                 min_min_dist, min_travel_dist):
        for entry in config_collection.find():
            to_annotate = data_collection.find({"uuids": entry[self.__uuid]})
            if to_annotate.count() < min_num_entries:
                continue
            poses = []
            dist_h = 0.
            dist_r = 0.
            min_dist = 1000.
            for x in to_annotate:
                stamp = x["header"]["stamp"]
                person = x["people"][x["uuids"].index(entry[self.__uuid])]["pose"]
                res = {
                    "time": float(str(stamp["secs"])+"."+str(stamp["nsecs"])),
                    "human": Point(x=person["position"]["x"], y=person["position"]["y"]),
                    "robot": Point(x=x["robot"]["position"]["x"], y=x["robot"]["position"]["y"])
                }
                poses.append(res)
                try:
                    dist_h += self.euclidean_distance(poses[-2]["human"], poses[-1]["human"])
                    dist_r += self.euclidean_distance(poses[-2]["robot"], poses[-1]["robot"])
                except IndexError:
                    pass
                cd = self.euclidean_distance(poses[-1]["human"], poses[-1]["robot"])
                min_dist = cd if cd < min_dist else min_dist
            if min_dist > min_min_dist or dist_h < min_travel_dist or dist_r < min_travel_dist:
                continue
#            print("Called")
            yield sorted(poses, key=lambda x: x["time"]), entry[self.__uuid], entry[self.__class]

    def initialise(self, button_list=[], canvas_width=100, canvas_height=100):
        self.grid()

        __button_list = ["<"]
        __button_list.extend(button_list)
        __button_list.append(">")

        self.uuid_text = Tkinter.StringVar()
        label1 = Tkinter.Label(self, textvariable=self.uuid_text)
        label1.grid(column=0, row=0, columnspan=len(__button_list)-3)

        self.class_text = Tkinter.StringVar()
        label2 = Tkinter.Label(self, textvariable=self.class_text)
        label2.grid(column=len(__button_list)-3, row=0, columnspan=3)

        self.canvas = Tkinter.Canvas(self, width=canvas_width, height=canvas_height)
        self.canvas.grid(row=1, column=0, columnspan=len(button_list), sticky='EW')

        buttons = []
        for button in __button_list:
            button = button.replace(' ','-')
            buttons.append(Tkinter.Button(
                self,
                text=button,
                command=(lambda n: lambda: self.button_callback(n))(button)
            ))
            buttons[-1].grid(row=2, column=len(buttons)-1)

    def paint(self):
#        print("CALLED")
        human, robot = self.normalise_pose_data([x["human"] for x in self.an_cur[0]], [x["robot"] for x in self.an_cur[0]])
#        while self.draw:
#        print("WHILE_START")
        self.canvas.create_oval(human[0].x,human[0].y,human[0].x+2,human[0].y+2,fill="red")
        self.canvas.create_oval(robot[0].x,robot[0].y,robot[0].x+2,robot[0].y+2,fill="blue")
        for h0,r0,h1,r1 in zip(human[:-1], robot[:-1], human[1:], robot[1:]):
#            print(self.draw)
            if self.draw:
                self.canvas.create_line(h0.x, h0.y, h1.x, h1.y, fill="red", width=4)
                self.canvas.create_line(r0.x, r0.y, r1.x, r1.y, fill="blue", width=4)
                time.sleep(.2)
            else:
                break
#        print("WHILE_END")
#        try:
#            print ("DELETE")
#        except RuntimeError:
#            pass
#        print("END")

    def normalise_pose_data(self, human, robot):
        joined = deepcopy(human)
        joined.extend(robot)
        min_x = min([p.x for p in joined])
        max_x = max([p.x for p in joined])
        min_y = min([p.y for p in joined])
        max_y = max([p.y for p in joined])
#        print(min_x, max_x, min_y, max_y)

        res_h = []
        res_r = []
        for h, r in zip(human, robot):
            res_h.append(
                Point(
                    x=((h.x-min_x)/(max_x-min_x))*self.width,
                    y=((h.y-min_y)/(max_y-min_y))*self.height
                )
            )
            res_r.append(
                Point(
                    x=((r.x-min_x)/(max_x-min_x))*self.width,
                    y=((r.y-min_y)/(max_y-min_y))*self.height
                )
            )
        return res_h, res_r

    def button_callback(self, name):
        self.draw = False
#        print(name)
#        print(self.an_list.index(self.an_cur))
        if name == "<":
            idx = self.an_list.index(self.an_cur)-1
            if idx < 0:
                return
            self.an_cur = self.an_list[idx]
            self.update_text()
            self.t.join()
            self.canvas.delete("all")
            self.t = threading.Thread(target=self.paint)
            self.draw = True
            self.t.start()
            return

        if name != ">":
            self.update_db_entry(self.an_cur[1], name)
            idx = self.an_list.index(self.an_cur)
            self.an_list[idx] = (self.an_cur[0], self.an_cur[1], name)
            self.an_cur = self.an_list[idx]

        if self.an_list.index(self.an_cur) == len(self.an_list)-1:
            self.an_list.append(self.an_gen.next())
            self.an_cur = self.an_list[-1]
        else:
            self.an_cur = self.an_list[self.an_list.index(self.an_cur)+1]

        self.update_text()
        self.t.join()
        self.canvas.delete("all")
        self.t = threading.Thread(target=self.paint)
        self.draw = True
        self.t.start()

    def update_db_entry(self, uuid, name):
#        print (uuid,name)
        result = self.an_col.update(
            {self.__uuid: uuid},
            {
                "$set": {
                    self.__class: name
                }
            }
        )
#        print(result)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str,
                        help="Path to yaml config file")
#    parser.add_argument("save_path", type=str,
#                        help="Path to save the results under")
    parser.add_argument("--dbhost", type=str, default='localhost',
                        help="The database host IP.")
    parser.add_argument("--dbport", type=int, default=62345,
                        help="The database port")
    parser.add_argument("--db", type=str, default="message_store",
                        help="The database name")
    parser.add_argument("--data_collection", type=str, default="people_perception",
                        help="The collection in the database db that contains the people tracks")
    parser.add_argument("--annotation_collection", type=str, default="people_perception_annotations",
                        help="The collection in the database db that should contain the results")
    parser.add_argument("--min_num_entries", type=int, default=100,
                        help="The minimum number of entries per uuid to be considered for annotation")
    parser.add_argument("--min_min_dist", type=float, default=2.,
                        help="The minimum minimum distance of the human to the robot for a uuid to be considered for annotation")
    parser.add_argument("--min_travel_dist", type=float, default=3.,
                        help="The minimum travel distance accumulated over all poses of human and robot for a uuid to be considered for annotation")
    args = parser.parse_args()

    app = SimpleAppTk(
        config_file=args.config,
        save_path=None,
        host=args.dbhost,
        port=args.dbport,
        db_name=args.db,
        data_collection=args.data_collection,
        config_collection=args.annotation_collection,
        min_num_entries=args.min_num_entries,
        min_min_dist=args.min_min_dist,
        min_travel_dist=args.min_travel_dist
    )
    app.title("MyApp")
    app.mainloop()
    app.draw = False
    app.t.join()
