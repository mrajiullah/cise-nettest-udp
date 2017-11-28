#!/usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import division
# Author: Mohammad Rajiullah (Used general experiment logic from 
# Jonas Karlsson)
# Date: October 2016
# License: GNU General Public License v3
# Developed for use by the EU H2020 MONROE project

"""
A Linux based lightweight tool to estimate available down-link bandwidth. 
UDPbwEstimator consists of a server that sends n number of back to back UDP 
packets in the beginning of each second. The receiver tells the server about
 the number of packets, bursts to be sent. Then receiver calculates the
  bandwidth using packet arrival times and payloads.
"""

import datetime
import dateutil.relativedelta

import sys, getopt
import time, os
import fileinput
import subprocess

import json
import zmq
import netifaces
import time
from subprocess import check_output, CalledProcessError
from multiprocessing import Process, Manager
from netifaces import AF_INET, AF_INET6, AF_LINK, AF_PACKET, AF_BRIDGE
import netifaces as ni


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

# Configuration
DEBUG = True
CONFIGFILE = '/monroe/config'

# Default values (overwritable from the scheduler)
# Can only be updated from the main thread and ONLY before any
# other processes are started
EXPCONFIG = {
        "guid": "no.guid.in.config.file",  # Should be overridden by scheduler
        "url": "http://193.10.227.25/test/1000M.zip",
        "size": 3*1024,  # The maximum size in Kbytes to download
        "time": 3600,  # The maximum time in seconds for a download
        "zmqport": "tcp://172.17.0.1:5556",
        "modem_metadata_topic": "MONROE.META.DEVICE.MODEM",
        "dataversion": 1,
        "dataid": "MONROE.EXP.UDPBWESTIMATOR",
        "nodeid": "fake.nodeid",
        "meta_grace": 120,  # Grace period to wait for interface metadata
        "exp_grace": 120,  # Grace period before killing experiment
        "ifup_interval_check": 5,  # Interval to check if interface is up
        "time_between_experiments": 5,
        "verbosity": 2,  # 0 = "Mute", 1=error, 2=Information, 3=verbose
        "resultdir": "/monroe/results/",
        "modeminterfacename": "InternalInterface",
        "allowed_interfaces": ["op0",
                               "op1",
                               "op2"],  # Interfaces to run the experiment on
        "interfaces_without_metadata": [ ]  # Manual metadata on these IF
        }


def run_exp(expconfig,ip):
    """Seperate process that runs the experiment and collect the ouput.

        Will abort if the interface goes down.
    """
    ifname = meta_info[expconfig["modeminterfacename"]]

    har_stats={}
    burst_sz="300"
    no_bursts="10"
    cmd=["./UDPbwEstimatorRcvr","-c",burst_sz,"-b",no_bursts,"-l","1400","-s",ip,"-o",
	   "8000",
            "-d", 
	   "193.10.227.44",
	   "-p", 
	   "8080",
	   "-w",
	   "test"]

    output=None
     
    try:
        output=check_output(cmd)
	output = output.strip(' \t\r\n\0')
	
    except CalledProcessError as error:
        if error.returncode == 28:
	    print "Time limit exceeded"
    
    logfile=open("test","r")
    num_packets=0

    first=0
    total_bytes=0
    count=0
    bw=""
    while True:
    	line=logfile.readline()
    	if line =='\n' or line == "":
        	count+=1
        	first=0
        	duration=float(tstamp)-float(start)
        	print ((total_bytes*8)/(1024*1024))
        	print duration, sizeof_fmt(total_bytes), ((total_bytes*8)/(1024*1024))/duration
    		bw+=str(((total_bytes*8)/(1024*1024))/duration)
		bw+=" "
        	total_bytes=0
        	if count==3:
            		break
    	else:
        	line = line.strip().split(' ')
        	num_packets=num_packets+1
        	if first==0:
            		start, numbytes=line[0], int(line[1])
            		total_bytes+=numbytes
            		first=1
        	else:
            		tstamp, numbytes=line[0], int(line[1])
            		total_bytes+=numbytes

    print num_packets
    logfile.close()
    har_stats["burst_sz"]=burst_sz
    har_stats["no_bursts"]=no_bursts
    har_stats["bw"]=output
    har_stats["bw1"]=bw
    har_stats["Guid"]= expconfig['guid']
    har_stats["DataId"]= expconfig['dataid']
    har_stats["DataVersion"]= expconfig['dataversion']
    har_stats["NodeId"]= expconfig['nodeid']
    har_stats["Timestamp"]= time.time()
    try:
    	har_stats["Iccid"]= meta_info["ICCID"]
    except Exception:
    	print("ICCID info is not available")
    try:
    	har_stats["Operator"]= meta_info["Operator"]
    except Exception:
    	print("Operator info is not available")
    try:
    	har_stats["IMSI"]=meta_info["IMSI"]
    except Exception:
    	print("IMSI info is not available")
    try:
    	har_stats["IMEI"]=meta_info["IMEI"]
    except Exception:
    	print("IMEI info is not available")
    try:
    	har_stats["InternalInterface"]=meta_info["InternalInterface"]
    except Exception:
    	print("InternalInterface info is not available")
    try:
    	har_stats["IPAddress"]=meta_info["IPAddress"]
    except Exception:
    	print("IPAddress info is not available")
    try:
    	har_stats["InternalIPAddress"]=meta_info["InternalIPAddress"]
    except Exception:
    	print("InternalIPAddress info is not available")
    try:
    	har_stats["InterfaceName"]=meta_info["InterfaceName"]
    except Exception:
    	print("InterfaceName info is not available")
    try:
    	har_stats["IMSIMCCMNC"]=meta_info["IMSIMCCMNC"]
    except Exception:
    	print("IMSIMCCMNC info is not available")
    try:
    	har_stats["NWMCCMNC"]=meta_info["NWMCCMNC"]
    except Exception:
    	print("NWMCCMNC info is not available")
    try:
    	har_stats["LAC"]=meta_info["LAC"]
    except Exception:
    	print("LAC info is not available")
    try:
    	har_stats["CID"]=meta_info["CID"]
    except Exception:
    	print("CID info is not available")
    try:
    	har_stats["RSCP"]=meta_info["RSCP"]
    except Exception:
    	print("RSCP info is not available")
    try:
    	har_stats["RSSI"]=meta_info["RSSI"]
    except Exception:
    	print("RSSI info is not available")
    try:
    	har_stats["ECIO"]=meta_info["ECIO"]
    except Exception:
    	print("ECIO info is not available")
    try:
    	har_stats["DeviceMode"]=meta_info["DeviceMode"]
    except Exception:
    	print("DeviceMode info is not available")
    try:
    	har_stats["DeviceSubmode"]=meta_info["DeviceSubmode"]
    except Exception:
    	print("DeviceSubmode info is not available")
    try:
    	har_stats["DeviceState"]=meta_info["DeviceState"]
    except Exception:
    	print("DeviceState info is not available")
    har_stats["SequenceNumber"]= 1
  
    
    if expconfig['verbosity'] > 2:
            print har_stats
    if not DEBUG:
	    print har_stats
            monroe_exporter.save_output(har_stats, expconfig['resultdir'])
 
  

def metadata(meta_ifinfo, ifname, expconfig):
    """Seperate process that attach to the ZeroMQ socket as a subscriber.

        Will listen forever to messages with topic defined in topic and update
        the meta_ifinfo dictionary (a Manager dict).
    """
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(expconfig['zmqport'])
    socket.setsockopt(zmq.SUBSCRIBE, expconfig['modem_metadata_topic'])
    # End Attach
    while True:
        data = socket.recv()
        try:
            ifinfo = json.loads(data.split(" ", 1)[1])
            if (expconfig["modeminterfacename"] in ifinfo and
                    ifinfo[expconfig["modeminterfacename"]] == ifname):
                # In place manipulation of the reference variable
                for key, value in ifinfo.iteritems():
                    meta_ifinfo[key] = value
        except Exception as e:
            if expconfig['verbosity'] > 0:
                print ("Cannot get modem metadata in http container {}"
                       ", {}").format(e, expconfig['guid'])
            pass


# Helper functions
def check_if(ifname):
    """Check if interface is up and have got an IP address."""
    return (ifname in netifaces.interfaces() and
            netifaces.AF_INET in netifaces.ifaddresses(ifname))


def check_meta(info, graceperiod, expconfig):
    """Check if we have recieved required information within graceperiod."""
    return (expconfig["modeminterfacename"] in info and
            "Operator" in info and
            "Timestamp" in info and
            time.time() - info["Timestamp"] < graceperiod)


def add_manual_metadata_information(info, ifname, expconfig):
    """Only used for local interfaces that do not have any metadata information.

       Normally eth0 and wlan0.
    """
    info[expconfig["modeminterfacename"]] = ifname
    info["Operator"] = "local"
    info["Timestamp"] = time.time()
    info["InternalIPAddress"]="130.243.26.22"


def create_meta_process(ifname, expconfig):
    meta_info = Manager().dict()
    process = Process(target=metadata,
                      args=(meta_info, ifname, expconfig, ))
    process.daemon = True
    return (meta_info, process)


def create_exp_process(expconfig,ip):
    process = Process(target=run_exp, args=(expconfig,ip))
    process.daemon = True
    return process


if __name__ == '__main__':
    """The main thread control the processes (experiment/metadata))."""
    # Settings related to browsing 

    if not DEBUG:
        import monroe_exporter
        # Try to get the experiment config as provided by the scheduler
        try:
            with open(CONFIGFILE) as configfd:
                EXPCONFIG.update(json.load(configfd))
        except Exception as e:
            print "Cannot retrive expconfig {}".format(e)
            raise e
    else:
        # We are in debug state always put out all information
        EXPCONFIG['verbosity'] = 3

    # Short hand variables and check so we have all variables we need
    try:
        allowed_interfaces = EXPCONFIG['allowed_interfaces']
        if_without_metadata = EXPCONFIG['interfaces_without_metadata']
        meta_grace = EXPCONFIG['meta_grace']
        exp_grace = EXPCONFIG['exp_grace'] + EXPCONFIG['time']
        ifup_interval_check = EXPCONFIG['ifup_interval_check']
        time_between_experiments = EXPCONFIG['time_between_experiments']
        EXPCONFIG['guid']
        EXPCONFIG['modem_metadata_topic']
        EXPCONFIG['zmqport']
        EXPCONFIG['verbosity']
        EXPCONFIG['resultdir']
        EXPCONFIG['modeminterfacename']
    except Exception as e:
        print "Missing expconfig variable {}".format(e)
        raise e

    for ifname in allowed_interfaces:
        # Interface is not up we just skip that one
        if not check_if(ifname):
            if EXPCONFIG['verbosity'] > 1:
                print "Interface is not up {}".format(ifname)
            continue
        # set the default route
            

        # Create a process for getting the metadata
        # (could have used a thread as well but this is true multiprocessing)
        meta_info, meta_process = create_meta_process(ifname, EXPCONFIG)
        meta_process.start()

        if EXPCONFIG['verbosity'] > 1:
            print "Starting Experiment Run on if : {}".format(ifname)

        # On these Interfaces we do net get modem information so we hack
        # in the required values by hand whcih will immeditaly terminate
        # metadata loop below
        if (check_if(ifname) and ifname in if_without_metadata):
            add_manual_metadata_information(meta_info, ifname, EXPCONFIG)
#
        # Try to get metadadata
        # if the metadata process dies we retry until the IF_META_GRACE is up
        start_time = time.time()
        while (time.time() - start_time < meta_grace and
               not check_meta(meta_info, meta_grace, EXPCONFIG)):
            if not meta_process.is_alive():
                # This is serious as we will not receive updates
                # The meta_info dict may have been corrupt so recreate that one
                meta_info, meta_process = create_meta_process(ifname,
                                                              EXPCONFIG)
                meta_process.start()
            if EXPCONFIG['verbosity'] > 1:
                print "Trying to get metadata"
            time.sleep(ifup_interval_check)

        # Ok we did not get any information within the grace period
        # we give up on that interface
        if not check_meta(meta_info, meta_grace, EXPCONFIG):
            if EXPCONFIG['verbosity'] > 1:
                print "No Metadata continuing"
            continue

        # Ok we have some information lets start the experiment script


	    output_interface=None

        cmd1=["route",
             "del",
             "default"]
        #os.system(bashcommand)
       # try:
        #        check_output(cmd1)
      #  except CalledProcessError as e:
       #         if e.returncode == 28:
        #                print "Time limit exceeded"
      #  gw_ip="192.168."+str(meta_info["InternalIPAddress"].split(".")[2])+".1"
      #  cmd2=["route", "add", "default", "gw", gw_ip,str(ifname)]
      #  try:
              #  check_output(cmd2)
       # 	cmd3=["ip", "route", "get", "8.8.8.8"]
              #  output=check_output(cmd3)
        #	output = output.strip(' \t\r\n\0')
        #	output_interface=output.split(" ")[4]
        #	if output_interface==str(ifname):
         #       	print "Source interface is set to "+str(ifname)
	#	else:
	#		continue
        
#	except CalledProcessError as e:
 #           	if e.returncode == 28:
  #              	print "Time limit exceeded"
#		continue
	

        if EXPCONFIG['verbosity'] > 1:
            print "Starting experiment"
        
        # Create a experiment process and start it
        start_time_exp = time.time()
	iface_ip= str(ni.ifaddresses(ifname)[AF_INET][0]['addr'])
	print iface_ip
        exp_process = exp_process = create_exp_process(EXPCONFIG,iface_ip)
        exp_process.start()
        
        while (time.time() - start_time_exp < exp_grace and
                     exp_process.is_alive()):
        
		if not (check_if(ifname) and check_meta(meta_info,
                                                            meta_grace,
	                                                            EXPCONFIG)):
			if EXPCONFIG['verbosity'] > 0:
                        	print "Interface went down during a experiment"
                	break
            	elapsed_exp = time.time() - start_time_exp
            	if EXPCONFIG['verbosity'] > 1:
               		print "Running Experiment for {} s".format(elapsed_exp)
            	time.sleep(ifup_interval_check)
        
        if exp_process.is_alive():
            exp_process.terminate()
        if meta_process.is_alive():
            meta_process.terminate()
        
        elapsed = time.time() - start_time
        if EXPCONFIG['verbosity'] > 1:
        	print "Finished {} after {}".format(ifname, elapsed)
        time.sleep(time_between_experiments)

    if EXPCONFIG['verbosity'] > 1:
        print ("Interfaces {} "
               "done, exiting").format(allowed_interfaces)
