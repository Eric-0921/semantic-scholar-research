"""
飞书文档与消息推送模块
支持：创建云文档、发送 IM 消息卡片
"""
import json
import time
import requests
from datetime import datetime
from typing import Optional, List

# 飞书应用配置（从环境变量或 config 读取）
# IMPORTANT: 不要硬编码 secrets，使用 .env 文件
from config import FEISHU_APP_ID, FEISHU_APP_SECRET

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 全局 token 缓存
_access_token = None
_token_expires_at = 0


def _get_access_token() -> str:
    """获取 app_access_token（带缓存）"""
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at - 60:
        return _access_token

    url = f"{FEISHU_API_BASE}/auth/v3/app_access_token/internal"
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    resp = requests.post(url, json=data, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise Exception(f"获取 access_token 失败: {result}")

    _access_token = result["app_access_token"]
    _token_expires_at = time.time() + result.get("expire", 7200)
    return _access_token


def _headers():
    """通用请求头"""
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json"
    }


# ============================================================================
# 文档操作
# ============================================================================

def create_doc(title: str, markdown_content: str, folder_token: str = None) -> dict:
    """
    从 Markdown 创建飞书云文档

    Args:
        title: 文档标题
        markdown_content: Markdown 格式内容
        folder_token: 可选，父文件夹 token

    Returns:
        {"doc_token": "...", "doc_url": "..."}
    """
    url = f"{FEISHU_API_BASE}/doc/v2/create"

    payload = {
        "title": title,
        "content": markdown_to_feishu_blocks(markdown_content)
    }

    if folder_token:
        payload["folder_token"] = folder_token

    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise Exception(f"创建文档失败: {result}")

    data = result.get("data", {})
    doc_token = data.get("doc_token", "")
    doc_url = f"https://feishu.cn/document/{doc_token}"

    return {"doc_token": doc_token, "doc_url": doc_url}


def create_wiki_node(title: str, markdown_content: str, parent_node_token: str = None, space_id: str = "my_library") -> dict:
    """
    在个人知识库创建 Wiki 文档

    Args:
        title: 文档标题
        markdown_content: Markdown 内容
        parent_node_token: 父节点 token（可选）
        space_id: 知识空间 ID，"my_library" 表示个人知识库

    Returns:
        {"node_token": "...", "node_url": "..."}
    """
    # 1. 先创建文档
    doc_result = create_doc(title, markdown_content)
    doc_token = doc_result["doc_token"]

    # 2. 创建 Wiki 节点
    url = f"{FEISHU_API_BASE}/wiki/v2/spaces/{space_id}/nodes"

    payload = {
        "obj_type": "doc",
        "node_type": "origin",
        "origin": {"token": doc_token, "type": "doc"},
        "parent_node_token": parent_node_token
    }

    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        # 如果创建 Wiki 节点失败，仍然返回文档信息
        return {"node_token": doc_token, "node_url": doc_result["doc_url"], "error": result.get("msg")}

    data = result.get("data", {})
    node_token = data.get("node_token", "")
    node_url = f"https://feishu.cn/wiki/{node_token}"

    return {"node_token": node_token, "node_url": node_url}


def update_doc(doc_token: str, markdown_content: str):
    """
    更新飞书文档内容

    Args:
        doc_token: 文档 token
        markdown_content: 新的 Markdown 内容
    """
    url = f"{FEISHU_API_BASE}/doc/v2/{doc_token}/raw_content"

    payload = {
        "content": markdown_content
    }

    resp = requests.put(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise Exception(f"更新文档失败: {result}")


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
        {"message_id": "...", "chat_id": "..."}
    """
    url = f"{FEISHU_API_BASE}/im/v1/messages?receive_id_type={receive_id_type}"

    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }

    resp = requests.post(url, headers=_headers(), json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise Exception(f"发送消息失败: {result}")

    data = result.get("data", {})
    return {
        "message_id": data.get("message_id", ""),
        "chat_id": data.get("chat_id", "")
    }


def send_interactive_card(receive_id: str, receive_id_type: str, card: dict) -> dict:
    """
    发送消息卡片（interactive）

    Args:
        receive_id: 接收者 ID
        receive_id_type: "open_id" 或 "chat_id"
        card: 卡片 JSON 对象

    Returns:
        {"message_id": "...", "chat_id": "..."}
    """
    url = f"{FEISHU_API_BASE}/im/v1/messages?receive_id_type={receive_id_type}"

    payload = {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card)
    }

    resp = requests.post(url, headers=_headers(), json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise Exception(f"发送卡片失败: {result}")

    data = result.get("data", {})
    return {
        "message_id": data.get("message_id", ""),
        "chat_id": data.get("chat_id", "")
    }


# ============================================================================
# 每日简报卡片
# ============================================================================

def build_daily_report_card(date_str: str, paper_count: int, high_impact: int, doc_url: str = None) -> dict:
    """
    构建每日科研简报卡片

    Args:
        date_str: 日期字符串
        paper_count: 论文数量
        high_impact: 高影响力论文数量
        doc_url: 完整报告文档链接

    Returns:
        飞书卡片 JSON
    """
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📚 每日科研简报 {date_str}"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**研究方向**: 金刚石NV色心 · 量子传感"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**今日新论文**: {paper_count} 篇"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**高影响力**: {high_impact} 篇 🔥"
                }
            },
            {"tag": "hr"}
        ]
    }

    if doc_url:
        card["elements"].append({
            "tag": "action",
            "actions": [
                {
                    "tag": "open_link",
                    "text": {"tag": "plain_text", "content": "📖 查看完整报告"},
                    "url": doc_url
                }
            ]
        })

    card["elements"].append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": "由 Semantic Scholar Research Automation 生成"}
        ]
    })

    return card


def send_daily_report_card(receive_id: str, receive_id_type: str, date_str: str,
                           paper_count: int, high_impact: int, doc_url: str = None) -> dict:
    """发送每日科研简报卡片"""
    card = build_daily_report_card(date_str, paper_count, high_impact, doc_url)
    return send_interactive_card(receive_id, receive_id_type, card)


# ============================================================================
# Markdown 转飞书块
# ============================================================================

def markdown_to_feishu_blocks(markdown: str) -> List[dict]:
    """
    将 Markdown 转换为飞书文档块格式

    支持: 标题、段落、分割线、列表、代码块、引用
    """
    lines = markdown.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 跳过空行
        if not line.strip():
            i += 1
            continue

        # 标题
        if line.startswith("### "):
            blocks.append({
                "tag": "heading3",
                "content": line[4:].strip()
            })
        elif line.startswith("## "):
            blocks.append({
                "tag": "heading2",
                "content": line[3:].strip()
            })
        elif line.startswith("# "):
            blocks.append({
                "tag": "heading1",
                "content": line[2:].strip()
            })

        # 分割线
        elif line.strip() in ["---", "***", "___"]:
            blocks.append({"tag": "horizontal_line"})

        # 无序列表
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            content = line.strip()[2:].strip()
            blocks.append({
                "tag": "bullet",
                "content": content
            })

        # 有序列表
        elif line.strip()[0].isdigit() and ". " in line:
            idx = line.index(". ")
            content = line.strip()[idx+2:].strip()
            blocks.append({
                "tag": "ordered",
                "content": content
            })

        # 引用
        elif line.strip().startswith(">"):
            content = line.strip()[1:].strip()
            blocks.append({
                "tag": "quote",
                "content": content
            })

        # 代码块
        elif line.strip().startswith("```"):
            # 收集代码块内容
            lang = line.strip()[3:]
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_content = "\n".join(code_lines)
            blocks.append({
                "tag": "code",
                "language": lang or "plain",
                "content": code_content
            })

        # 段落（默认）
        else:
            # 合并连续的非特殊行
            para_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip() and not any(
                lines[j].strip().startswith(x) for x in ["#", "-", "*", ">", "```", "---"]
            ):
                para_lines.append(lines[j])
                j += 1
            content = " ".join(l.strip() for l in para_lines if l.strip())
            if content:
                blocks.append({
                    "tag": "text",
                    "content": content,
                    "text_styles": {"bold": True} if "**" in content else None
                })
            i = j - 1

        i += 1

    return blocks


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
    url = f"{FEISHU_API_BASE}/contact/v3/users/batch_get_id"

    payload = {}
    if user_email:
        payload["emails"] = [user_email]
    elif user_name:
        # 搜索用户
        search_url = f"{FEISHU_API_BASE}/search/v1/user"
        params = {"query": user_name, "user_id_type": "open_id"}
        resp = requests.get(search_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json()

        if result.get("code") != 0 or not result.get("data", {}).get("users"):
            raise Exception(f"未找到用户: {user_name}")

        users = result["data"]["users"]
        return users[0].get("open_id", "")

    if not payload:
        raise ValueError("需要提供 email 或 name")

    resp = requests.post(url, headers=_headers(), json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 0:
        raise Exception(f"获取用户 ID 失败: {result}")

    users = result.get("data", {}).get("user_list", [])
    if not users:
        raise Exception("未找到对应用户")

    return users[0].get("open_id", "")
