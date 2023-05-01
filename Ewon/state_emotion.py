import threading
import time
from servoMovementAndDisplay import default, init, listen, happy, sad, angry, fear, disgust, surprise

exitFlag = 0
first = True
current_emotion = 1
previous_emotion = 1


def animateServosAndDisplay(emotion):
    if emotion == 0: #default
        default()
    elif emotion == 1: #listen
        listen()
    elif emotion == 2: #happy
        happy()
    elif emotion == 3: #sad
        sad()
    elif emotion == 4:
        angry()
    elif emotion == 5:
        fear()
    elif emotion == 6:
        disgust()
    elif emotion == 7:
        surprise()

class Animation (threading.Thread):
    def __init__(self, startEmotion):
        init()
        threading.Thread.__init__(self)
        current_emotion = startEmotion
        previous_emotion = startEmotion
    
    
        
    def run(self):
        global first
        while True:
            if first:
                print("animating")
                previous_emotion = current_emotion
                first = False
                animateServosAndDisplay(current_emotion)
            else:
                if current_emotion != previous_emotion:
                    previous_emotion = current_emotion
                    animateServosAndDisplay(current_emotion)
                    print("animating")



# Create new threads


# Start new Threads
Animation(1).start()

print("Exiting Main Thread")