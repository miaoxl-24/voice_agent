import pyaudio
import dashscope
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from dashscope.audio.asr import Recognition, RecognitionCallback
from dashscope import Generation
import threading
import time
import wave
import io

API_KEY = ""
dashscope.api_key = API_KEY

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

def get_audio_devices():
    p = pyaudio.PyAudio()
    devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            devices.append({
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': int(info['defaultSampleRate'])
            })
    p.terminate()
    return devices

def get_best_microphone():
    devices = get_audio_devices()
    if not devices:
        return None

    problematic_devices = {12, 13, 14, 15, 19}

    for d in devices:
        if d['index'] == 0:
            return d

    for d in devices:
        name_lower = d['name'].lower()
        if d['index'] in problematic_devices:
            continue
        if 'mic' in name_lower or '麦克风' in name_lower:
            if 'speaker' not in name_lower and '扬声器' not in name_lower:
                return d

    for d in devices:
        if d['index'] not in problematic_devices:
            return d

    return devices[0]

class VoiceAgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("语音智能助手")
        self.root.geometry("700x600")

        self.is_recording = False
        self.stream = None
        self.p = None
        self.audio_thread = None
        self.audio_frames = []

        self.devices = get_audio_devices()
        self.selected_device = get_best_microphone()

        self.create_widgets()

    def create_widgets(self):
        self.title_label = tk.Label(self.root, text="🎤 语音智能助手", font=("Arial", 16, "bold"))
        self.title_label.pack(pady=10)

        device_frame = tk.LabelFrame(self.root, text="🎤 麦克风设备选择", font=("Arial", 12))
        device_frame.pack(fill="x", padx=20, pady=5)

        problematic_devices = {12, 13, 14, 15, 19}

        self.device_var = tk.StringVar()
        if self.devices:
            device_names = []
            default_idx = 0
            for i, d in enumerate(self.devices):
                name = d['name']
                is_problematic = d['index'] in problematic_devices

                if is_problematic:
                    display_name = f"🚫 {d['index']}: {name} (设备异常)"
                elif self.selected_device and d['index'] == self.selected_device['index']:
                    display_name = f"🎤 {d['index']}: {name} (已选择)"
                    default_idx = i
                elif 'Mic input' in name or ('麦克风' in name and '阵列' not in name):
                    display_name = f"✅ {d['index']}: {name} (推荐)"
                    if not self.selected_device or self.selected_device['index'] in problematic_devices:
                        default_idx = i
                else:
                    display_name = f"🎤 {d['index']}: {name}"

                device_names.append(display_name)

            self.device_var.set(device_names[default_idx])

            self.device_combo = ttk.Combobox(device_frame, textvariable=self.device_var,
                                           values=device_names, state="readonly", width=70)
            self.device_combo.pack(padx=10, pady=5)
            self.device_combo.bind('<<ComboboxSelected>>', self.on_device_selected)
        else:
            tk.Label(device_frame, text="⚠️ 未检测到麦克风设备", fg="red").pack(padx=10, pady=5)

        self.status_label = tk.Label(self.root, text="状态：等待开始", font=("Arial", 12), fg="gray")
        self.status_label.pack(pady=5)

        self.volume_frame = tk.LabelFrame(self.root, text="音量指示", font=("Arial", 10))
        self.volume_frame.pack(fill="x", padx=20, pady=5)

        self.volume_label = tk.Label(self.volume_frame, text="静音", font=("Arial", 10))
        self.volume_label.pack(side="left", padx=10, pady=5)

        self.volume_canvas = tk.Canvas(self.volume_frame, width=200, height=20, bg="white")
        self.volume_canvas.pack(side="right", padx=10, pady=5)
        self.volume_bar = self.volume_canvas.create_rectangle(0, 0, 0, 20, fill="#4CAF50")

        self.record_btn = tk.Button(
            self.root,
            text="🎤 开始录音",
            font=("Arial", 14),
            width=20,
            height=3,
            bg="#4CAF50",
            fg="white",
            command=self.toggle_recording
        )
        self.record_btn.pack(pady=20)

        self.separator = tk.Frame(self.root, height=2, bg="gray")
        self.separator.pack(fill="x", padx=20, pady=10)

        self.dialog_frame = tk.LabelFrame(self.root, text="对话记录", font=("Arial", 12))
        self.dialog_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.dialog_text = scrolledtext.ScrolledText(self.dialog_frame, font=("Arial", 12))
        self.dialog_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.dialog_text.insert(tk.END, "===== 语音智能助手已启动 =====\n")
        self.dialog_text.insert(tk.END, f"📢 检测到 {len(self.devices)} 个麦克风设备\n")
        if self.selected_device:
            self.dialog_text.insert(tk.END, f"📌 当前选择: {self.selected_device['name']}\n")
        self.dialog_text.insert(tk.END, "\n⚠️ 使用方法：点击开始录音 → 说话 → 点击停止录音\n\n")
        self.dialog_text.config(state=tk.DISABLED)

    def on_device_selected(self, event):
        idx = self.device_combo.current()
        if idx >= 0 and idx < len(self.devices):
            selected = self.devices[idx]
            problematic_devices = {12, 13, 14, 15, 19}

            if selected['index'] in problematic_devices:
                messagebox.showwarning("警告", f"设备 {selected['index']} 可能存在驱动问题，建议选择其他设备")
                return

            self.selected_device = selected
            self.append_message("system", f"已选择设备: {self.selected_device['name']}")

    def append_message(self, role, content):
        self.dialog_text.config(state=tk.NORMAL)
        if role == "user":
            self.dialog_text.insert(tk.END, f"👤 你：{content}\n\n")
        elif role == "assistant":
            self.dialog_text.insert(tk.END, f"🤖 智能助手：{content}\n\n")
        elif role == "system":
            self.dialog_text.insert(tk.END, f"📢 {content}\n")
        elif role == "debug":
            self.dialog_text.insert(tk.END, f"🔍 [调试] {content}\n")
        self.dialog_text.see(tk.END)
        self.dialog_text.config(state=tk.DISABLED)

    def update_volume_indicator(self, volume):
        width = min(volume * 2, 200)
        self.volume_canvas.coords(self.volume_bar, 0, 0, width, 20)

        if volume < 0.05:
            self.volume_label.config(text="🔇 静音", fg="gray")
            self.volume_canvas.itemconfig(self.volume_bar, fill="#f44336")
        elif volume < 0.2:
            self.volume_label.config(text=f"🔈 音量: {int(volume*100)}%", fg="#FF9800")
            self.volume_canvas.itemconfig(self.volume_bar, fill="#FF9800")
        else:
            self.volume_label.config(text=f"🔊 音量: {int(volume*100)}%", fg="#4CAF50")
            self.volume_canvas.itemconfig(self.volume_bar, fill="#4CAF50")

    def start_recording(self):
        if not self.selected_device:
            messagebox.showerror("错误", "没有可用的麦克风设备")
            return

        try:
            self.audio_frames = []
            self.p = pyaudio.PyAudio()
            device_index = self.selected_device['index']

            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )

            self.is_recording = True
            self.audio_thread = threading.Thread(target=self.record_audio)
            self.audio_thread.start()

            self.status_label.config(text="状态：正在录音...", fg="#4CAF50")
            self.record_btn.config(text="⏹️ 停止录音", bg="#f44336")
            self.append_message("system", "🎤 麦克风已开启，请对着麦克风说话...")

        except Exception as e:
            error_msg = f"启动录音失败：{str(e)}"
            messagebox.showerror("错误", error_msg)
            self.append_message("system", error_msg)

    def record_audio(self):
        import struct
        while self.is_recording:
            try:
                audio_data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.audio_frames.append(audio_data)

                samples = struct.unpack(f"{len(audio_data)//2}h", audio_data)
                max_val = max(abs(s) for s in samples) if samples else 0
                volume = min(max_val / 32767.0, 1.0)

                self.root.after(0, lambda v=volume: self.update_volume_indicator(v))

            except Exception as e:
                print(f"录音错误: {e}")
                break

    def stop_recording(self):
        self.is_recording = False

        if self.audio_thread:
            self.audio_thread.join(timeout=2)

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        if self.p:
            self.p.terminate()

        self.status_label.config(text="状态：正在识别...", fg="#FF9800")
        self.record_btn.config(state=tk.DISABLED)
        self.update_volume_indicator(0)

        audio_data = b''.join(self.audio_frames)
        duration = len(audio_data) / (RATE * CHANNELS * 2)

        if duration < 0.5:
            self.append_message("system", "🔇 录音时间太短，请多说一点")
            self.reset_ui()
            return

        self.append_message("system", f"📊 录音完成，时长: {duration:.1f}秒")

        threading.Thread(target=self.process_audio, args=(audio_data,)).start()

    def process_audio(self, audio_data):
        try:
            self.append_message("system", "🔊 正在识别语音...")

            final_text = []

            class MyCallback(RecognitionCallback):
                def on_event(self, event):
                    try:
                        if isinstance(event, str):
                            import json
                            event_data = json.loads(event)
                        else:
                            event_data = event
                        if event_data.get('status_code') == 200:
                            sentence = event_data.get('output', {}).get('sentence', {})
                            text = sentence.get('text', '').strip()
                            sentence_end = sentence.get('sentence_end', False)
                            if text:
                                final_text.append(text)
                    except:
                        pass

            rec = Recognition(
                model='paraformer-realtime-v2',
                callback=MyCallback(),
                format='pcm',
                sample_rate=RATE
            )
            rec.start()

            for i in range(0, len(audio_data), CHUNK):
                chunk = audio_data[i:i+CHUNK]
                if chunk:
                    rec.send_audio_frame(chunk)
                    time.sleep(0.001)

            time.sleep(1)
            rec.stop()

            text = ''.join(final_text).strip()
            
            if not text:
                self.append_message("system", "🔇 未识别到语音内容")
                self.reset_ui()
                return

            self.append_message("user", text)

            self.append_message("system", "🤔 正在调用通义千问(qwen-turbo)...")

            resp = Generation.call(
                model="qwen-turbo",
                messages=[{"role":"user","content":text}]
            )

            if resp.status_code == 200:
                reply = resp.output.text
                self.append_message("assistant", reply)
            else:
                self.append_message("system", f"❌ AI调用失败: {resp.message}")

        except Exception as e:
            error_msg = f"处理音频失败: {str(e)}"
            self.append_message("system", error_msg)
            import traceback
            traceback.print_exc()

        self.reset_ui()

    def reset_ui(self):
        self.status_label.config(text="状态：等待开始", fg="gray")
        self.record_btn.config(text="🎤 开始录音", bg="#4CAF50", state=tk.NORMAL)

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def on_closing(self):
        self.is_recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=1)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceAgentApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()