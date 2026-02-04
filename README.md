# dolores

一个命令行智能助手，支持自然语言交互与Shell命令执行，提供流式输出和交互式对话体验。(项目仍不完善，26年2月份会持续更新)

## 功能

![image-20250403170408109](./image/used.png)

✅ **Shell命令执行**（以`!`开头的命令）

✅ **流式响应输出**

✅ **交互模式(REPL)**

✅ **翻译模式**（支持管道输入）

✅ **跨平台兼容**（支持中文输入编辑）

✅ **智能对话**

## 快速开始

### 环境要求
```bash
pip install -r requirements.txt
```

### 配置

创建一个 `.env` 文件（参考 `.env.example`）并设置以下环境变量：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，设置您的API密钥
DOLORES_API_KEY="your-api-key"
DOLORES_MODEL_ID="deepseek-chat"
DOLORES_BASE_URL="https://api.deepseek.com"
```

或者直接在终端中设置临时环境变量：

```bash
# Linux/Mac
export DOLORES_API_KEY="your-api-key"
export DOLORES_MODEL_ID="deepseek-chat"
export DOLORES_BASE_URL="https://api.deepseek.com"

# Windows (PowerShell)
$env:DOLORES_API_KEY="your-api-key"
$env:DOLORES_MODEL_ID="deepseek-chat"
$env:DOLORES_BASE_URL="https://api.deepseek.com"
```

### 基本使用

```bash
# 交互模式
./dolores.py

# 单次查询
./dolores.py "如何查看磁盘使用情况？"

# 翻译模式
./dolores.py -t "Hello World"

# 首段对话后进入交互模式
./dolores.py -rt "Hello World"
```

## 交互模式功能
1. **自然语言对话**：

   ```
   Q: 如何查找大文件？
   A: 可以使用find命令：find /path -type f -size +500M...
   ```

2. **执行Shell命令**：

   ```
   Q: !ls -l
   A: [显示命令输出]
   ```

3. **快捷操作**：
   - `clear`：清空对话历史
   - `exit/quit`：退出程序
   - `Ctrl+C`：中断当前操作

4. **管道：**
```bash
# 翻译gcc --help输出
gcc --help | ./dolores.py --translate

# 解释说明
gcc --help | ./dolores.py "gcc应该如何使用"
```

## 致谢

- DeepSeek-R1
- 火山引擎
- OpenAI
