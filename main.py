import mp3toMidi
import gui

def main() :
    mp3toMidi.decode("PinkPanther_Piano_Only.mp3")
    gui.start_gui()

if __name__ == "__main__":
    main()