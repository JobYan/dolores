# Dolores

一个基于面向对象设计的命令行智能助手，支持自然语言交互与 Shell 命令执行，提供流式输出和交互式对话体验。

## 功能特性

![Dolores in Action](./image/used.png)

### 核心功能
- ✅ **Shell 命令执行**（以 `!` 开头的命令）
- ✅ **流式响应输出**（实时显示 AI 回复）
- ✅ **交互模式 (REPL)**（支持多轮对话）
- ✅ **翻译模式**（支持管道输入）
- ✅ **跨平台兼容**（支持中文输入编辑和方向键）
- ✅ **智能对话**（基于 DeepSeek API）

### 界面定制
- 🎨 **颜色主题**（支持 ANSI 颜色代码）
- 😊 **表情符号**（可选的 emoji 前缀）
- 🎯 **灵活配置**（通过环境变量自定义）

### 架构特点
- 🏗️ **面向对象设计**（模块化、可扩展）
- 📝 **类型注解**（完整的类型提示）
- 📚 **详细文档**（每个类和方法都有 docstring）
- 🔧 **易于维护**（清晰的职责分离）

## 快速开始

### 环境要求

```bash
# 安装依赖
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件（参考 `.env.example`）并设置以下环境变量：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，设置您的 API 密钥
DOLORES_API_KEY="your-api-key-here"
DOLORES_MODEL_ID="deepseek-chat"
DOLORES_BASE_URL="https://api.deepseek.com"
DOLORES_ENABLE_EMOJI=true
DOLORES_ENABLE_COLOR=true
```

或者直接在终端中设置临时环境变量：

```bash
# Linux/Mac
export DOLORES_API_KEY="your-api-key"
export DOLORES_MODEL_ID="deepseek-chat"
export DOLORES_BASE_URL="https://api.deepseek.com"
export DOLORES_ENABLE_EMOJI=true
export DOLORES_ENABLE_COLOR=true

# Windows (PowerShell)
$env:DOLORES_API_KEY="your-api-key"
$env:DOLORES_MODEL_ID="deepseek-chat"
$env:DOLORES_BASE_URL="https://api.deepseek.com"
$env:DOLORES_ENABLE_EMOJI="true"
$env:DOLORES_ENABLE_COLOR="true"
```

### 配置说明

| 环境变量 | 说明 | 默认值 | 必需 |
|-----------|------|--------|------|
| `DOLORES_API_KEY` | OpenAI API 密钥 | - | ✅ |
| `DOLORES_MODEL_ID` | 使用的模型 ID | `deepseek-chat` | ❌ |
| `DOLORES_BASE_URL` | API 基础 URL | `https://api.deepseek.com` | ❌ |
| `DOLORES_ENABLE_EMOJI` | 是否启用表情符号 | `true` | ❌ |
| `DOLORES_ENABLE_COLOR` | 是否启用颜色 | `true` | ❌ |

## 使用方法

### 基本命令

```bash
# 交互模式
python3 dolores.py

# 单次查询
python3 dolores.py "如何查看磁盘使用情况？"

# 翻译模式
python3 dolores.py -t "Hello World"

# 首次对话后进入交互模式
python3 dolores.py -rt "Hello World"

# 自定义系统提示词
python3 dolores.py -p "你是一个专业的程序员助手" "帮我写一个 Python 函数"

# 打印输入文本
echo "测试文本" | python3 dolores.py -P
```

### 交互模式功能

#### 1. 自然语言对话
```
🧐 Q: 如何查找大文件？
🤖 A: 可以使用 find 命令：
find /path -type f -size +500M
```

#### 2. 执行 Shell 命令
```
🧐 Q: !ls -l
🤖 A: [显示命令输出]
```

#### 3. 快捷操作
- `clear`：清空对话历史并清屏
- `exit` / `quit`：退出程序
- `Ctrl+C`：中断当前操作

#### 4. 管道输入
```bash
# 翻译 gcc --help 输出
gcc --help | python3 dolores.py --translate

# 解释命令输出
gcc --help | python3 dolores.py "gcc 应该如何使用"

# 批量处理
cat file1.txt file2.txt | python3 dolores.py -r
```

## 代码架构

项目采用面向对象设计，主要包含以下类：

### 核心类

- **[Config](dolores.py#L22-L70)**：配置管理类，使用 `@dataclass` 管理应用配置
- **[Formatter](dolores.py#L73-L166)**：格式化处理类，负责颜色和表情符号
- **[LLMClient](dolores.py#L169-L201)**：LLM 客户端类，封装 OpenAI API 交互
- **[CommandExecutor](dolores.py#L204-L247)**：命令执行类，处理 Shell 命令
- **[InputHandler](dolores.py#L250-L313)**：输入处理类，处理用户输入和管道
- **[DoloresApp](dolores.py#L316-L418)**：主应用类，协调所有功能模块

### 设计优势

- **模块化**：每个类都有明确的职责
- **可扩展**：易于添加新功能或修改现有功能
- **可测试**：独立的类便于单元测试
- **类型安全**：完整的类型注解提高代码质量
- **文档完善**：详细的 docstring 便于理解和维护

## 开发计划

- [ ] 添加对话历史持久化
- [ ] 支持多模型切换
- [ ] 添加插件系统
- [ ] 支持自定义主题
- [ ] 添加单元测试
- [ ] 性能优化和缓存

## 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供 AI 模型
- [OpenAI](https://openai.com/) - API 接口标准
- [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/) - 命令行界面库

## 许可证

MIT License