#!/usr/bin/env python3
import os
import sys
import sounddevice as sd
import numpy as np
import matplotlib
# Agg backend を使用して GUI 表示はせずにファイル保存する
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
import contextlib
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning, module='matplotlib.font_manager')

# オーディオ設定
RATE = 44100          # サンプリングレート
DURATION = 30         # テスト時間（秒）
FREQUENCY = 1000      # 再生するサイン波の周波数 (Hz)
CHANNELS = 1          # モノラル

def generate_sine_wave(frequency, duration, rate):
    t = np.linspace(0, duration, int(rate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t)

def play_and_record():
    print("Generating sine wave...")
    sine_wave = generate_sine_wave(FREQUENCY, DURATION, RATE)
    recorded_data = np.zeros((int(RATE * DURATION), CHANNELS))

    # Callback function for playback and recording
    def callback(in_data, out_data, frames, time_info, status):
        start = callback.frame
        # Processing playback data
        if start >= len(sine_wave):
            out_data[:] = np.zeros((frames, CHANNELS))
        else:
            frames_to_copy = min(len(sine_wave) - start, frames)
            out_data[:frames_to_copy] = sine_wave[start:start+frames_to_copy].reshape(-1, CHANNELS)
            if frames_to_copy < frames:
                out_data[frames_to_copy:] = np.zeros((frames - frames_to_copy, CHANNELS))
        # Processing recording data
        frames_to_copy = min(len(recorded_data) - start, frames)
        if frames_to_copy > 0:
            recorded_chunk = np.frombuffer(in_data, dtype=np.float32).reshape(-1, CHANNELS)
            recorded_data[start:start+frames_to_copy] = recorded_chunk[:frames_to_copy]
        callback.frame += frames

    callback.frame = 0

    print("Starting playback and recording...")
    with sd.Stream(samplerate=RATE, channels=CHANNELS, dtype='float32', callback=callback):
        sd.sleep(int((DURATION + 0.5) * 1000))
    print("Playback and recording finished.")

    # Calculate correlation coefficients for each segment
    segment_duration = 2  # Duration of each segment in seconds
    start_time_seg = 3    # Start time in seconds
    end_time_seg = DURATION - segment_duration
    correlations = []
    segment_times = []

    while start_time_seg <= end_time_seg:
        start_sample = int(RATE * start_time_seg)
        end_sample = int(RATE * (start_time_seg + segment_duration))
        sine_segment = sine_wave[start_sample:end_sample]
        recorded_segment = recorded_data.flatten()[start_sample:end_sample]

        # Normalize the signals
        sine_norm = sine_segment / np.max(np.abs(sine_segment))
        recorded_norm = recorded_segment / np.max(np.abs(recorded_segment))

        # Scale recorded signal to match sine wave amplitude
        scaling_factor = np.max(np.abs(sine_segment)) / (np.max(np.abs(recorded_segment)) + 1e-8)
        recorded_scaled = recorded_segment * scaling_factor

        # Normalize the scaled recorded signal
        recorded_scaled_norm = recorded_scaled / np.max(np.abs(recorded_scaled))

        # Invert the recorded signal
        recorded_inverted = -recorded_scaled_norm

        # Calculate the correlation coefficients
        corr = np.corrcoef(sine_norm, recorded_scaled_norm)[0, 1]
        corr_inv = np.corrcoef(sine_norm, recorded_inverted)[0, 1]

        # Select the best correlation coefficient
        final_corr = corr if abs(corr) > abs(corr_inv) else corr_inv

        print(f"Segment {start_time_seg}-{start_time_seg + segment_duration}s: Correlation coefficient = {final_corr:.4f}")
        correlations.append(abs(final_corr))
        segment_times.append(start_time_seg)
        start_time_seg += segment_duration

    mean_corr = np.mean(correlations)
    print(f"\nAverage Correlation Coefficient: {mean_corr:.4f}")
    if mean_corr > 0.6:
        print("Test Result: Sound test success!")
    else:
        print("Test Result: Sound test failed.")

    # 保存先は、このスクリプトの1階層上
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    current_date = datetime.now().strftime("%Y%m%d")

    # Plot the original sine wave and recorded signal
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    time_axis = np.linspace(0, DURATION, len(sine_wave))
    plt.plot(time_axis, sine_wave, label='Original Sine Wave')
    plt.title('Original Sine Wave')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.grid(True)
    plt.legend()
    plt.subplot(2, 1, 2)
    time_axis = np.linspace(0, DURATION, len(recorded_data))
    plt.plot(time_axis, recorded_data.flatten(), label='Recorded Signal')
    for st in segment_times:
        plt.axvline(x=st, color='red', linestyle='--', alpha=0.7)
        plt.axvline(x=st + segment_duration, color='red', linestyle='--', alpha=0.7)
    plt.title('Recorded Signal with Segment Boundaries')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    # 保存ファイルのパスを作成
    save_path1 = os.path.join(save_dir, f"{current_date}_original_recorded_signals.png")
    plt.savefig(save_path1)
    plt.close()

    # Plot the correlation coefficients for each segment
    plt.figure(figsize=(10, 5))
    plt.plot(segment_times, correlations, marker='o', linestyle='-', color='blue')
    plt.title('Correlation Coefficient for Each Segment')
    plt.xlabel('Start Time of Segment (s)')
    plt.ylabel('Absolute Correlation Coefficient')
    plt.ylim(0, 1)
    plt.grid(True)
    plt.tight_layout()
    save_path2 = os.path.join(save_dir, f"{current_date}_correlation_coefficients.png")
    plt.savefig(save_path2)
    plt.close()

if __name__ == "__main__":
    with contextlib.redirect_stderr(open(os.devnull, 'w')):
        play_and_record()
