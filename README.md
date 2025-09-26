# 视频文件智能重命名工具

一个基于AI的视频文件批量重命名工具，专门用于处理乱码文件名（长串随机数字字母）的视频文件。

## 功能特点

- 🔍 **智能识别**：自动识别乱码文件名（长串十六进制字符）
- 🎬 **视频截图**：从视频中提取关键帧进行分析
- 🤖 **AI驱动**：使用Gemini 2.5 Flash分析视频内容
- 🏷️ **智能命名**：基于内容生成有意义的中文文件名
- ⚡ **异步处理**：支持批量并发处理，提高效率
- 🛡️ **安全可靠**：文件名冲突检测，详细操作日志

## 安装说明

### 1. 创建Conda环境
```bash
conda env create -f environment.yml
conda activate video_renamer
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法
```bash
python scripts/run_renamer.py /path/to/video/files
```

### 高级选项
```bash
python scripts/run_renamer.py --help
```

## 配置文件

在项目根目录创建 `.env` 文件：

```
API_URL=http://localhost:3001/proxy/free
MAX_RETRIES=3
MAX_WORKERS=2
SCREENSHOT_COUNT=3
```

## 项目结构

```
video_renamer_project/
├── src/
│   ├── core/              # 核心功能模块
│   ├── utils/             # 工具函数
│   └── config/            # 配置管理
├── tests/                 # 单元测试
├── scripts/               # 执行脚本
└── README.md             # 说明文档
```

## 开发说明

### 运行测试
```bash
pytest tests/
```

### 代码格式化
```bash
black src/
```

### 类型检查
```bash
mypy src/
```

## 注意事项

- 仅处理乱码文件名，其他文件保持不变
- 需要网络连接调用AI API
- 建议先在小批量文件上测试
- 处理前请确保重要文件已备份

## 许可证

MIT License