import librosa
import numpy as np
import matplotlib.pyplot as plt

# Load the audio
y, sr = librosa.load(".\\sounds\\Ecossaise_Trumpet.mp3")

S = librosa.stft(y)

# Generate a plot of waveform and spectrogram
fig, ax = plt.subplots(nrows=2, sharex=True, height_ratios=(1, 4))
librosa.display.waveshow(y=y, sr=sr, ax=ax[0], label="Waveform")
img = librosa.display.specshow(S, vscale="dBFS", x_axis="time", y_axis="log", sr=sr)
librosa.display.colorbar_db(img, label="dBFS")
ax[0].label_outer()
ax[0].legend()

# Map the magnitude abs(S) to decibels
logS = librosa.amplitude_to_db(np.abs(S), ref=np.max)

# Compute the first-order difference logS[:, t] - logS[:, t-1]
# along the time direction.
# We'll pad the differencing operation with the first column of
# logS to prevent a spike in the first step.
# This also ensures that the output has the same number of frames as the
# input (`logS`), since the differencing operation would otherwise
# discard the first frame.
diffS = np.diff(logS, axis=-1, prepend=logS[:, :1])

# We'll threshold out any negative values as these correspond to
# falling energy
diffS_thresh = np.maximum(diffS, 0)

# Visualize the results
fig, ax = plt.subplots(nrows=3, sharex=True, sharey=True)
i1 = librosa.display.specshow(S, vscale="dBFS", x_axis="time", y_axis="log", ax=ax[0], sr=sr)
i2 = librosa.display.specshow(diffS, x_axis="time", y_axis="log", ax=ax[1], sr=sr)
i3 = librosa.display.specshow(diffS_thresh, x_axis="time", y_axis="log", ax=ax[2], sr=sr, norm=i2.norm, cmap=i2.cmap)

librosa.display.colorbar_db(i1, label="dBFS")
librosa.display.colorbar_db(i2, label="Δ dB")
librosa.display.colorbar_db(i3, label="Δ dB")
ax[0].label_outer()
ax[1].label_outer()
ax[0].set(ylabel="STFT")
ax[1].set(ylabel="Difference")
ax[2].set(ylabel="Thresholded diff")

# Average across frequencies to get the onset strength envelope
onset_env = np.mean(diffS_thresh, axis=0)

# Plot the waveform, spectrogram, and onset envelope together

fig, ax = plt.subplots(nrows=3, sharex=True, height_ratios=(1, 1, 4))
librosa.display.waveshow(y=y, sr=sr, ax=ax[0], label="Waveform")
img = librosa.display.specshow(S, vscale="dBFS", x_axis="time", y_axis="log", ax=ax[2], sr=sr)
librosa.display.colorbar_db(img, label="dBFS")
times = librosa.times_like(onset_env, sr=sr)
ax[1].plot(times, onset_env, label="Onset envelope", color="C1")
ax[1].legend()
ax[0].legend()
ax[0].label_outer()
ax[1].label_outer()

onset_peaks = librosa.util.localmax(onset_env)

fig, ax = plt.subplots(nrows=2, sharex=True, height_ratios=(3, 1))

librosa.display.waveshow(y=y, sr=sr, ax=ax[1], label="Waveform")
ax[1].legend()
ax[0].plot(times, onset_env, label="Onset envelope", color="C1")
ax[0].scatter(times[onset_peaks], onset_env[onset_peaks], marker="^", color="k", label="Peaks")
ax[0].legend()
ax[0].label_outer()

onset_detect = librosa.onset.onset_detect(onset_envelope=onset_env)

fig, ax = plt.subplots(nrows=2, sharex=True, height_ratios=(3, 1))

librosa.display.waveshow(y=y, sr=sr, ax=ax[1], label="Waveform")
ax[1].legend()
ax[0].plot(times, onset_env, label="Onset envelope", color="C1")
ax[0].scatter(times[onset_peaks], onset_env[onset_peaks], marker="^", color="k", label="Localmax Peaks")
ax[0].scatter(times[onset_detect], onset_env[onset_detect], marker="o",
              edgecolor="C2", facecolor="none", label="onset_detect")
ax[0].legend()
ax[0].label_outer()

# Generate a click track from the detected frames
# and match the length to the original input signal
clicks = librosa.clicks(frames=onset_detect, length=len(y), sr=sr)

onset_times = librosa.frames_to_time(onset_detect, sr=sr)

onset_times = librosa.onset.onset_detect(onset_envelope=onset_env,
                                         units="time")

print(onset_times)

clicks = librosa.clicks(times=onset_times, length=len(y), sr=sr)