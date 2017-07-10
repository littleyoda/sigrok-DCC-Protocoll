##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2013 Sven Bursch-Osewold
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
##

import sigrokdecode as srd
from enum import Enum

class DCC(Enum):
     WAITINGFORPREAMBLE = 1
     PREAMBLE = 2
     ADDRESSDATABYTE = 3
#     CMDCODEPRE0 = 4
#     CMDCODE = 5
#     AOISUB = 6

class Decoder(srd.Decoder):
    dccCmds = ["Decoder and Consist Control Instruction", 		#0
              "Adv Instruction", 					#1
              "Speed and Direction Instruction for reverse operation",  #2
              "Speed and Direction Instruction for forward operation",  #3
              "F0-F4",	 						#4
              "F5-F8/F9-F12",						#5
              "Future Expansion",					#6
              "Configuration Variable Access Instruction"		#7
              ]

    # SubCommands for "Futre Expansion Instruction 110"
    subCmd = [
              "0", "1", "2","3","4",
              "5","6","7","8","9",
              "10", "11", "12","13","14",
              "15","16","17","18","19",
              "20", "21", "22","23","24",
              "25","26","27","28","29",
              "F13-F20", "F21-28"
              ]

    dccBitPos = []
    dccStatus = DCC.WAITINGFORPREAMBLE;
    dccStart = 0;
    dccLast = 0;
    dccCounter = 0;
    dccValue = 0;
    decodedBytes = [];
    
    api_version = 2
    id = 'dcc'
    name = 'DCC'
    longname = 'Digital Command Control (DCC)'
    desc = 'Decoder for Digital Command Control used to operate model railways.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['dcc']
    channels = (
        {'id': 'data', 'name': 'Data', 'desc': 'Data line'},
    )
    annotations = (
        ('Logical Bits', 'Logical Bigs'),
        ('DCC', 'DCC'),
    )
    annotation_rows = (
        ('bits', 'Bits', (0,)),
        ('data', 'Decoded', (1,)),
    )
    options = (
        {'id': 'Phase', 'desc': '01 or 10',
            'default': '01', 'values': ('01', '10')},
    )
 
    def putx(self, data):
        self.put(self.ss_edge, self.samplenum, self.out_ann, data)

    def __init__(self, **kwargs):
        self.olddata = None
        self.lastfall = None
        self.ss_edge = None
        self.first_transition = True
        self.bitwidth = None

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value;

    def handleDecodedBytes(self, d):
        if (len(d) < 2):
          return;        
        l = len(d);
        idx = 0
        self.put(d[idx][1][0], d[idx][1][8], self.out_ann, [1, ["Addr:" + str(d[idx][0])]])
        
        idx += 1
        cmd = d[idx][0] >> 5
        subcmd = d[idx][0] & 31
        self.put(d[idx][1][0], d[idx][1][3], self.out_ann, [1, [self.dccCmds[cmd]]])
        
        if (cmd == 1): ## Advanced Operations Instruction 001
          self.put(d[idx][1][3], d[idx][1][8], self.out_ann, [1, ["Adv. Operations Inst."]])
          if (subcmd == 31 and len(d) > 2):
            idx += 1                
            self.put(d[idx][1][0], d[idx][1][1], self.out_ann, [1, ["D"]])
            self.put(d[idx][1][1], d[idx][1][8], self.out_ann, [1, ["Speed:" + str(d[idx][0] & 127)]])

        elif (cmd == 4): ## Function Group One
          value = subcmd
          f = [ "F1", "F2", "F3", "F4", "F0" ]
          out = ""
          for i in range(0,len(f)):
            out = out + "F" + f[i] + ":" + str(value & 1) + " "
            value = value >> 1 
          self.put(d[idx][1][3], d[idx][1][8], self.out_ann, [1,[out]])

        elif (cmd == 5): ## Function Group Two
          value = subcmd
          f = 9;
          if (value & 16 == 16):
            f = 5;
          out = ""
          for i in range(0,5):
            out = out + "F" + str(f) + ":" + str(value & 1) + " "
            value = value >> 1 
            f += 1
          self.put(d[idx][1][3], d[idx][1][8], self.out_ann, [1,[out]])
            
        elif (cmd == 6): ## Futre Expansion Instruction 110
          self.put(d[idx][1][3], d[idx][1][8], self.out_ann, [1, ["Sub:" + self.subCmd[subcmd]]])

          if (subcmd in [30, 31]): #F13 - 20  // F21 to F28
            idx += 1
            value = d[idx][0]
            out = "";
            f = 0
            if (subcmd == 30):
                f = 13
            if (subcmd == 31):
                f = 21
            for x in range(0,8):
              out = out + "F" + str(f + x) + ":" + str(value & 1) + " " 
              value = value >> 1
              self.put(d[idx][1][0], d[idx][1][8], self.out_ann, [1, [out]])

            
        # Checksum
        if ((idx + 1) < l):
            checksum = d[0][0]
            for x in range(1, l - 1):
              checksum = checksum ^ d[x][0]
            if (checksum == d[l-1][0]):
              out = "CHECK: OK"
            else:
              out = "CHECK: " + str(checksum) + "/" + str(d[l-1][0])
            self.put(d[l - 1][1][0], d[l - 1][1][8], self.out_ann, [1, [out]])
            l -= 1
        for x in range(idx + 1, l):
            self.put(d[x][1][0], d[x][1][8], self.out_ann, [1, ["?: " + str(d[x][0])]])
          

    def setNextStatus(self, newstatus):
        self.handleDecodedBytes(self.decodedBytes);
        self.decodedBytes = []      
        self.dccCounter = 0
        self.dccValue = 0
        self.dccStatus = newstatus
    
    def collectDataBytes(self, start, stop, data):
          # Test for invalid bits
          if (data not in ["0", "1"]):
              self.setNextStatus(DCC.WAITINGFORPREAMBLE)
              
          # Wait for the first 1
          elif self.dccStatus == DCC.WAITINGFORPREAMBLE:
              if data == "1":
                  self.dccStart = start;
                  self.setNextStatus(DCC.PREAMBLE)
                  self.dccStart = start;
                  self.dccCounter = 1;
                  
          # Collect the Preamble Bits
          elif self.dccStatus == DCC.PREAMBLE:
              if data == "1":
                  self.dccCounter = self.dccCounter + 1;
                  self.dccLast = stop;
              else:
                  if (self.dccCounter >= 10):
                      self.put(self.dccStart, self.dccLast, self.out_ann, [1, ["Preamble"]])
                      self.put(start, stop, self.out_ann, [1, ["Start"]])
                      self.setNextStatus(DCC.ADDRESSDATABYTE)
                  else:
                      self.setNextStatus(DCC.WAITINGFORPREAMBLE)
          # Collection 8 databits and one bit indicating the end of data
          elif self.dccStatus == DCC.ADDRESSDATABYTE:   
                  if (self.dccCounter == 0):
                      self.dccValue = 0
                      self.dccStart = start
                      self.dccBitPos = []
                  if (self.dccCounter < 8):
                    self.dccBitPos.append(start)
                    self.dccCounter = self.dccCounter + 1;
                    value = int(data)
                    self.dccValue = ((self.dccValue) << 1) + value;
                    if self.dccCounter == 8:
                        self.dccBitPos.append(stop)
                        self.decodedBytes.append([self.dccValue, self.dccBitPos])
                  else:                  
                      # Test for end of sequence
                      if (data == "1"):
                        self.setNextStatus(DCC.WAITINGFORPREAMBLE)
                      else:
                          self.dccCounter = 0;
                          self.dccValue = 0;
          else:
              print("Unhandelt Status " + str(self.dccStatus))                              

            
    def decode(self, ss, es, data):
        if self.samplerate is None:
            raise Exception("Cannot decode without samplerate.")
        if self.options['Phase'] == '01':
            bit = 0
        else:
            bit = 1           
 
        for (self.samplenum, pins) in data:

            data = pins[0]

            # Wait for any transition on the data line.
            if data == self.olddata:
                continue

            # Initialize first self.olddata with the first sample value.
            if self.olddata == None:
                self.olddata = data
                self.lastfall = self.samplenum
                continue

            if data == bit:
                diff = (self.samplenum - self.lastfall)/self.samplerate * 1000000;
                if diff > (103 - 5) and diff < (129):
                    value = "1"
                elif   diff > (179) and diff < (243):
                    value = "0"
                else:
                    value = " (" + str(diff) + ")"
                self.put(self.lastfall, self.samplenum, self.out_ann, [0, [value]])
                self.collectDataBytes(self.lastfall, self.samplenum, value)
                self.lastfall = self.samplenum
            self.olddata = data
