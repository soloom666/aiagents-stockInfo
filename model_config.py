"""
模型配置文件
包含所有可用的AI模型选项与自定义模型辅助方法
"""

from typing import Dict


model_options: Dict[str, str] = {
    "__custom__": "自定义模型",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-reasoner": "DeepSeek Reasoner",
    "qwen3-max": "Qwen3 Max (阿里百炼)",
    "gpt-5.4": "GPT-5.4 (OpenAI)",
    "gpt-5.5": "GPT-5.5 (OpenAI)",
    "claude-4-6-sonnet-latest": "Claude 4.6 Sonnet (Anthropic)",
    "claude-sonnet-4-20250514": "Claude Sonnet 4 (Anthropic)",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview (Google)",
    "gemini-3.1-flash": "Gemini 3.1 Flash (Google)"
}


def get_model_label(model_name: str) -> str:
    """获取模型展示名。"""
    if not model_name:
        return "未设置"
    if model_name in model_options:
        return model_options[model_name]
    return f"自定义: {model_name}"


def build_model_options_with_current(current_model: str) -> Dict[str, str]:
    """如果当前模型不在预设列表中，动态加入为自定义模型。"""
    options = dict(model_options)
    if current_model and current_model not in options and current_model != "__custom__":
        options[current_model] = f"自定义: {current_model}"
    return options
