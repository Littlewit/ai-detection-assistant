"""图像分析服务 - 多模态产品识别与拆分图渲染"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from dashscope import MultiModalConversation
from app.config import get_settings


SPLIT_ANALYSIS_PROMPT = """
你是一名资深检测工程师，擅长产品样板拆分分析。
你所在的实验室拥有 CNAS/CMA/CPSC 资质，
检测领域涵盖：有害物质、安规、EMC、环境可靠性、材料分析、纺织品、玩具、食品接触材料等。

请仔细观察该产品图片，分析产品的组成部分，并以 JSON 格式输出拆分结果。
请特别关注以下方面：
1. 每个组件的材质类型（决定需要哪些化学检测）
2. 每个组件对应的检测项目
3. 适用的检测标准（如 IEC/EN/GB/ASTM/UL 等）

输出格式要求：
{
  "product_name": "产品名称",
  "components": [
    {
      "name": "组件名称",
      "material": "主要材质",
      "material_category": "材质大类(金属/塑料/纺织/陶瓷/木材/其他)",
      "quantity": 1,
      "position": "在整体产品中的位置描述",
      "test_items": ["建议检测项目"],
      "applicable_standards": ["适用标准编号"]
    }
  ],
  "overall_structure": "整体结构描述"
}

请仅输出 JSON，不要包含其他内容。
"""


def analyze_product_image(image_path: str) -> dict:
    """分析产品图片，生成拆分结构（使用 DashScope MultiModalConversation 原生 API）"""
    settings = get_settings()

    messages = [
        {
            "role": "user",
            "content": [
                {"text": SPLIT_ANALYSIS_PROMPT},
                {"image": f"file://{image_path}"},
            ],
        }
    ]

    response = MultiModalConversation.call(
        model=settings.qwen_vl_model,
        messages=messages,
        api_key=settings.dashscope_api_key,
    )

    if response.status_code != 200:
        raise RuntimeError(f"VL model error: {response.code} - {response.message}")

    content = response.output.choices[0].message["content"][0]["text"].strip()
    # 清理 markdown 代码块
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return json.loads(content)


def render_split_diagram(analysis_result: dict, output_path: str) -> str:
    """根据拆分分析结果渲染拆分示意图"""
    # 支持中文
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12)
    ax.axis("off")

    product_name = analysis_result.get("product_name", "未知产品")
    ax.set_title(f"{product_name} - 样板拆分图", fontsize=16, fontweight="bold", pad=20)

    components = analysis_result.get("components", [])
    n = len(components)
    if n == 0:
        ax.text(6, 6, "未识别到组件", ha="center", va="center", fontsize=14)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return output_path

    colors = plt.cm.Set3([i / max(n, 1) for i in range(n)])
    available_height = 9
    item_height = min(available_height / n - 0.3, 1.5)

    for i, comp in enumerate(components):
        y_pos = 10 - i * (available_height / n)
        width = 8
        rect = patches.FancyBboxPatch(
            (2, y_pos), width, item_height,
            boxstyle="round,pad=0.05",
            facecolor=colors[i], edgecolor="#333333", linewidth=1.5,
        )
        ax.add_patch(rect)

        name = comp.get("name", f"组件{i+1}")
        material = comp.get("material", "未知")
        qty = comp.get("quantity", 1)
        mat_cat = comp.get("material_category", "")
        label = f"{name}\n材质: {material} × {qty}"
        if mat_cat:
            label += f" [{mat_cat}]"
        ax.text(6, y_pos + item_height / 2, label,
                ha="center", va="center", fontsize=9, fontweight="bold")

        # 右侧标注检测项目
        test_items = comp.get("test_items", [])
        if test_items:
            items_text = ", ".join(test_items[:3])
            if len(test_items) > 3:
                items_text += f" +{len(test_items)-3}"
            ax.text(11, y_pos + item_height / 2, items_text,
                    ha="right", va="center", fontsize=7, color="#666666")

    # 底部标注
    ax.text(6, 0.5, f"CNAS L7462 | 共 {n} 个组件",
            ha="center", va="center", fontsize=8, color="#999999")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path
