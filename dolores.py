#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
import tempfile
import asyncio
import threading
import select
import re
from typing import Optional, List, Dict
from dataclasses import dataclass

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import ANSI
from openai import OpenAI

# 尝试导入 pygame 用于跨平台音频播放
try:
    import os
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    sys.stderr.write("Warning: pygame not installed. TTS functionality will be disabled.\n")
    sys.stderr.write("Install it with: pip install pygame\n")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    """配置管理类
    
    使用 dataclass 管理应用配置，支持从环境变量加载配置。
    
    Attributes:
        api_key: OpenAI API 密钥
        model_id: 使用的模型 ID
        base_url: API 基础 URL
        enable_emoji: 是否启用表情符号
        enable_color: 是否启用颜色
        system_prompt: 系统提示词
    """
    api_key: str
    model_id: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    enable_emoji: bool = True
    enable_color: bool = True
    system_prompt: str = "你是一个能干的助手。"

    @classmethod
    def from_env(cls) -> "Config":
        """
        从环境变量创建配置
        
        支持的环境变量：
        - DOLORES_API_KEY: API 密钥（必需）
        - DOLORES_MODEL_ID: 模型 ID（默认：deepseek-chat）
        - DOLORES_BASE_URL: API 基础 URL（默认：https://api.deepseek.com）
        - DOLORES_ENABLE_EMOJI: 是否启用表情符号（默认：true）
        - DOLORES_ENABLE_COLOR: 是否启用颜色（默认：true）
        
        Returns:
            配置对象
            
        Raises:
            ValueError: 如果未设置 API 密钥
        """
        api_key = os.getenv("DOLORES_API_KEY")
        if not api_key:
            raise ValueError("API 密钥未设置，请设置环境变量 DOLORES_API_KEY 或在 .env 文件中配置")

        return cls(
            api_key=api_key,
            model_id=os.getenv("DOLORES_MODEL_ID", "deepseek-chat"),
            base_url=os.getenv("DOLORES_BASE_URL", "https://api.deepseek.com"),
            enable_emoji=os.getenv("DOLORES_ENABLE_EMOJI", "true").lower() == "true",
            enable_color=os.getenv("DOLORES_ENABLE_COLOR", "true").lower() == "true",
        )


class Formatter:
    """格式化和颜色处理类
    
    负责处理终端输出格式化，包括：
    - ANSI 颜色代码
    - 表情符号
    - 文本前缀
    - 清屏操作
    """

    class AnsiColors:
        """ANSI 颜色代码常量"""
        BLUE = '\033[34m'
        GREEN = '\033[32m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

    def __init__(self, config: Config):
        """
        初始化格式化器
        
        Args:
            config: 配置对象
        """
        self.config = config

    def get_user_prefix(self) -> str:
        """
        获取用户输入前缀
        
        根据配置返回不同风格的前缀：
        - 启用表情符号：🧐 Q: 
        - 启用颜色：[Q] （蓝色粗体）
        - 同时启用：🧐 Q: （蓝色粗体）
        - 都不启用：[Q]
        
        Returns:
            用户输入前缀字符串
        """
        emoji = "🧐 Q: " if self.config.enable_emoji else "[Q] "
        
        if self.config.enable_color:
            return self.AnsiColors.BOLD + self.AnsiColors.BLUE + emoji + self.AnsiColors.RESET
        else:
            return emoji

    def get_assistant_prefix(self) -> str:
        """
        获取助手输出前缀
        
        根据配置返回不同风格的前缀：
        - 启用表情符号：🤖 A: 
        - 启用颜色：[A] （绿色粗体）
        - 同时启用：🤖 A: （绿色粗体）
        - 都不启用：[A]
        
        Returns:
            助手输出前缀字符串
        """
        emoji = "🤖 A: " if self.config.enable_emoji else "[A] "
        
        if self.config.enable_color:
            return self.AnsiColors.BOLD + self.AnsiColors.GREEN + emoji + self.AnsiColors.RESET
        else:
            return emoji

    def print_colored(self, text: str, end: str = "\n") -> None:
        """
        打印带颜色的文本
        
        Args:
            text: 要打印的文本
            end: 行尾字符（默认：换行符）
        """
        print(text, end=end, flush=True)

    def clear_screen(self) -> None:
        """清屏，使用 ANSI 转义序列"""
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


class LLMClient:
    """LLM 客户端类，负责与 OpenAI API 进行交互"""

    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def query(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        执行 LLM 查询（流式输出）
        
        Args:
            messages: 消息列表，包含对话历史
            
        Returns:
            LLM 的响应内容，如果发生错误则返回 None
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                stream=True
            )
            response = []
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    sys.stdout.write(content)
                    sys.stdout.flush()
                    response.append(content)
            print()
            return "".join(response)
        except Exception as e:
            sys.stderr.write(f"\nError: {str(e)}\n")
            return None


class CommandExecutor:
    """命令执行类，负责执行 shell 命令并处理输出"""

    def __init__(self, formatter: Formatter):
        self.formatter = formatter

    def execute(self, command: str) -> str:
        """
        执行 shell 命令并实时流式输出结果
        
        Args:
            command: 要执行的 shell 命令
            
        Returns:
            命令的输出内容
        """
        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            output = []
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    output.append(line)
            return "".join(output)
        except Exception as e:
            error_msg = f"\nError executing command: {str(e)}"
            sys.stdout.write(error_msg + "\n")
            return error_msg


class InputHandler:
    """用户输入处理类，负责处理用户输入和管道输入"""

    def __init__(self, formatter: Formatter):
        self.formatter = formatter

    def get_input(self, prompt: str) -> str:
        """
        获取用户输入（支持中文编辑/方向键）
        
        Args:
            prompt: 输入提示符
            
        Returns:
            用户输入的内容
        """
        if not sys.stdin.isatty():
            return input(prompt).strip()

        bindings = KeyBindings()

        @bindings.add("c-c")
        def _(event):
            event.app.exit(exception=KeyboardInterrupt)

        session = PromptSession(
            key_bindings=bindings,
            vi_mode=False,
            multiline=False,
            mouse_support=False
        )

        return session.prompt(
            message=ANSI(prompt),
            wrap_lines=True,
            enable_history_search=False
        ).strip()

    def read_piped_input(self) -> Optional[str]:
        """
        读取管道输入
        
        Returns:
            管道输入的内容，如果没有管道输入则返回 None
        """
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            if content:
                return content.strip()
        return None


class TTSClient:
    """文本转语音客户端类，使用 Microsoft Edge TTS 和 pygame 播放"""

    def __init__(self):
        """初始化 TTS 客户端"""
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.edge_available = True
        except ImportError:
            self.edge_available = False
            sys.stderr.write("Warning: edge-tts not installed. TTS functionality will be disabled.\n")
            sys.stderr.write("Install it with: pip install edge-tts\n")
        
        self.available = self.edge_available and PYGAME_AVAILABLE
        if not PYGAME_AVAILABLE:
            sys.stderr.write("Warning: pygame not available. TTS playback will not work.\n")
        
        # 缓存机制：记录上次播放的文本和对应的音频文件
        self.last_text = None
        self.last_audio_file = None

    def speak(self, text: str) -> bool:
        """
        将文本转换为语音并播放，支持按键中断
        
        如果文本与上次相同，则复用缓存的 MP3 文件，避免重新生成。
        
        Args:
            text: 要朗读的文本
            
        Returns:
            是否成功播放（如果被中断则返回 False）
        """
        if not self.available:
            sys.stderr.write("TTS is not available. Please install edge-tts and pygame.\n")
            return False

        if not text or not text.strip():
            return False

        try:
            # 检查是否可以使用缓存的音频文件
            if (self.last_text == text and
                self.last_audio_file is not None and
                os.path.exists(self.last_audio_file)):
                # 文本相同且缓存文件存在，直接使用缓存
                temp_path = self.last_audio_file
            else:
                # 文本不同或缓存文件不存在，生成新的音频文件
                # 如果存在旧的缓存文件，先删除
                if self.last_audio_file and os.path.exists(self.last_audio_file):
                    try:
                        os.unlink(self.last_audio_file)
                    except Exception:
                        pass
                
                communicate = self.edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                    temp_path = temp_file.name
                
                asyncio.run(communicate.save(temp_path))
                
                # 更新缓存
                self.last_text = text
                self.last_audio_file = temp_path
            
            # 使用 pygame 统一播放，支持跨平台
            return self._play_with_pygame(temp_path)

        except Exception as e:
            sys.stderr.write(f"TTS Error: {str(e)}\n")
            return False

    def _play_with_pygame(self, audio_file: str) -> bool:
        """
        使用 pygame 播放音频文件，支持按键中断
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            是否成功播放完成（如果被中断则返回 False）
        """
        if not PYGAME_AVAILABLE:
            sys.stderr.write("pygame is not available.\n")
            return False
            
        self.interrupted = False
        
        def play_audio():
            try:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            except Exception as e:
                sys.stderr.write(f"Playback error: {str(e)}\n")
        
        play_thread = threading.Thread(target=play_audio)
        play_thread.daemon = False
        play_thread.start()
        
        print("\n按任意键停止朗读...", end="", flush=True)
        
        if sys.stdin.isatty():
            try:
                if sys.platform == "win32":
                    import msvcrt
                    while play_thread.is_alive():
                        if msvcrt.kbhit():
                            self.interrupted = True
                            print("\n朗读已停止")
                            pygame.mixer.music.stop()
                            break
                        play_thread.join(timeout=0.1)
                    # 播放完成后，清除提示信息并换行
                    if not self.interrupted:
                        print("\r" + " " * 30 + "\r", end="", flush=True)
                        print()
                else:
                    import termios
                    import tty
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setcbreak(sys.stdin.fileno())
                        while play_thread.is_alive():
                            if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                                sys.stdin.read(1)
                                self.interrupted = True
                                print("\n朗读已停止")
                                pygame.mixer.music.stop()
                                break
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    # 播放完成后，清除提示信息
                    if not self.interrupted:
                        print("\r" + " " * 30 + "\r", end="", flush=True)
            except (ImportError, OSError, KeyboardInterrupt):
                pass
        
        play_thread.join(timeout=5)
        pygame.mixer.music.unload()
        
        # 只有当音频文件不是缓存文件时才删除
        # 缓存文件会在下次生成新音频时删除，或者在程序退出时由系统清理
        if audio_file != self.last_audio_file and os.path.exists(audio_file):
            os.unlink(audio_file)
        
        return not self.interrupted


class DoloresApp:
    """主应用类，整合所有功能模块
    
    该类负责协调各个功能模块，包括：
    - 配置管理
    - 格式化和颜色处理
    - LLM 客户端交互
    - 命令执行
    - 用户输入处理
    """

    def __init__(self, config: Config):
        """
        初始化应用
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.formatter = Formatter(config)
        self.llm_client = LLMClient(config)
        self.command_executor = CommandExecutor(self.formatter)
        self.input_handler = InputHandler(self.formatter)
        self.tts_client = TTSClient()
        self.messages = [{"role": "system", "content": config.system_prompt}]

    def reset_conversation(self) -> None:
        """重置对话历史，保留系统提示词"""
        self.messages = [{"role": "system", "content": self.config.system_prompt}]
        self.formatter.print_colored("对话历史已重置")

    def process_user_input(self, user_input: str) -> None:
        """
        处理用户输入，根据输入类型分发到不同的处理方法
        
        支持的输入类型：
        - "clear": 清屏并重置对话历史
        - "/speak": 朗读上一次的回复
        - 以 "!" 开头：执行 shell 命令
        - 其他：发送给 LLM 进行处理
        
        Args:
            user_input: 用户输入的内容
        """
        if user_input.strip().lower() == "clear":
            self.formatter.clear_screen()
            self.reset_conversation()
            return

        if user_input.strip().lower() == "/speak":
            self._handle_speak()
            return

        if not user_input:
            print()
            return

        if user_input.startswith("!"):
            self._handle_command(user_input)
        else:
            self._handle_llm_query(user_input)

    def _handle_command(self, user_input: str) -> None:
        """
        处理 shell 命令
        
        Args:
            user_input: 以 ! 开头的命令字符串
        """
        command = user_input[1:].strip()
        if not command:
            return

        self.messages.append({"role": "user", "content": user_input})
        self.formatter.print_colored(self.formatter.get_assistant_prefix(), end="")
        cmd_output = self.command_executor.execute(command)
        print()

        self.messages.append({
            "role": "system",
            "content": f"命令执行结果:\n{cmd_output}",
        })

    def _find_file_recursive(self, filename: str) -> tuple:
        """
        递归查找文件，处理同名文件的情况
        
        Args:
            filename: 文件名或相对路径
            
        Returns:
            (文件路径, 匹配数量) 的元组
        """
        # 首先尝试直接路径（支持用户指定相对路径如 subdir/file.txt）
        direct_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(direct_path) and os.path.isfile(direct_path):
            # 如果用户指定了路径分隔符（如 subdir/file.txt），直接返回
            if os.path.sep in filename or '/' in filename:
                return (direct_path, 1)
        
        # 递归查找所有匹配的文件（只在文件名为纯文件名时）
        matches = []
        if os.path.sep not in filename and '/' not in filename:
            for root, dirs, files in os.walk(os.getcwd()):
                # 排除常见的非代码目录
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
                
                if filename in files:
                    matches.append(os.path.join(root, filename))
        
        # 如果直接路径存在且没有其他匹配，返回直接路径
        if os.path.exists(direct_path) and os.path.isfile(direct_path):
            if len(matches) <= 1:
                return (direct_path, 1)
            else:
                # 直接路径也是匹配之一，加入列表
                if direct_path not in matches:
                    matches.append(direct_path)
        
        if len(matches) == 1:
            return (matches[0], 1)
        elif len(matches) > 1:
            return (matches, len(matches))  # 返回所有匹配路径
        else:
            return (None, 0)

    def _process_file_references(self, user_input: str) -> str:
        """
        处理 @file(xxx) 引用，将文件内容插入到输入中
        
        Args:
            user_input: 用户输入的内容
            
        Returns:
            处理后的内容，包含文件内容
        """
        file_pattern = r'@file\(([^)]+)\)'
        
        def replace_file_reference(match):
            filename = match.group(1).strip()
            
            # 查找文件
            result, count = self._find_file_recursive(filename)
            
            if count == 0:
                return f"[文件不存在: {filename}]"
            elif count > 1:
                # 发现多个同名文件，列出所有选项
                matches_list = "\n".join([f"  {i+1}. {path}" for i, path in enumerate(result)])
                return f"[发现多个同名文件 '{filename}'，请使用完整相对路径指定：\n{matches_list}\n例如: @file(subdir/{filename})]"
            
            file_path = result
            
            # 检查是否是文件（不是目录）
            if not os.path.isfile(file_path):
                return f"[不是文件: {filename}]"
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 显示找到的文件的相对路径
                rel_path = os.path.relpath(file_path, os.getcwd())
                return f"\n\n--- 文件 {rel_path} 内容 ---\n{content}\n--- 文件 {rel_path} 结束 ---\n\n"
            except UnicodeDecodeError:
                return f"[无法读取文件（可能是二进制文件）: {filename}]"
            except Exception as e:
                return f"[读取文件错误 {filename}: {str(e)}]"
        
        return re.sub(file_pattern, replace_file_reference, user_input)

    def _handle_llm_query(self, user_input: str) -> None:
        """
        处理 LLM 查询
        
        Args:
            user_input: 用户的问题或对话内容
        """
        # 处理 @file(xxx) 引用
        processed_input = self._process_file_references(user_input)
        
        self.messages.append({"role": "user", "content": processed_input})
        self.formatter.print_colored(self.formatter.get_assistant_prefix(), end="")
        assistant_response = self.llm_client.query(self.messages)

        if assistant_response:
            self.messages.append({"role": "assistant", "content": assistant_response})
        else:
            sys.stderr.write("获取响应失败，请重试\n")
        print()

    def _handle_speak(self) -> None:
        """朗读上一次的助手回复"""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                response_text = msg["content"]
                if response_text:
                    self.formatter.print_colored(f"🔊 正在朗读...")
                    self.tts_client.speak(response_text)
                return

    def single_query(self, question: str) -> None:
        """
        单次查询模式
        
        Args:
            question: 要查询的问题
        """
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": question},
        ]
        self.formatter.print_colored(self.formatter.get_user_prefix() + question)
        self.formatter.print_colored(self.formatter.get_assistant_prefix(), end="")

        assistant_response = self.llm_client.query(messages)
        if not assistant_response:
            sys.exit(1)

    def interactive_mode(self, initial_input: Optional[str] = None) -> None:
        """
        交互式对话模式
        
        Args:
            initial_input: 初始输入，如果提供则先处理该输入
        """
        is_tty = sys.stdin.isatty()
        
        if initial_input:
            self.messages.append({"role": "user", "content": initial_input})
            self.formatter.print_colored(self.formatter.get_user_prefix() + initial_input)
            self.formatter.print_colored(self.formatter.get_assistant_prefix(), end="")
            assistant_response = self.llm_client.query(self.messages)
            if assistant_response:
                self.messages.append({"role": "assistant", "content": assistant_response})

        if not is_tty:
            return

        print("进入对话模式（输入 exit 退出）")
        while True:
            try:
                user_input = self.input_handler.get_input(self.formatter.get_user_prefix())

                if user_input.lower() in ["exit", "quit"]:
                    break

                self.process_user_input(user_input)

            except KeyboardInterrupt:
                print("\n再见！")
                break
            except EOFError:
                print("\n再见！")
                break

    def run(self, args: argparse.Namespace) -> None:
        """
        运行应用
        
        Args:
            args: 命令行参数
        """
        in_text = None
        in_text_list = []
        piped_input = self.input_handler.read_piped_input()

        if piped_input:
            in_text_list.append(piped_input)
        if args.text:
            in_text_list.append("".join(args.text))
        if args.translate and in_text_list:
            in_text_list.append("\n请将以上文本翻译成中文\n")

        if in_text_list:
            in_text = "".join(in_text_list)
        if args.print_text and in_text:
            sys.stdout.write(in_text)

        if args.prompt:
            self.config.system_prompt = args.prompt
            self.messages[0]["content"] = args.prompt

        if in_text:
            if args.repl and not sys.stdin.isatty():
                lines = [line.strip() for line in in_text.split('\n') if line.strip()]
                if lines:
                    first_line = lines[0]
                    commands = lines[1:]
                    
                    self.interactive_mode(first_line)
                    
                    for cmd in commands:
                        self.process_user_input(cmd)
            elif args.repl:
                self.interactive_mode(in_text)
            else:
                self.single_query(in_text)
        else:
            self.interactive_mode()


def main():
    """主函数"""
    config = Config.from_env()
    app = DoloresApp(config)

    parser = argparse.ArgumentParser(description="AI 命令行助手")
    parser.add_argument("text", nargs="*", help="输入问题（直接模式）")
    parser.add_argument("-r", "--repl", action="store_true", help="进入交互模式")
    parser.add_argument("-t", "--translate", action="store_true", help="翻译")
    parser.add_argument("-P", "--print-text", action="store_true", help="打印完整的输入文本")
    parser.add_argument("-p", "--prompt", type=str, help="输入提示词")
    args = parser.parse_args()

    app.run(args)


if __name__ == "__main__":
    main()