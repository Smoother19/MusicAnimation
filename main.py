import mp3toMidi
import mp3toAprèsMidi
import gui
import midiDecoder

inputfile = "PinkPanther_Both.mp3"

def main() :
    #isMidi = mp3toMidi.decode(inputfile)
    isMidi = mp3toAprèsMidi.decode(inputfile)
    midi_array, bpm = midiDecoder.decode() # RETURNS AS ARRAY : [STARTTIME;ENDTIME;NOTE(Hz)] & the BPM
    gui.start_gui(isMidi)

if __name__ == "__main__":
    main()