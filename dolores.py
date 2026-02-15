#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from typing import Optional, List, Dict
from dataclasses import dataclass

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import ANSI
from openai import OpenAI

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
            raise ValueError("API密钥未设置，请设置环境变量 DOLORES_API_KEY 或在 .env 文件中配置")

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
        - 以 "!" 开头: 执行 shell 命令
        - 其他: 发送给 LLM 进行处理
        
        Args:
            user_input: 用户输入的内容
        """
        if user_input.strip().lower() == "clear":
            self.formatter.clear_screen()
            self.reset_conversation()
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

    def _handle_llm_query(self, user_input: str) -> None:
        """
        处理 LLM 查询
        
        Args:
            user_input: 用户的问题或对话内容
        """
        self.messages.append({"role": "user", "content": user_input})
        self.formatter.print_colored(self.formatter.get_assistant_prefix(), end="")
        assistant_response = self.llm_client.query(self.messages)

        if assistant_response:
            self.messages.append({"role": "assistant", "content": assistant_response})
        else:
            sys.stderr.write("获取响应失败，请重试\n")
        print()

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
        if initial_input:
            self.messages.append({"role": "user", "content": initial_input})
            self.formatter.print_colored(self.formatter.get_user_prefix() + initial_input)
            self.formatter.print_colored(self.formatter.get_assistant_prefix(), end="")
            assistant_response = self.llm_client.query(self.messages)
            if assistant_response:
                self.messages.append({"role": "assistant", "content": assistant_response})

        if not sys.stdin.isatty():
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
            if args.repl:
                self.interactive_mode(in_text)
            else:
                self.single_query(in_text)
        else:
            self.interactive_mode()


def main():
    """主函数"""
    config = Config.from_env()
    app = DoloresApp(config)

    parser = argparse.ArgumentParser(description="AI命令行助手")
    parser.add_argument("text", nargs="*", help="输入问题（直接模式）")
    parser.add_argument("-r", "--repl", action="store_true", help="进入交互模式")
    parser.add_argument("-t", "--translate", action="store_true", help="翻译")
    parser.add_argument("-P", "--print-text", action="store_true", help="打印完整的输入文本")
    parser.add_argument("-p", "--prompt", type=str, help="输入提示词")
    args = parser.parse_args()

    app.run(args)


if __name__ == "__main__":
    main()