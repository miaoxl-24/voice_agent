# 🎤 语音智能助手

一个基于阿里云语音服务和通义千问的语音智能助手应用。

## ✨ 功能特性

- 🎙️ **语音识别**：使用阿里云语音识别服务（ASR）将语音转换为文字
- 🤖 **智能对话**：调用通义千问大语言模型进行智能对话
- 🎨 **图形界面**：友好的Tkinter图形用户界面
- 🔊 **实时音量指示**：录音时实时显示麦克风音量
- 📝 **对话记录**：保存完整的对话历史

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 阿里云DashScope API Key

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API Key

在 `voice_agent.py` 文件中设置你的阿里云API Key：

```python
API_KEY = "your-api-key-here"
```

### 运行程序

```bash
python voice_agent.py
```

## 📖 使用说明

1. **选择麦克风设备**：从下拉菜单中选择可用的麦克风设备
2. **开始录音**：点击绿色的"开始录音"按钮
3. **说话**：对着麦克风说出你的问题
4. **停止录音**：点击红色的"停止录音"按钮
5. **查看结果**：语音会被识别为文字，并显示AI的回复

## 🛠️ 技术栈

- **语音识别**：阿里云DashScope ASR（paraformer-realtime-v2）
- **大语言模型**：通义千问（qwen-turbo）
- **音频处理**：PyAudio
- **图形界面**：Tkinter

## 📁 项目结构

```
asr/
├── voice_agent.py    # 主程序文件
├── requirements.txt  # 依赖列表
├── .gitignore        # Git忽略配置
└── README.md         # 项目说明文档
```

## 🔑 API Key获取

1. 访问 [阿里云DashScope控制台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 创建API Key
4. 将API Key填入 `voice_agent.py` 文件中

## ⚠️ 注意事项

- 确保麦克风设备正常工作
- 确保网络连接正常
- API Key需要有足够的余额或配额

## 📄 许可证

MIT License
