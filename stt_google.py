import pyaudio
import wave
import audioop
from collections import deque
import os
import urllib2
import urllib
import time
import math
import speech_recognition as sr
import cleverbot
import tungsten


cb=cleverbot.Cleverbot()
wa=tungsten.Tungsten('TY2G9V-VG865JGGTG')
LANG_CODE = 'en-US'  # Language to use

GOOGLE_SPEECH_URL = 'https://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&pfilter=2&lang=%s&maxresults=6' % (LANG_CODE)

FLAC_CONV = 'flac -f'  # We need a WAV to FLAC converter. flac is available
                       # on Linux

# Microphone stream config.
CHUNK = 1024  # CHUNKS of bytes to read each time from mic
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
THRESHOLD = 3800  # The threshold intensity that defines silence
                  # and noise signal (an int. lower than THRESHOLD is silence).

SILENCE_LIMIT = 1.5  # Silence limit in seconds. The max ammount of seconds where
                   # only silence is recorded. When this time passes the
                   # recording finishes and the file is delivered.

PREV_AUDIO = 2  # Previous audio (in seconds) to prepend. When noise
                  # is detected, how much of previously recorded audio is
                  # prepended. This helps to prevent chopping the beggining
                  # of the phrase.

def audio_int(num_samples=50):
    """ Gets average audio intensity of your mic sound. You can use it to get
        average intensities while you're talking and/or silent. The average
        is the avg of the 20% largest intensities recorded.
    """

    #print "Getting intensity values from mic."
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    values = [math.sqrt(abs(audioop.avg(stream.read(CHUNK), 4)))
              for x in range(num_samples)]
    values = sorted(values, reverse=True)
    r = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
    #print " Finished "
    #print " Average audio intensity is ", r
    stream.close()
    p.terminate()
    return r


def listen_for_speech(threshold=THRESHOLD, num_phrases=-1):
    """
    Listens to Microphone, extracts phrases from it and sends it to
    Google's TTS service and returns response. a "phrase" is sound
    surrounded by silence (according to threshold). num_phrases controls
    how many phrases to process before finishing the listening process
    (-1 for infinite).
    """

    #Open stream
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print "* Listening mic. "
    audio2send = []
    cur_data = ''  # current chunk  of audio data
    rel = RATE/CHUNK
    slid_win = deque(maxlen=SILENCE_LIMIT * rel)
    #Prepend audio from 0.5 seconds before noise was detected
    prev_audio = deque(maxlen=PREV_AUDIO * rel)
    started = False
    n = num_phrases
    response = []

    while (num_phrases == -1 or n > 0):
        cur_data = stream.read(CHUNK)
        slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
        #print slid_win[-1]
        if(sum([x > THRESHOLD for x in slid_win]) > 0):
            if(not started):
                print "Starting record of phrase"
                started = True
            audio2send.append(cur_data)
        elif (started is True):
            print "Finished"
            # The limit was reached, finish capture and deliver.
            filename = save_speech(list(prev_audio) + audio2send, p)
            # Send file to Google and get response
            r = recognize(filename)
            if num_phrases == -1:
                print "Response", r
            else:
                response.append(r)
            # Remove temp file. Comment line to review.
            os.remove(filename)
            # Reset all
            started = False
            slid_win = deque(maxlen=SILENCE_LIMIT * rel)
            prev_audio = deque(maxlen=0.5 * rel)
            audio2send = []
            n -= 1
            print "Listening ..."
        else:
            prev_audio.append(cur_data)

    print "* Done recording"
    stream.close()
    p.terminate()

    return response


def save_speech(data, p):
    """ Saves mic data to temporary WAV file. Returns filename of saved
        file """

    filename = 'output'
    # writes data to WAV file
    data = ''.join(data)
    wf = wave.open(filename + '.wav', 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)  # TODO make this value a function parameter?
    wf.writeframes(data)
    wf.close()
    return filename + '.wav'

def recognize(filename):
    r = sr.Recognizer()
    with sr.WavFile(filename) as source: # use "test.wav" as the audio source
        audio = r.record(source) # extract audio data from the file

        try:
            #print "Transcription: " + r.recognize(audio)# recognize speech using Google Speech Recognition
            said=r.recognize(audio)
            THRESHOLD=10000
            doit(said)
        except LookupError: # speech is unintelligible
            print "Could not understand audio"

def doit(userin):
    if userin.startswith("how did") or userin.startswith("who is") or userin.startswith("what is") or userin.startswith("when was") or userin.startswith("how many") or userin.startswith("who was"):
        result=wa.query(userin)
        for pod in result.pods:
            if pod.id == 'Result':
                leslis = pod.format.get('plaintext')
            elif pod.id == 'NotableFacts:PeopleData':
                leslis = pod.format.get('plaintext')
        for string in leslis:
            les = string
        jarvis = False
    elif userin=="shut down":
        les = "shut it down ya bro"
        os.system("shutdown now")
        jarvis = False
    elif userin=="play music" or userin=="stop music":
        les = userin.split(' ', 1)[0] + "ing music"
        os.system("mpc toggle")
        jarvis = False
    elif userin.startswith("open "):
        les = "running " + userin.split()[-1]
        torun = userin.split()[-1].lower() + " &"
        os.system(torun)
        jarvis = False
    elif userin.startswith("close "):
        les = "closing " + userin.split()[-1]
        toclose = "killall " + userin.split()[-1].lower()
        os.system(toclose)
        jarvis = False
    else:
        les = cb.ask(userin)
    command = "say \"" + les + "\""
    os.system(command)
    time.sleep(len(les)/25)
    THRESHOLD=3800

def jar_vis(userin):
    if userin.lower() == "jarvis":
        jarvis = True
        os.system("espeak \" what can I do for you today, sir\"")

if(__name__ == '__main__'):
    listen_for_speech()
    #recognize()
    #print stt_google_wav('output.wav')  # translate audio file
    #audio_int()  # To measure your mic levels
