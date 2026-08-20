import mp3toMidi
import gui
import midiDecoder

inputfile = "Never-Gonna-Give-You-Up.mid"

def main() :
    isMidi = mp3toMidi.decode(inputfile)
    midi_array, bpm = midiDecoder.decode() # RETURNS AS ARRAY : [STARTTIME;ENDTIME;NOTE(Hz)] & the BPM
    gui.start_gui(isMidi)

if __name__ == "__main__":
    main()