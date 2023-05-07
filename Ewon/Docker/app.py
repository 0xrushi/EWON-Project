#!/usr/bin/env python
# coding: utf-8

from time import sleep
import math
import multiprocessing 
from adafruit_servokit import ServoKit
import serial
import sys
import os
import re
import ipywidgets as widgets
import time
from adafruit_servokit import ServoKit
import time
import math
import multiprocessing 
from adafruit_servokit import ServoKit
import serial
import sys
import os
import re
from flask import Flask, jsonify, request

app = Flask(__name__)

left_ear_angles = {
    'front': 0,
    'back': 90,
    'mid_front': 45,
    'left': 133,
    'right': 45,
    'mid': 73
}

right_ear_angles = {
    'front': 180,
    'back': 90,
    'mid_front': 140,
    'left': 180,
    'right': 90,
    'mid': 110
}


e = "\xff\xff\xff"

try:
    ser = serial.Serial("/dev/ttyS0", 9600, timeout=5)
except serial.serialutil.SerialException:
    print('could not open serial device /dev/ttyS0')
    exit(1)
if serial.VERSION <= "3.0":
    if not ser.isOpen():
        ser.open()
    else:
        if not ser.is_open:
            ser.open()

def setDownloadBaudrate(ser, baudrate):
    ser.write(b"")
    #ser.write(("whmi-wri " + "," + str(baudrate) + ",0" + e).encode('utf-8'))
    time.sleep(.05)
    ser.baudrate = baudrate
    ser.timeout = .5
    r = ser.read(1)
    if b"\x05" in r:
        return True
    return False

def init():
    global ser
    setDownloadBaudrate(ser, 9600)

def display(images):
    for i in images:
        ser.write(b"p0.pic=")
        ser.write(bytes(str(i), 'utf-8'))
        ser.write(b"\xff\xff\xff")
        time.sleep(0.1)
        
def emotion_animations(em):
    if em=='sad_face':
        p = multiprocessing.Process(target=display, args=([13,14,15,16], ))
        p.start()
        sleep(1)
    elif em=="happy_face":
        p = multiprocessing.Process(target=display, args=([0,1,2,3,4,5,6], ))
        p.start()
        sleep(1)
    elif em=="angry_face":
        p = multiprocessing.Process(target=display, args=([7,8,9,10,11,12], ))
        p.start()
        sleep(1)
    elif em=="listen_face":
        p = multiprocessing.Process(target=display, args=([13,14,15,16,17,18,19], ))
        p.start()
        sleep(1)
    elif em=="default_face":
        p = multiprocessing.Process(target=display, args=([0,1,2,3,4,5], ))
        p.start()   
        sleep(1)        

# Initialize the ServoKit object and the servos
kit = ServoKit(channels=16)
left_ear_left_right_servo = kit.servo[0]
right_ear_left_right_servo = kit.servo[1]
left_ear_front_behind_servo = kit.servo[2]
right_ear_front_behind_servo = kit.servo[3]

# Define the functions to move the servos in different ways
def default_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['front']
    right_ear_front_behind_servo.angle = right_ear_angles['front']
    # bring both ears stay straight in the middle
    right_ear_left_right_servo.angle = right_ear_angles['mid']
    left_ear_left_right_servo.angle = left_ear_angles['mid']
    
    emotion_animations('default_face')
    

def happy_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['front']
    right_ear_front_behind_servo.angle = right_ear_angles['front']
    
    # oscillate left right
    for i in range(3):
        right_ear_left_right_servo.angle = right_ear_angles['left']
        left_ear_left_right_servo.angle = left_ear_angles['right']
        sleep(1)
        right_ear_left_right_servo.angle = right_ear_angles['right']
        left_ear_left_right_servo.angle = left_ear_angles['left']
        sleep(1)
    #add code to show happy face
    emotion_animations('happy_face')
    
def listen_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['front']
    right_ear_front_behind_servo.angle = right_ear_angles['front']
    
    right_ear_left_right_servo.angle = right_ear_angles['right']
    left_ear_left_right_servo.angle = left_ear_angles['left']
    

def sad_ears():
    # bring both ears face back
    left_ear_front_behind_servo.angle = left_ear_angles['back']
    right_ear_front_behind_servo.angle = right_ear_angles['back']
    
    # show sad face
    emotion_animations('sad_face')

def angry_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['front']
    right_ear_front_behind_servo.angle = right_ear_angles['front']
    
    right_ear_left_right_servo.angle = right_ear_angles['left']
    left_ear_left_right_servo.angle = left_ear_angles['right']
    # add code to show angry face
    emotion_animations('angry_face')

def fear_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['mid_front']
    right_ear_front_behind_servo.angle = right_ear_angles['mid_front']
    
    right_ear_left_right_servo.angle = right_ear_angles['left']
    left_ear_left_right_servo.angle = left_ear_angles['right']
    # add code to show fear face

def disgust_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['front']
    right_ear_front_behind_servo.angle = right_ear_angles['front']
    
    right_ear_left_right_servo.angle = right_ear_angles['right']
    left_ear_left_right_servo.angle = left_ear_angles['right']
    # https://i0.wp.com/media0.giphy.com/media/vcnV29vDVl8U6KJuiR/giphy.gif?resize=640%2C640&ssl=1&crop=1
    
    # add code for disgust emoji

def surprise_ears():
    # bring both ears face front
    left_ear_front_behind_servo.angle = left_ear_angles['front']
    right_ear_front_behind_servo.angle = right_ear_angles['front']
    
    right_ear_left_right_servo.angle = right_ear_angles['left']
    left_ear_left_right_servo.angle = left_ear_angles['mid']    
    # add code for surprise emoji

# Create a dictionary that maps emotions to their corresponding ear movements
emotion_ears = {
    'default': default_ears,
    'listen': listen_ears,
    'happy': happy_ears,
    'awesome': happy_ears,
    'sad': sad_ears,
    'upset': sad_ears,
    'disappointed': sad_ears,
    'angry': angry_ears,
    'furious': angry_ears,
    'fear': fear_ears,
    'scared': fear_ears,
    'disgust': disgust_ears,
    'surprise': surprise_ears,
    'exited': surprise_ears,
    'surprised': surprise_ears,
}

# Test the ear movements for each emotion
emotions = [
    ['default'],
    ['listen'],
    ['happy', 'awesome'],
    ['sad', 'upset', 'disappointed'],
    ['angry', 'furious'],
    ['fear', 'scared'],
    ['disgust'],
    ['surprise', 'exited', 'surprised'],
]

emotions = [['sad']]


def parse_emotion(em="sad"):
    emotions = [[em]]
    try:
        for emotion_list in emotions:
            for emotion in emotion_list:
                print(f"Performing ear movements for {emotion}...")
                emotion_ears[emotion]()  # Call the corresponding ear movement function
                time.sleep(2)
            print("Returning to default position...")
            default_ears()  # Reset the ear
            return True
    except:
        return False


@app.route('/parse_emotion', methods=['GET'])
def get_emotion():
    query = request.args.get('query', default='', type=str)
    if parse_emotion(query):
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')