import mp3toMidi
import gui
import midiDecoder

inputfile = "PinkPanther_Trumpet_Only.mp3"

def main() :
    mp3toMidi.decode(inputfile)
    midi_array = midiDecoder.decode() # RETURNS AS ARRAY : [STARTTIME;ENDTIME;NOTE(Hz)]
    gui.start_gui()

if __name__ == "__main__":
    main()