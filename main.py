import mp3toMidi
import gui
import midiDecoder
import mp3toMidi_RMS
import mp3toMidi_salience

inputfile = "PinkPanther_Piano_Only.mp3"

def main():
    #isMidi = mp3toMidi.decode(inputfile)
    isMidi = mp3toMidi_RMS.decode(inputfile)
    #isMidi = mp3toMidi_salience.decode(inputfile)

    midi_array, bpm = midiDecoder.decode()
    gui.start_gui(isMidi)

if __name__ == "__main__":
    main()