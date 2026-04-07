"""
飞书文档与消息推送模块
使用 lark-cli 进行飞书文档创建和消息发送
"""
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# 飞书用户 ID（接收推送的用户）
FEISHU_USER_ID = "ou_603bc50e2bf3c6f09f4aec8c89f655b1"

# 代理环境变量
PROXY_ENV = {
    "HTTP_PROXY": "http://127.0.0.1:7897",
    "HTTPS_PROXY": "http://127.0.0.1:7897",
    "http_proxy": "http://127.0.0.1:7897",
    "https_proxy": "http://127.0.0.1:7897",
}


def run_lark_cli(cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
    """运行 lark-cli 命令"""
    full_env = os.environ.copy()
    full_env.update(PROXY_ENV)
    full_env["PATH"] = "/home/linuxbrew/.linuxbrew/bin:" + full_env["PATH"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=full_env
    )
    return result


# ============================================================================
# 文档操作
# ============================================================================

def create_doc(title: str, markdown_content: str, folder_token: str = None) -> dict:
    """
    创建飞书云文档

    Args:
        title: 文档标题
        markdown_content: Markdown 格式内容
        folder_token: 可选，父文件夹 token

    Returns:
        {"doc_id": "...", "doc_url": "...", "ok": true/false}
    """
    cmd = [
        "npx", "lark-cli", "docs", "+create",
        "--title", title,
        "--markdown", markdown_content,
        "--as", "bot"
    ]

    if folder_token:
        cmd.extend(["--folder-token", folder_token])

    result = run_lark_cli(cmd)

    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            return {
                "doc_id": data["data"].get("doc_id", ""),
                "doc_url": data["data"].get("doc_url", ""),
                "ok": True
            }
    except:
        pass

    return {"doc_id": "", "doc_url": "", "ok": False, "error": result.stderr}


def create_wiki_node(title: str, markdown_content: str, parent_node_token: str = None, space_id: str = "my_library") -> dict:
    """
    在个人知识库创建 Wiki 文档

    Args:
        title: 文档标题
        markdown_content: Markdown 内容
        parent_node_token: 父节点 token（可选）
        space_id: 知识空间 ID，"my_library" 表示个人知识库

    Returns:
        {"doc_id": "...", "doc_url": "...", "ok": true/false}
    """
    cmd = [
        "npx", "lark-cli", "docs", "+create",
        "--title", title,
        "--markdown", markdown_content,
        "--as", "bot",
        "--wiki-space", space_id
    ]

    if parent_node_token:
        cmd.extend(["--wiki-node", parent_node_token])

    result = run_lark_cli(cmd)

    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            return {
                "doc_id": data["data"].get("doc_id", ""),
                "doc_url": data["data"].get("doc_url", ""),
                "ok": True
            }
    except:
        pass

    return {"doc_id": "", "doc_url": "", "ok": False, "error": result.stderr}


# ============================================================================
# 消息操作
# ============================================================================

def send_text_message(receive_id: str, receive_id_type: str, text: str) -> dict:
    """
    发送文本消息

    Args:
        receive_id: 接收者 ID（open_id 或 chat_id）
        receive_id_type: "open_id" 或 "chat_id"
        text: 消息文本

    Returns:
        {"message_id": "...", "chat_id": "...", "ok": true/false}
    """
    # lark-cli 使用 --user-id 或 --chat-id
    cmd = [
        "npx", "lark-cli", "im", "+messages-send",
        "--as", "bot",
        "--text", text
    ]

    if receive_id_type == "open_id":
        cmd.extend(["--user-id", receive_id])
    else:
        cmd.extend(["--chat-id", receive_id])

    result = run_lark_cli(cmd)

    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            return {
                "message_id": data["data"].get("message_id", ""),
                "chat_id": data["data"].get("chat_id", ""),
                "ok": True
            }
    except:
        pass

    return {"message_id": "", "chat_id": "", "ok": False, "error": result.stderr}


def send_markdown_message(receive_id: str, receive_id_type: str, markdown: str) -> dict:
    """
    发送 Markdown 格式消息

    Args:
        receive_id: 接收者 ID
        receive_id_type: "open_id" 或 "chat_id"
        markdown: Markdown 格式消息

    Returns:
        {"message_id": "...", "chat_id": "...", "ok": true/false}
    """
    cmd = [
        "npx", "lark-cli", "im", "+messages-send",
        "--as", "bot",
        "--markdown", markdown
    ]

    if receive_id_type == "open_id":
        cmd.extend(["--user-id", receive_id])
    else:
        cmd.extend(["--chat-id", receive_id])

    result = run_lark_cli(cmd)

    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            return {
                "message_id": data["data"].get("message_id", ""),
                "chat_id": data["data"].get("chat_id", ""),
                "ok": True
            }
    except:
        pass

    return {"message_id": "", "chat_id": "", "ok": False, "error": result.stderr}


# ============================================================================
# 每日简报
# ============================================================================

def send_daily_report_card(date_str: str, paper_count: int, high_impact: int,
                           doc_url: str = None, user_id: str = None) -> dict:
    """
    发送每日科研简报卡片

    Args:
        date_str: 日期字符串
        paper_count: 论文数量
        high_impact: 高影响力论文数量
        doc_url: 完整报告文档链接
        user_id: 接收者 open_id（默认使用 FEISHU_USER_ID）

    Returns:
        {"message_id": "...", "ok": true/false}
    """
    if user_id is None:
        user_id = FEISHU_USER_ID

    message = f"""📚 **每日科研简报 {date_str}**

**研究方向**: 金刚石NV色心 · 量子传感

---

**今日新论文**: {paper_count} 篇

**高影响力**: {high_impact} 篇 🔥
"""

    if doc_url:
        message += f"""
📖 [点击查看完整报告]({doc_url})
"""

    message += """
---
*由 Semantic Scholar Research Automation 生成*"""

    return send_markdown_message(user_id, "open_id", message)


# ============================================================================
# 便捷函数
# ============================================================================

def get_user_open_id(user_email: str = None, user_name: str = None) -> str:
    """
    获取用户 open_id

    Args:
        user_email: 用户邮箱
        user_name: 用户名（用于搜索）

    Returns:
        open_id 字符串
    """
    if user_name:
        cmd = [
            "npx", "lark-cli", "contact", "+search-user",
            "--query", user_name,
            "--format", "json"
        ]
        result = run_lark_cli(cmd)

        try:
            data = json.loads(result.stdout)
            if data.get("ok") and data.get("data", {}).get("users"):
                return data["data"]["users"][0].get("open_id", "")
        except:
            pass

    raise Exception(f"未找到用户: {user_name or user_email}")
