import mp3toMidi
import gui
import midiDecoder
import mp3toMidi_RMS

inputfile = "song.mp3"

def main() :
    #isMidi = mp3toMidi.decode(inputfile)
    isMidi = mp3toMidi_RMS.decode(inputfile)
    midi_array, bpm = midiDecoder.decode() # RETURNS AS ARRAY : [STARTTIME;ENDTIME;NOTE(Hz)] & the BPM
    gui.start_gui(isMidi)

if __name__ == "__main__":
    main()